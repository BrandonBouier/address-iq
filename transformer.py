# Goal: take rows in one database, perform a transformation, dump them into another

# steps:
# connect to database
# load rows
# for each:
#     run transformation function
#     queue insert into destination table
# connect to destination database
# execute inserts

# interface: 
# `transformer --hostdb=dbstring1 --destinationdb=dbstring2 transformation.py`
# `python fire_transformation.py --hostdb=dbstring1 --destinationdb=dbstring2`

# transformations desired:
# text transforms on row/col (done, though ideally by name)
# remove duplicates based on key

import argparse
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.sql import select, insert

host_db = None
destination_db = None

meta = MetaData()

def transform(host_engine, dest_engine, table_name, transformations):
    host_table = Table(table_name, meta, autoload=True, autoload_with=host_engine)

    results = host_engine.execute(select([host_table]))

    transformed_rows = []
    for row in results:
        new_row = row
        
        # Run all transformations, stopping if one returns None
        for f in transformations:
            new_row = f(new_row)
            if new_row == None:
                break

        if new_row != None:
            transformed_rows.append(new_row)

    dest_table = Table(table_name, meta, autoload=True, autoload_with=dest_engine)
    dest_engine.execute(dest_table.delete())
    dest_engine.execute(dest_table.insert(), transformed_rows)

