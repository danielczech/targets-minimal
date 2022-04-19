import redis
import pandas as pd
import yaml
import scipy.constants as constants
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
import numpy as np
import json
import time

from .logger import log

class TargetsMinimal(object):
    """A minimal implementation of the target selector.
    """

    def __init__(self, redis_endpoint, pointing_channel, targets_channel, config_file):
        """Initialise the minimal target selector. 
        """
        log.info('Initialising the minimal target selector')
        redis_host, redis_port = redis_endpoint.split(':')
        self.redis_server = redis.StrictRedis(host=redis_host, 
                                              port=redis_port, 
                                              decode_responses=True)
        self.pointing_channel = pointing_channel
        self.targets_channel = targets_channel
        self.configure_db(config_file)

    def start(self):
        """Start the minimal target selector.
        """
        log.info('Starting minmial target selector.')
        log.info('Listening for new pointings on Redis channel: {}'.format(self.pointing_channel))
        ps = self.redis_server.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(self.pointing_channel)
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

        `<subarray name>:<target name>:<RA (deg)>:<Dec (deg)>:<FECENTER>:<OBSID>`
 
        """
        msg_data = msg['data']
        log.info(msg_data)
        msg_components = msg_data.split(':')
        # Basic checks of incoming message
        if(len(msg_components) == 6):
            subarray = msg_components[0]       
            target_name = msg_components[1]       
            ra_deg = float(msg_components[2])       
            dec_deg = float(msg_components[3])
            fecenter = float(msg_components[4])
            obsid = msg_components[5]
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
        targets_query = """
                        SELECT `source_id`, `ra`, `dec`, `dist_c`
                        FROM target_list
                        WHERE ACOS(SIN(RADIANS(`dec`))*SIN({})+COS(RADIANS(`dec`))*COS({})*COS({}-RADIANS(`ra`)))<{};
                        """.format(np.deg2rad(dec_deg), np.deg2rad(dec_deg), np.deg2rad(ra_deg), beam_radius)
        start_ts = time.time()
        target_list = pd.read_sql(targets_query, con=self.connection)
        end_ts = time.time()
        log.info('Retrieved {} targets in field of view in {} seconds'.format(target_list.shape[0], int(end_ts - start_ts)))
        json_list = self.format_targets(target_list)
        # Write the list of targets to Redis under OBSID and alert listeners
        # that new targets are available:
        self.redis_server.set(obsid, json_list)
        self.redis_server.publish(self.targets_channel, '{}:{}'.format(subarray, obsid))

    def format_targets(self, df):
        """Formats dataframe target list into JSON list of dict for storing in Redis. 
        """ 
        output_list = []
        df = df.to_numpy()
        for i in range(df.shape[0]):
            source_i = {}
            source_i['source_id'] = df[i, 0]
            source_i['ra'] = df[i, 1]
            source_i['dec'] = df[i, 2]
            output_list.append(source_i)
        json_list = json.dumps(output_list)
        return(json_list)






