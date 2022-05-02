## Full-featured target selector  

A more full-featured version of the target selector is described here. 
The target selector should listen to a Redis channel `target-selector:new-pointing`
for information about new pointings as well as another, `target-selector:completed`,
for information about targets (within the primary field of view surrounding a new pointing)
for which recording and observing has been completed. The full-featured target selector 
is being worked on here: https://github.com/UCBerkeleySETI/target-selector.  
  
**New primary pointings:**  
  
New target messages are of the form 
`<subarray name>:<target name>:<RA (deg)>:<Dec (deg)>:<FECENTER>:<OBSID>`.  

Upon receiving this message, the `target-selector` process should do the 
following:  

1. Estimate the current primary field of view of the telescope.  

2. Query the different databases (e.g. full Gaia-derived source list, exotica 
target list, ad-hoc sources, etc) and determine all the sources in the current
 primary field of view, ranked by distance.  

3. Query the different databases (e.g. full Gaia-derived source list, exotica 
target list, ad-hoc sources, etc) and determine all the sources in the current
 primary field of view, ranked by distance, **excluding** all previously 
observed targets in the same frequency band.  

4. Query the different databases (e.g. full Gaia-derived source list, exotica 
target list, ad-hoc sources, etc) and determine all the sources in the current
 primary field of view, **excluding** all previously observed targets in the 
same frequency band **and** ranked by priority score.  

5. Query the different databases (e.g. full Gaia-derived source list, exotica 
target list, ad-hoc sources, etc) and, based on priority score, determine the 
optimal beam placement.  

6. Place all of the above lists into separate JSON-formatted dictionaries, and write 
these into Redis under the following keys respectively: `all_targets:<OBSID>`, 
`unseen_targets:<OBSID>`, `ranked_targets:<OBSID>` and `beam_placement:<OBSID>`.

7. Dictionaries 4 and 5 are to include respectively a field for the priority algorithm and 
parameters, and for the optimal beam placement parameters. 

8. Publish an alert (`targets:<OBSID>`) to the Redis channel for new targets 
(`targets`). 
  
**Observation/processing completed:**   
  
Once a source in the field of view has been observed, observation completion 
messages will be sent to a "completed observations" channel. Such messages 
could be of the form:  
  
`<OBSID>:<Gaia source ID>:<RA>:<Dec>:<freq. band>:<antennas>:<recording duration>`   
  
Here, `antennas` refers to the number of antennas for which data were recorded
and `freq. band` refers to the actual segment of the band that was recorded 
and processed for this particular observation. `recording duration` is the 
length of the recording that was processed in seconds.  

Once a new observation completion message is received, it is stored in a 
database of completed observations (along with all the metadata above). This
database is to be used when making priority criteria determinations for 
selection and ranking of targets for any future new pointing messages. 
  
For example: closer sources that have not yet been observed in any frequency 
band would be ranked higher than others. If available sources have already 
been observed in a different frequency band than the current observation,
they would rank lower, but still above sources that have been observed in all 
available bands. 
