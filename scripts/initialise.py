"""
Initialise targets and scores tables for target selector. 
"""

import csv
import mysql.connector 
import yaml

print("Loading config file")

with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

connection = mysql.connector.connect(**config)
cursor = connection.cursor()

print("Creating targets table")

cursor.execute(
    "CREATE TABLE IF NOT EXISTS targets (source_id VARCHAR(255), ra DOUBLE, "
    "decl DOUBLE, dist_c DOUBLE)"
    )

print("Creating scores table")

cursor.execute(
    "CREATE TABLE IF NOT EXISTS scores (source_id VARCHAR(255), "
    "band VARCHAR(16), uhf INT, l INT, s0 INT, s1 INT, s2 INT, "
    "s3 INT, s4 INT)"
    )

print("Populating from Gaia csv")

filepath = "tiny.csv"

insert_targets = (
    "INSERT INTO targets (source_id, ra, decl, dist_c) "
    "VALUES (%s, %s, %s, %s)"
)

insert_scores = "INSERT INTO scores (source_id) VALUES (%s)"

with open(filepath, "r") as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        cursor.execute(insert_targets, row)
        cursor.execute(insert_scores, (row[0],))

connection.commit()

cursor.close()
connection.close()