#Save ArcGIS License Manager log files

By default, the ArcGIS license server log files are over-written every day. This script extracts the important
information from the log files, such that they can be analysed and patterns discerned, etc.

This script should be run regularly as a scheduled task to avoid losing information when the log file is over-written.

Before running this script:
 - Ensure that the license manager log file is accessible to this script (eg share the folder on the network)
 - Create a PostGreSQL table containing the fields:
   - servername (text)
   - action_date (date)
   - action_time (time without timezone)
   - license (text)
   - action (text)
   - username (text)
- Set the PostGreSQL password in an environment variable 'pgpassword'
