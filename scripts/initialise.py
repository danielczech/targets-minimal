"""
Initialise targets and scores tables for target selector. 
"""

import csv
import mysql.connector 
import yaml

print("Loading config file")

with open("../config.yml", "r") as f:
    config = yaml.safe_load(f)

connection = mysql.connector.connect(**config)
cursor = connection.cursor()

print("Creating targets table")

cursor.execute(
    "CREATE TABLE IF NOT EXISTS targets (source_id VARCHAR(255), ra DOUBLE, "
    "decl DOUBLE, dist_c DOUBLE, uhf INT, l INT, s0 INT, s1 INT, s2 INT, "
    "s3 INT, s4 INT)"
    )

print("Populating from Gaia csv")

filepath = "gaia_targets_complete.csv"

insert_targets = (
    "INSERT INTO targets (source_id, ra, decl, dist_c, uhf, l, s0, s1, s2, s3, s4) "
    "VALUES (CONCAT('Gaia_', %s), %s, %s, %s, 0, 0, 0, 0, 0, 0, 0)"
)

with open(filepath, "r") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        cursor.execute(insert_targets, row)

connection.commit()

cursor.close()
connection.close()
