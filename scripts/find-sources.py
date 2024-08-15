"""
Retrieve source info from targets DB, given a JSON dict of sources.
"""

import json
import mysql.connector
import argparse
import sys
import yaml

def cli(args = sys.argv[0]):
    usage = "{} [options]".format(args)
    description = "Retrieve source information from list of source IDs."
    parser = argparse.ArgumentParser(prog = "source-info",
                                     usage = usage,
                                     description = description)
    parser.add_argument("-i",
                        type = str,
                        default = None,
                        help = 'Input JSON-formatted list of sources')

    parser.add_argument("-o",
                        type = str,
                        default = "output.json",
                        help = "Output file name.")

    parser.add_argument("-c",
                        type = str,
                        default = "config.yml",
                        help = "DB config file.")

    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()
    args = parser.parse_args()

    find_sources(input = args.i, output = args.o, config = args.c)

def find_sources(input, output, config):

    with open(input, "r") as f:
        sourcedict = json.load(f)

    sourcelist = list(sourcedict.values())

    with open(config, "r") as f:
        db_params = yaml.safe_load(f)

    connection = mysql.connector.connect(**db_params)
    cursor = connection.cursor()

    query_list = "' OR source_id = '".join(sourcelist)
    query = f"SELECT source_id, dist_c FROM target_list WHERE source_id = '{query_list}'"

    with connection.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchall()

    with open(output, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    cli()
