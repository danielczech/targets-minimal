import redis
import pandas as pd
import yaml
import scipy.constants as constants
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
import numpy as np

from .logger import log

class TargetsMinimal(object):
    """A minimal implementation of the target selector.
    """

    def __init__(self, redis_endpoint, redis_channel, config_file):
        """Initialise the minimal target selector. 
        """
        log.info('Initialising the minimal target selector')
        redis_host, redis_port = redis_endpoint.split(':')
        self.redis_server = redis.StrictRedis(host=redis_host, 
                                              port=redis_port, 
                                              decode_responses=True)
        self.redis_channel = redis_channel
        self.configure_db(config_file)

    def start(self):
        """Start the minimal target selector.
        """
        log.info('Starting. Listening on Redis channel: {}'.format(self.redis_channel))
        ps = self.redis_server.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(self.redis_channel)
        for msg in ps.listen():
            self.parse_msg(msg)

    def configure_db(self, config_file):
        """Configure access to the database of sources.
        """
        cfg = self.read_config_file(config_file)
        url = URL(**cfg)
        self.engine = create_engine(url)
        self.connection = self.engine.connect()

    def read_config_file(self, config_file):
        """Read the database configuration yaml file. 
        """
        try:
            with open(config_file, 'r') as f:
                try:
                    cfg = yaml.safe_load(f)
                    return(cfg['mysql'])
                except yaml.YAMLError as E:
                    log.error(E)
        except IOError:
            log.error('Config file not found')

 
    def parse_msg(self, msg):
        """Examines and parses incoming messages, and initiates the
        appropriate response.

        Expects a message of the form:

        `new-target:<subarray name>:<target name>:<RA (deg)>:<Dec (deg)>:<FECENTER>:<OBSID>`
 
        """
        msg_data = msg['data']
        log.info(msg_data)
        msg_components = msg_data.split(':')
        # Basic checks of incoming message
        if((len(msg_components) == 7) & (msg_components[0] == 'new-target')):
            subarray = msg_components[1]       
            target_name = msg_components[2]       
            ra_deg = float(msg_components[3])       
            dec_deg = float(msg_components[4])
            fecenter = float(msg_components[5])
            obsid = msg_components[6]
            self.calculate_targets(subarray, target_name, ra_deg, dec_deg, fecenter, obsid)
        else:
            log.warning('Unrecognised message: {}'.format(msg_data))
 
    def calculate_targets(self, subarray, target_name, ra_deg, dec_deg, fecenter, obsid):
        """Calculates and communicates targets within the current field of view 
        for downstream processes. 
        """
        log.info('Calculating for {} at ({}, {})'.format(target_name, ra_deg, dec_deg))
        # Calculate beam radius (TODO: generalise for other antennas besides MeerKAT):
        beam_radius = 0.5*(constants.c/fecenter)/13.5         
        log.info(beam_radius)
        targets_query = """
                        SELECT *
                        FROM target_list
                        WHERE ACOS( SIN( RADIANS('"dec"') )*SIN({}) + COS( RADIANS('"dec"') )*COS({})*COS({} - RADIANS('"ra"'))) < {}; 
                        """.format(np.deg2rad(dec_deg), np.deg2rad(dec_deg), np.deg2rad(ra_deg), beam_radius)
        log.info(targets_query)
        target_list = pd.read_sql(targets_query, con=self.connection)
        log.info(target_list)





