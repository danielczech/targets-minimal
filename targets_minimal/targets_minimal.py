import redis
import pandas as pd
import yaml
import scipy.constants as constants
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
import numpy as np
import json
import time

try:
    from .logger import log
except ImportError:
    from logger import log

class TargetsMinimal(object):
    """A minimal implementation of the target selector. It functions as follows:

       1. Subscribes to the `pointing_channel` - the Redis pub/sub channel to 
          which new pointings are to be published. These messages must be 
          formatted as follows:
          `<subarray name>:<target name>:<RA>:<Dec>:<FECENTER>:<OBSID>`
          RA and Dec should be in degrees, while `FECENTER` should be in Hz.

       2. When a new pointing message is received, the radius of the primary 
          beam is estimated using `FECENTER`. 

       3. Retrieves the list of targets available within the primary field of 
          view from the primary star database.

       4. Formats the list into a list of dictionaries:
          `[{source_id, ra, dec}, {source_id, ra, dec}, ... ]`
          Details of the primary pointing are included as follows:
          `{primary_pointing, primary_ra, primary_dec}`

       5. This list is JSON-formatted and saved in Redis under the key:
          `targets:<OBSID>`

       6. The key is published to the `targets_channel`. 
    """

    def __init__(self, redis_endpoint, pointing_channel, targets_channel, config_file):
        """Initialise the minimal target selector. 

        Args:
            redis_endpoint (str): Redis endpoint (of the form <host IP
            address>:<port>) 
            pointing_channel (str): Name of the channel from which the minimal
            target selector will receive new pointing information.  
            targets_channel (str): Name of the channel to which the minimal 
            target selector will publish target information.  
            config_file (str): Location of the database config file (yml).

        Returns:
            None
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

        Args:
            config_file (str): File path to the .yml DB configuration file. 

        Returns:
            None
        """
        cfg = self.read_config_file(config_file)
        url = URL(**cfg)
        self.engine = create_engine(url)
        self.connection = self.engine.connect()

    def read_config_file(self, config_file):
        """Read the database configuration yaml file.

        Args:
            config_file (str): File path to the .yml DB configuration file. 

        Returns:
            None
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

        `<OBSID>:<target name>:<RA (deg)>:<Dec (deg)>:<FECENTER>`

        Note that OBSID must be constructed as follows:

        `<telescope name>:<subarray name>:<PKTSTART timestamp>`
 
        Args:
            msg (str): The incoming message from the `pointing_channel`. 

        Returns:
            None
        """
        msg_data = msg['data']
        log.info(msg_data)
        msg_components = msg_data.split(':')
        # Basic checks of incoming message
        if(len(msg_components) == 7):
            telescope_name = msg_components[0]       
            subarray = msg_components[1]       
            pktstart_ts = msg_components[2]       
            target_name = msg_components[3]       
            ra_deg = float(msg_components[4])       
            dec_deg = float(msg_components[5])
            fecenter = float(msg_components[6])
            obsid = '{}:{}:{}'.format(telescope_name, subarray, pktstart_ts)
            self.calculate_targets(subarray, target_name, ra_deg, dec_deg, fecenter, obsid)
        else:
            log.warning('Unrecognised message: {}'.format(msg_data))
 
    def calculate_targets(self, subarray, target_name, ra_deg, dec_deg, fecenter, obsid):
        """Calculates and communicates targets within the current field of view
        for downstream processes.

        Args:
            subarray (str): The name of the current subarray.  
            (TODO: use this to manage multiple simultaneous subarrays). 
            target_name (str): The name of the primary pointing target.
            ra_deg (float): RA in degrees of the primary pointing target. 
            J2000 coordinates should be used if the original 26M Gaia 
            DR2-derived star list is used.
            dec_deg (float): As above, Dec in degrees. 
            fecenter (float): The centre frequency of the current observation.
            (TODO: more nuanced estimate of field of view).
            obsid (str): `OBSID` (unique identifier) for the current obs. Note
            that `OBSID` is of the form:
            `<telescope name>:<subarray name>:<PKTSTART timestamp>`

        Returns:
            None   
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
        pointing_dict = {'primary_pointing':target_name, 'primary_ra':ra_deg, 'primary_dec':dec_deg}
        json_list = self.format_targets(target_list, pointing_dict)
        # Write the list of targets to Redis under OBSID and alert listeners
        # that new targets are available:
        self.redis_server.set('targets:{}'.format(obsid), json_list)
        self.redis_server.publish(self.targets_channel, 'targets:{}'.format(obsid))

    def format_targets(self, df, pointing_dict):
        """Formats dataframe target list into JSON list of dict for storing in Redis. 
        
        Args:
            df (dataframe): Dataframe of target list for the current pointing.
            pointing_dict (dict): Dictionary containing the name of the 
            primary pointing and its coordinates.

        Returns:
            json_list (JSON): JSON-formatted dictionary containing the targets
            in the current field of view. The structure is as follows:
            `[{primary_pointing, primary_ra, primary_dec}, {source_id_0, ra, 
            dec}, {source_id_1, ra, dec}, ... ]`
        """ 
        output_list = [pointing_dict]
        df = df.to_numpy()
        for i in range(df.shape[0]):
            source_i = {}
            source_i['source_id'] = df[i, 0]
            source_i['ra'] = df[i, 1]
            source_i['dec'] = df[i, 2]
            output_list.append(source_i)
        json_list = json.dumps(output_list)
        return(json_list)






