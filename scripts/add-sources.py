#!/usr/bin/env python

"""
Script to add or remove sources from the initial sql database. 
"""

import argparse
import sys
import yaml
from sqlalchemy import create_engine, inspect, Column, Float, delete
from sqlalchemy.types import VARCHAR
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def read_yml(source_file):
    """Read in list of source dicts.
    """
    with open(source_file, 'r') as f:
        sources = yaml.safe_load(f)
    return sources

def add(sources):
    source_list = read_yml(sources)
    inputurl = "mysql+pymysql://root:root@localhost/breakthrough_db"
    engine = create_engine(url=inputurl)
    if inspect(engine).has_table('target_list'):
        Session = sessionmaker(bind=engine)
        session = Session()
        for source in source_list:
            s_id = source['source']
            ra = float(source['ra'])
            dec = float(source['dec'])
            dist = float(source['dist'])
            new_source = Source(source_id=s_id, ra=ra, decl=dec, dist_c=dist)
            session.add(new_source)
            session.commit()
    session.close()
        
def remove(sources):
    source_list = read_yml(sources)
    inputurl = "mysql+pymysql://root:root@localhost/breakthrough_db"
    engine = create_engine(url=inputurl)
    if inspect(engine).has_table('target_list'):
        Session = sessionmaker(bind=engine)
        session = Session()
        for source in source_list:
            print("Deleting 1 of {}".format(len(source_list)))
            s_id = source['source']
            session.query(Source).filter_by(source_id=s_id).delete()
            session.commit()
    session.close()

class Source(Base):
    __tablename__ = 'target_list'
    source_id = Column(VARCHAR(45), primary_key=True)
    ra = Column(Float)
    decl = Column(Float)
    dist_c = Column(Float)

def cli(args = sys.argv[0]):
    """Tool to add or remove sources from targets database.
    """
    usage = '{} [options]'.format(args)
    description = 'Add or remove sources from targets database.'
    parser = argparse.ArgumentParser(usage = usage, 
                                     description = description)
    parser.add_argument('-s',
                        '--sources', 
                        type = str,
                        default = 'sources.yml', 
                        help = 'Location of list of sources to add/remove')
    parser.add_argument('-r', 
                        '--remove', 
                        action='store_true', 
                        help='Remove sources')
    parser.add_argument('-a', '--add', 
                        action='store_true', 
                        help='Add sources')

    
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()
    args = parser.parse_args()

    if args.remove:
        remove(sources = args.sources)
    if args.add:
        add(sources = args.sources)

if __name__ == '__main__':
    cli()
