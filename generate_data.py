from factories import FireIncidentFactory, PoliceIncidentFactory, BusinessLicenseFactory
from app import db
import factory
import factory.fuzzy
import datetime
import pytz

ADDRESSES = [
    '123 MAIN ST',
    '444 MARKET ST',
    '155 9TH ST',
    '1 SO VAN NESS AV',
    '4555 UNION ST',
    '9999 GRAND VIEW AV',
    '2121 VALENCIA ST',
    '666 JUNIPERO SERRA'
]

FIRE_TYPES = [
    'Difficulty Breathing',
    'EMS call, excluding vehicle accident with injury',
    'Fall,Possibly Dangerous',
    'Chest Pain',
    'Unconscious/Fainting, After Interrogation',
    'Seizure,activ Mult',
    'Abdom Pain Fem>12'
]

POLICE_TYPES = [
    'District Car Check',
    'Traffic Stop',
    'Suspicious Person',
    'Party Disturbance',
    'Group Disturbance',
    'Burglary Report',
    'Battery'
]

BUSINESS_TYPES = [
    'Residential Care Facility',
    'Laundromat',
    'Liquor Store',
    'Bar'
]

AVG_RECORDS_PER_ADDRESS = 60

START_DATE = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=365*2)

def generate_fire_data():
    num_records = AVG_RECORDS_PER_ADDRESS * len(ADDRESSES)

    incidents = [FireIncidentFactory(incident_address=factory.fuzzy.FuzzyChoice(ADDRESSES),
                                     alarm_datetime=factory.fuzzy.FuzzyDateTime(START_DATE),
                                     actual_nfirs_incident_type_description=factory.fuzzy.FuzzyChoice(FIRE_TYPES))
     for i in range(num_records)]

def generate_police_data():
    num_records = AVG_RECORDS_PER_ADDRESS * len(ADDRESSES)

    incidents = [PoliceIncidentFactory(incident_address=factory.fuzzy.FuzzyChoice(ADDRESSES),
                                       call_datetime=factory.fuzzy.FuzzyDateTime(START_DATE),
                                       final_cad_call_type_description=factory.fuzzy.FuzzyChoice(POLICE_TYPES))
     for i in range(num_records)]

def generate_business_data():
    num_biz = len(ADDRESSES) / 2

    businesses = [BusinessLicenseFactory(business_address=factory.fuzzy.FuzzyChoice(ADDRESSES),
                                         name="bizbizbiz",
                                         business_service_description=factory.fuzzy.FuzzyChoice(BUSINESS_TYPES))
    for i in range(num_biz)]

if __name__ == '__main__':
    generate_fire_data()
    generate_police_data()
    generate_business_data()
    db.session.commit()