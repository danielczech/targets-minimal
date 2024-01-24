import redis
import time
import json

from target_selector.triage import Triage
from target_selector.logger import log

DELAY = 75 # seconds

class Selector(object):
    """A target selector class that supplies new target lists for observation,
    ordered by observing priority. It also responds to observing completion
    messages, updating the observing priority table accordingly.
    """

    def __init__(self, redis_ep, pointings, targets, processing, config, d):
        """Initialises a target selector instance.

        Args:
            redis_ep (str): Redis endpoint (<host IP address>:<port>)
            pointings (str): Name of the channel from which the target
            selector will receive new pointing information.
            targets (str): Name of the channel to which the target selector
            will publish target information.
            processing (str): Name of the channel from which the target
            selector will receive information about completed processing units.
            config (str): Location of the database config file (yml).
            d (float): diameter of telescope antenna (used in generic FoV
            calculation) in meters.
        """
        redis_host, redis_port = redis_ep.split(':')
        self.redis_server = redis.StrictRedis(host=redis_host, 
                                              port=redis_port, 
                                              decode_responses=True)
        self.pointing_channel = pointings
        self.targets_channel = targets
        self.proc_channel = processing
        self.msg_ts = 0
        self.Triage = Triage(config, redis_ep)
        self.d = d

    def start(self):
        """Start the target selector.
        """
        log.info('Starting the target selector.')
        ps = self.redis_server.pubsub(ignore_subscribe_messages=True)
        ps.subscribe(self.pointing_channel)
        log.info(f"Listening for new pointings on: {self.pointing_channel}")
        ps.subscribe(f"{self.proc_channel}")
        log.info(f"Listening for completion on: {self.proc_channel}")
        log.info(f"Publishing results to: {self.targets_channel}")
        for msg in ps.listen():
            self.msg_ts = time.time()
            self.parse_msg(msg)

    def parse_msg(self, msg):
        """Examines and parses incoming messages, and initiates the
        appropriate response.
        """
        msg_data = msg['data']
        msg_components = msg_data.split(':', 1)
        # Segment/subband successfully processed:
        if msg_components[0] == "UPDATE":
            log.info(f"Handling message: {msg_data}")
            self.update(msg_components[1])
        # New pointing, we need to supply new targets:
        elif msg_components[0] == "POINTING":
            log.info(f"Handling message: {msg_data}")
            self.pointing(msg_components[1])
        else:
            log.warning(f"Unrecognised message: {msg_data}")

    def update(self, msg):
        """Processes an update message for a completed subband.
        """
        try:
            update = json.loads(msg)
        except json.decoder.JSONDecodeError:
            log.error("Invalid JSON")
            return
        try:
            n = update["n"]
            band = update["band"]
            t = update["t"]
            nants = update["nants"]
            obsid = update["obsid"]
            nbeams = update["nbeams"]
        except KeyError as e:
            log.error(f"Missing key: {e}")
            return
        # Get targets that were just processed
        targets = self.Triage.get_targets(obsid, nbeams)
        # In sequence for now; consider altering format in future
        for target in targets:
            self.Triage.update(band, target["source_id"], t, n, nants)
        log.info(f"Updated target scores for {obsid}")

    def pointing(self, msg):
        """Processes a request for targets in the FoV of a new pointing.
        """
        try:
            pointing = json.loads(msg)
        except json.decoder.JSONDecodeError:
            log.error("Invalid JSON")
            return
        try:
            telescope = pointing["telescope"]
            array = pointing["array"]
            pktstart_ts = pointing["pktstart_ts"]
            target = pointing["target"]
            ra_deg = pointing["ra_deg"]
            dec_deg = pointing["dec_deg"]
            f_max = pointing["f_max"]
            band = pointing["band"]
            obsid = f"{telescope}:{array}:{pktstart_ts}"
        except KeyError as e:
            log.error(f"Missing key: {e}")
            return
        self.calc_targets(target, ra_deg, dec_deg, f_max, obsid, band)

    def calc_targets(self, target, ra_deg, dec_deg, f_max, obsid, band):
        """Calculates and communicates targets within the current field of
        view to downstream processes.
        """
        primary_target = {"source_id":target, "ra":ra_deg, "dec":dec_deg}
        target_list = self.Triage.triage(ra_deg, dec_deg, self.d, f_max, band)
        json_list = self.Triage.format_targets(target_list, primary_target)
        # Write the list of targets to Redis under OBSID and alert listeners
        # that new targets are available:
        self.redis_server.set(f"targets:{obsid}", json_list)
        # Temporary: Apply delay to ensure 60 + 15 second delay 
        current_duration = time.time() - self.msg_ts
        log.info(current_duration)
        if(current_duration < DELAY):
            log.info(f'TEMPORARY: sleeping for {DELAY - current_duration} seconds.')
            time.sleep(DELAY - current_duration)
        self.redis_server.publish(self.targets_channel, f"targets:{obsid}")



