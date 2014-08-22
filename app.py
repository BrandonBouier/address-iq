import datetime
import os
import operator
import pytz

from flask import Flask, render_template, abort, request, Response, session, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, login_user, logout_user, current_user, login_required
from functools import wraps
from requests import post

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
db = SQLAlchemy(app)

meta = db.MetaData()
meta.bind = db.engine

import models

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(userid):
    if not userid:
        return None
    try:
        userid = int(userid)
    except ValueError:
        # @todo: Log error.
        return None

    return models.User.query.get(userid)

def fetch_incidents_at_address(address):
    fire_query = db.session.query(models.FireIncident)
    fire_query = fire_query.filter(models.FireIncident.incident_address == address.upper())

    police_query = db.session.query(models.PoliceIncident)
    police_query = police_query.filter(models.PoliceIncident.incident_address == address.upper())

    business_query = db.session.query(models.BusinessLicense)
    business_query = business_query.filter(models.BusinessLicense.business_address == address.upper())

    return {
        'fire': fire_query.all(),
        'police': police_query.all(),
        'businesses': business_query.all()
    }


def count_incidents_by_timeframes(incidents, timeframes):
    def start_date_for_days(days):
        return datetime.date.today() - datetime.timedelta(days=days)

    # dates to look for events after for each timeframe
    timeframes_info = [{"days": days,
                        "start_date": start_date_for_days(days)
                        } for days in timeframes]

    counts = {'fire': {}, 'police': {}}

    for incident_type in counts:
        if incident_type == 'fire':
            date_field = 'alarm_datetime'
        else:
            date_field = 'call_datetime'

        for timeframe in timeframes:
            counts[incident_type][timeframe] = 0

        for incident in incidents[incident_type]:
            incident_date = getattr(incident, date_field).date()
            for timeframe_info in timeframes_info:
                if incident_date > timeframe_info['start_date']:
                    counts[incident_type][timeframe_info['days']] = \
                        counts[incident_type][timeframe_info['days']] + 1

    return counts

def get_top_incident_reasons_by_timeframes(incidents, timeframes):
    def start_date_for_days(days):
        return datetime.date.today() - datetime.timedelta(days=days)

    # dates to look for events after for each timeframe
    timeframes_info = [{"days": days,
                        "start_date": start_date_for_days(days)
                        } for days in timeframes]

    counts = {'fire': {}, 'police': {}}

    # count how many of each incident type happen in each timeframe
    for incident_type in counts:
        if incident_type == 'fire':
            reason_field = 'actual_nfirs_incident_type_description'
        else:
            reason_field = 'final_cad_call_type_description'

        if incident_type == 'fire':
            date_field = 'alarm_datetime'
        else:
            date_field = 'call_datetime'

        for timeframe in timeframes:
            counts[incident_type][timeframe] = {}

        for incident in incidents[incident_type]:
            incident_date = getattr(incident, date_field).date()
            incident_reason = getattr(incident, reason_field)
            for timeframe_info in timeframes_info:
                if incident_date > timeframe_info['start_date']:
                    relevant_reasons_table = counts[incident_type][timeframe_info['days']]

                    if incident_reason in relevant_reasons_table:
                        relevant_reasons_table[incident_reason] = relevant_reasons_table[incident_reason] + 1
                    else:
                        relevant_reasons_table[incident_reason] = 1

    top_call_types = {'fire': {}, 'police': {}}
    for incident_type in top_call_types:
        for timeframe_info in timeframes_info:
            num_days = timeframe_info['days']
            top_call_types[incident_type][num_days] = sorted(counts[incident_type][num_days].iteritems(),
                                                             key=operator.itemgetter(1))
            top_call_types[incident_type][num_days].reverse()
            top_call_types[incident_type][num_days] = top_call_types[incident_type][num_days][:5]

    return top_call_types


@app.route("/")
def home():
    user_email = get_email_of_current_user()
    kwargs = dict(email=user_email)

    return render_template('home.html', **kwargs)

@app.route('/log-in', methods=['POST'])
def log_in():
    posted = post('https://verifier.login.persona.org/verify',
                  data=dict(assertion=request.form.get('assertion'),
                            audience=app.config['BROWSERID_URL']))

    response = posted.json()

    if response.get('status', '') == 'okay':
        user = load_user_by_email(response['email'])
        if user:
            login_user(user)
            return 'OK'

    return Response('Failed', status=400)

@app.route('/log-out', methods=['POST'])
def log_out():
    logout_user()

    return redirect(url_for('home'))

def create_user(name, email):
    # Check whether a record already exists for this user.
    user = models.User.query.filter(models.User.email==email).first()
    if user:
        return False

    # If no record exists, create the user.
    user = models.User(name=name, email=email, date_created=datetime.datetime.now(pytz.utc))
    db.session.add(user)
    db.session.commit()

    return user

def load_user_by_email(email):
    # @todo: When we incorporate LDAP, update this to pull real name.
    name = 'Fireworks Joe'
    user = models.User.query.filter(models.User.email==email).first()
    if not user:
        create_user(name, email)

    return user

def get_email_of_current_user(user=current_user):
    if user.is_anonymous():
        return None

    email = user.email

    if not email:
        return None

    return email

@app.route("/address/<address>")
@login_required
def address(address):
    incidents = fetch_incidents_at_address(address)

    if len(incidents['fire']) == 0 and len(incidents['police']) == 0:
        abort(404)

    counts = count_incidents_by_timeframes(incidents, [7, 30, 90, 365])
    business_types = [biz.business_service_description.strip() for biz in incidents['businesses']]
    business_names = [biz.name.strip() for biz in incidents['businesses']]
    top_call_types = get_top_incident_reasons_by_timeframes(incidents, [7, 30, 90, 365])

    user_email = get_email_of_current_user()
    kwargs = dict(email=user_email, incidents=incidents, counts=counts,
                           business_types=business_types, business_names=business_names,
                           top_call_types=top_call_types, address=address)

    return render_template('address.html', **kwargs)

if __name__ == "__main__":
    app.run(debug=True)
