import mysql.connector
from mysql.connector.errors import OperationalError
import yaml
import scipy.constants as constants
import json
import redis

from target_selector.logger import log
from target_selector.util import alert

class Triage:
    """Connect to the main target list database and rank objects in the field
    of view by observing priority.
    """

    def __init__(self, config_file, redis_endpoint):
        self.connection = self.connect(config_file)
        redis_host, redis_port = redis_endpoint.split(':')
        self.r = redis.StrictRedis(host=redis_host,
                                   port=redis_port,
                                   decode_responses=True)
        self.valid_bands = {"u", "l", "s0", "s1", "s2", "s3", "s4"}

    def connect(self, config_file):
        """Connect to DB.
        """
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        return mysql.connector.connect(**config)


    def update(self, band, source_id, t, nsegs, nants):
        """Atomic update of scores for specified sources.
        """
        # Check input for `band`:
        if band not in self.valid_bands:
            log.error("Bad input for `band`")
            raise ValueError
        delta_score = t*nsegs*nants
        update = f"UPDATE targets SET {band} = {band} + %s WHERE source_id = %s"

        with self.connection.cursor() as cursor:
        #cursor = self.connection.cursor()
            cursor.execute(update, (delta_score, source_id))
            self.connection.commit()
        #cursor.close()

    def get_targets(self, obsid, n):
        """Get the top <n> targets for a particular obsid.
        """
        targets = json.loads(self.r.get(f"targets:{obsid}"))
        return targets[0:n]

    def est_fov_generic(self, d, f):
        """Estimate field of view for cone search. b in metres, f in MHz.
        """
        return 0.5*(constants.c/(f*1e6))/d

    def cone_query(self, ra, dec, d, f):
        """Cone search query for a given target. ra and dec in radians;
        f in MHz, d in metres.
        """
        r = self.est_fov_generic(d, f)
        query = ("SELECT `source_id`, `ra`, `decl` FROM targets "
                 "WHERE ACOS(SIN(RADIANS(`decl`))*SIN(%s)+COS(RADIANS(`decl`))"
                 "*COS(%s)*COS(%s-RADIANS(`ra`)))<%s")
        values = (dec, dec, ra, r)
        return query, values

    def rank_sources(self, ra, dec, d, f, band):
        """Triage sources within search area.
        """
        # Check input for `band`:
        if band not in self.valid_bands:
            log.error("Bad input for `band`")
            raise ValueError
        other_bands = "+".join({band}^self.valid_bands)
        sub_query = f" ORDER BY {band}, ({other_bands}), dist_c"
        cone_query, cone_values = self.cone_query(ra, dec, d, f)
        targets = []
        try:
            #cursor = self.connection.cursor()
            with self.connection.cursor() as cursor:
                cursor.execute(cone_query + sub_query, cone_values)
                targets.extend(cursor.fetchall())
        except OperationalError:
            alert(self.r,
            f":warning: MySQL connection not available",
            "target selector")
        return targets

    def format_targets(self, targets, pointing):
        """Formats dataframe target list into JSON list of dicts for storing
        in Redis. 

        Args:
            targets: List of target tuples.
            pointing (dict): Dictionary containing the name of the 
            primary pointing and its coordinates.

        Returns:
            json_list (JSON): JSON-formatted dictionary containing the targets
            in the current field of view. The structure is as follows:
            `[{primary_pointing, primary_ra, primary_dec}, {source_id_0, ra,
            dec}, {source_id_1, ra, dec}, ... ]`
        """
        t_list = [{"source_id":t[0], "ra":t[1], "dec":t[2]} for t in targets]
        t_list.insert(0, pointing)
        json_list = json.dumps(t_list)
        return json_list
