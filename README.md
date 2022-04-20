## Minimal Target Selector

Provides basic target selection capabilities. 

**Usage:**  

```
usage: /opt/virtualenv/bluse3.9/bin/targets_minimal [options]

Start the Commensal Automator

optional arguments:
  -h, --help            show this help message and exit
  --redis_endpoint REDIS_ENDPOINT
                        Local Redis endpoint
  --pointing_channel POINTING_CHANNEL
                        Name of the channel from which information about new pointings will be received.
  --targets_channel TARGETS_CHANNEL
                        Name of the channel to which targets information will be published.
  --config_file CONFIG_FILE
                        Database configuration file.
```      

**Redis interfacing:**

This minimimal target selector provides the coordinates of stars within the current field of view.  
When a new source is tracked by the `coordinator`, the following message should be sent to the 
`pointing_channel` (at the same time as `PKTSTART`):

`<subarray name>:<target name>:<RA (deg)>:<Dec (deg)>:<FECENTER>:<OBSID>`

Upon receiving this message, the target selector does the following:  

1. Calculates an estimate of the radius of the primary beam at frequency `FECENTER`.  
2. Retrieves the list of targets available within the primary field of view from the primary star database.  
3. Formats the list into a list of dictionaries: `[{source_id, ra, dec}, {source_id, ra, dec}, ...`
4. Saves this list in the JSON format in Redis under the key given by `OBSID`.
5. Publishes a message: `<subarray name>:<OBSID>` to the `targets` Redis channel.

**Things to note:**  

1. Due to time limitations, I have not yet written full documentation of all the functions in the code. I will do so on 2022-04-19. 
2. `source_id` is the Gaia source ID of the particular star within the current field of view (most don't have a name beyond this).  
3. The minimal target selector does not take into account prior observations. 

**Daemonisation:**  

The target selector is designed to run as a daemon via circus:   
Logging: `/var/log/bluse/targets_minimal/targets_minimal.err`  
Starting via circus: `circusctl --endpoint tcp://10.98.81.254:5555 start targets_minimal`  

Example:  
`circusctl --endpoint tcp://10.98.81.254:5555 start targets_minimal`  
```
[2022-04-20 12:44:55,714 - INFO - targets_minimal.py:23] Initialising the minimal target selector
[2022-04-20 12:44:55,774 - INFO - targets_minimal.py:35] Starting minmial target selector.
[2022-04-20 12:44:55,774 - INFO - targets_minimal.py:36] Listening for new pointings on Redis channel: target-selector:new-pointing
```
`redis-cli publish target-selector:new-pointing test_array:test_src_name:40.44:60.52:1284000000:test_obsid`
```
[2022-04-20 13:21:50,652 - INFO - targets_minimal.py:92] Calculating for test_src_name at (40.44, 60.52)
[2022-04-20 13:22:33,686 - INFO - targets_minimal.py:103] Retrieved 910 targets in field of view in 43 seconds
```

**Installation:**  
Database config file must be placed in this location: `/usr/local/etc/bluse/db_config.yml`  
Use virtual environment: `source /opt/virtualenv/bluse3.9/bin/activate`   
Install via `python3.9 setup.py install` into the virtual environment selected.  

