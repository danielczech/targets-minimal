"""
Connect to the main target list database and rank objects in the field of view
by observing priority.
"""

import mysql.connector
import yaml
import scipy.constants as constants
import json
import redis

class Triage:

    def __init__(self, config, redis_endpoint):
        self.connection = self.connect(config)
        redis_host, redis_port = redis_endpoint.split(':')
        self.r = redis.StrictRedis(host=redis_host,
                                   port=redis_port,
                                   decode_responses=True)

    def connect(self, config):

        with open("config.yml", "r") as f:
            config = yaml.safe_load(f)

        return mysql.connector.connect(**config)

    def get_score(self, band, source_id):
        """Get existing score.
        """
        # Check input for `band`:
        if band not in {"uhf", "l", "s0", "s1", "s2", "s3", "s4"}:
            #log.error("Bad input for `band`")
            raise ValueError

        cursor = self.connection.cursor()
        query = f"SELECT {band} FROM targets WHERE source_id = %s"
        cursor.execute(query, (source_id,))
        score = cursor.fetchone()
        cursor.close()
        return int(score[0])

    def set_score(self, band, source_id, score):
        """Set score in table.
        """
        # Check input for `band`:
        if band not in {"uhf", "l", "s0", "s1", "s2", "s3", "s4"}:
            #log.error("Bad input for `band`")
            raise ValueError

        cursor = self.connection.cursor()
        update = f"UPDATE targets SET {band} = %s WHERE source_id = %s"
        cursor.execute(update, (score, source_id))
        self.connection.commit()
        cursor.close()

    def update(self, band, source_id, t, nsegs, nants):
        # Check input for `band`:
        if band not in {"uhf", "l", "s0", "s1", "s2", "s3", "s4"}:
            #log.error("Bad input for `band`")
            raise ValueError
        new_score = t*nsegs*nants
        update = f"UPDATE targets SET {band} = {band} + %s WHERE source_id = %s"
        cursor = self.connection.cursor()
        cursor.execute(update, (new_score, source_id))
        self.connection.commit()
        cursor.close()

    def get_targets(self, obsid, n):
        """Get the top <n> targets for a particular obsid.
        """
        targets = json.loads(self.r.get(f"targets:{obsid}"))
        return targets[0:n]

    def est_fov(self, d, f):
        """Estimate field of view for cone search. b in metres, f in MHz.
        """
        return 0.5*(constants.c/(f*1e6))/d

    def cone_query(self, ra, dec, d, f):
        """Cone search query for a given target. ra and dec in radians;
        f in MHz, d in metres.
        """
        r = self.est_fov(d, f)
        query = ("SELECT `source_id`, `ra`, `decl` FROM targets "
                 "WHERE ACOS(SIN(RADIANS(`decl`))*SIN(%s)+COS(RADIANS(`decl`))"
                 "*COS(%s)*COS(%s-RADIANS(`ra`)))<%s")
        values = (dec, dec, ra, r)
        return query, values

    def triage(self, ra, dec, d, f, band):
        """Triage sources within search area
        """
        # Check input for `band`:
        if band not in {"uhf", "l", "s0", "s1", "s2", "s3", "s4"}:
            #log.error("Bad input for `band`")
            raise ValueError

        sub_query=(f" ORDER BY {band}, (uhf + l + s0 + s1 + s2 + s3 + s4), "
                   "dist_c")
        cone_query, cone_values = self.cone_query(ra, dec, d, f)

        cursor = self.connection.cursor()
        cursor.execute(cone_query + sub_query, cone_values)
        targets = cursor.fetchall()
        cursor.close()

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