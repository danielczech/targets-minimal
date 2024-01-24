# Target Selector

Provides target selection capabilities for commensal observing, including priority ranking and
updating.

## Usage
```
targetselector -h
usage: /usr/local/bin/targetselector [options]

Target selector for commensal beamforming searches.

optional arguments:
  -h, --help            show this help message and exit
  --redis_endpoint REDIS_ENDPOINT
                        Local Redis endpoint
  --pointing_channel POINTING_CHANNEL
                        Channel from which new pointings will be received.
  --targets_channel TARGETS_CHANNEL
                        Channel to which targets will be published.
  --processing_channel PROCESSING_CHANNEL
                        Channel from which processing messages will be received.
  --config CONFIG       Database configuration file.
  --diameter DIAMETER   Diameter of antenna for generic FoV estimate.
```

## Requesting targets for commensal observation

To request new targets, a string should be sent (via Redis pub/sub) to the
specified `pointing_channel`, with the following structure:

```
"POINTING:{
  "telescope":<telescope name>,
  "array":<subarray name>,
  "pktstart_ts":<recording timestamp>,
  "target":<target name>,
  "ra_deg":<RA in degrees>,
  "dec_deg":<Declination in degrees>,
  "f_max":<Maximum observing frequency>,
  "band":<observing band name>
  }"
```

Upon receiving this message, the target selector does the following:

1. Calculates an estimate of the radius of the primary beam at the frequency specified by `f_max`.
2. Retrieves the list of targets available within the primary field of view from the primary star database (see below for further details).
3. Calculates and applies observing priority to this list.
4. Formats the list into a list of dictionaries: `[{source_id_0, ra, dec}, {source_id_1, ra, dec}, ... ]`
 (Note that the first source in the list is the primary pointing).
5. Saves this list (JSON formatted) in Redis under the key given by `targets:<OBSID>`.
6. Publishes a Redis message: `targets:<OBSID>` to the associated targets channel.

## Observing priority

The aim is to deliver targets in order of observing priority. Since it is
possible that some targets have already been observed (or have already been
observed in other bands), an observing priority calculation is needed.

When a target has successfully been observed (and processed) in a particular
band, an observing score is calculated as follows:

```
score = <observed bandwidth>*<number of antennas>*<observation time>
```

This score is then added to the cumulative score recorded in the database for
that particular band. Observation time is in seconds, and observation
bandwidth is in "number of segments". A "segment" is simply the amount of
bandwidth processed by a single processing instance (the most granular level
possible). A processing instance will either succeed at processing the entire
segment, or fail entirely, no partial processing is possible.

When delivering new targets, they are ordered by priority as follows:

1. Targets that have the lowest score in the current band.
2. Targets that have the lowest cumulative score in other bands.
3. Targets that are closest.

For example, targets that have never been observed in the current band will
appear first, ordered by distance.

## Updating observing priority

To update observing scores for a completed observation and successful
processing, a message should be sent to the `processing_channel` as
follows:

```
"UPDATE:{
  "n":<number of segments>,
  "band":<observing band>,
  "nants":<number of antennas>
  "obsid":<unique observation identifier>,
  "nbeams":<number of processed beams>,
  "t":<observing duration in seconds>
  }"
```

## Database setup

To set up the initial Gaia targets database from a `.csv` file:

1. Edit the `config.yml` file with the appropriate database name and
permissions.
2. Acquire the needed `.csv` file (for example, the
[BLUSE target list](https://seti.berkeley.edu/meerkat_db/BL_MeerKAT_target_list_2021.csv.gz),
accompanying paper [here](https://arxiv.org/pdf/2103.16250.pdf)).
3. Edit and run `initialise.py`.

To improve cone search performance, consider indexing the `ra` and `decl`
columns, for example as follows:

```
mysql> CREATE INDEX index_ra_dec ON target_list(ra, decl);
```

## Installation

Consider installing within an appropriate virtual environment. Then:

```
python3 setup.py
```

For use as a daemonised process with circus, follow these steps:

- Ensure `targetselector.ini` is copied to the correct location (eg
`/etc/circus/conf.d/targetselector/targetselector.ini`)

- Ensure the environment initialisation file refers correctly to the coordinator.ini file, eg:

```
[env:targetselector]
VE_DIR = /opt/virtualenv/<env_name>
VE_VER = <env version>
```

Ensure logging is set up correctly and that a location for the log files exists, eg:

```
mkdir /var/log/bluse/targetselector
```

Run `circusctl --endpoint <endpoint> reloadconfig`

Run `circusctl --endpoint <endpoint> start targetselector`

## Daemonisation

The target selector is designed to run as a daemon via circus:

Logging: `/var/log/bluse/targetselector/targetselector.err`

Starting via circus: `circusctl --endpoint tcp://<IP address>:5555 start targetselector`

Example:
```
circusctl --endpoint tcp://10.98.81.254:5555 start targetselector

[2024-01-24 17:03:27,313 - INFO - selector.py:45] Starting the target selector.
[2024-01-24 17:03:27,315 - INFO - selector.py:48] Listening for new pointings on: target-selector:pointings
[2024-01-24 17:03:27,315 - INFO - selector.py:50] Listening for completion on: target-selector:processing
[2024-01-24 17:03:27,315 - INFO - selector.py:51] Publishing results to: target-selector:targets
```