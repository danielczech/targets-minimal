##Minimal Target Selector

Provides basic target selection capabilities.
  
*Redis interfacing* 

This minimimal target selector provides the coordinates of stars within the current field of view.  
When a new source is tracked by the `coordinator`, the following message is sent (at the same time 
as `PKTSTART`) to the `target-selector` Redis channel:

`new-target:<subarray name>:<target name>:<RA (deg)>:<Dec (deg)>:<FECENTER>:<OBSID>`

Upon receiving this message, the target selector does the following:  

1. Calculates an estimate of the radius of the primary beam at frequency `FECENTER`.  
2. Retrieves the list of targets available within the primary field of view from the primary star database.  
3. Formats the list into a list of dictionaries: `[{source_id, ra, dec}, {source_id, ra, dec}, ...`
4. Saves this list in the JSON format in Redis under the key given by `OBSID`.
5. Publishes a message: `new-targets:<subarray name>:<OBSID>` to the `target-selector` Redis channel.
