'''
By default, the ArcGIS license server log files are over-written every day. This script extracts the important
information from the log files (namely the date and time that each license was checked out/in, and by which user),
such that the license usage can be analysed and patterns discerned, etc.

The outputs are stored in a PostGreSQL table, but any other database would suffice. A database is preferable to a
text file as it's easier to query for existing entries, to avoid creating duplicate entries.

This script should be run regularly as a scheduled task to avoid losing information when the log file is over-written.

Before running this script:
 - Set the postgres password in an environment variable 'pgpassword'
 - Ensure that the license manager log file is accessible to this script (eg share the folder on the network)
 - Create a table containing the fields:
   - servername (text)
   - action_date (date)
   - action_time (time without timezone)
   - license (text)
   - action (text)
   - username (text)

Original coding: 2016-11-22 by Stephen Lead

'''

import os, sys, psycopg2, datetime

licenseServers = [
    #[license server name, path to the log file]
    ["vm-geolicense",r"\\vm-geolicense\License10.4_bin\lmgrd9.log"]
]

# Postgres parameters
dbHost = "localhost"
dbPort = "5432"
dbName = "steve"
dbUsername = "postgres"
dbTable = "arcgis_desktop"

# Retrieve the postgres password from the environment variable 'pgpassword'
try:
    dbPassword = os.environ['pgpassword']
except KeyError:
    sys.exit("Please set the PostGreSQL password in an environment variable 'pgpassword'")

# Connect to the output database
conn_string = "host=" + dbHost + " port=" + dbPort + " dbname=" + dbName + " user=" + dbUsername + " password=" + dbPassword
conn = psycopg2.connect(conn_string)
cursor = conn.cursor()
cursor.execute("SET DateStyle='mdy'")

for licenseServer in licenseServers:
    serverName = licenseServer[0]
    logFile = licenseServer[1]

    print("\nChecking " + serverName)

    if not (os.path.exists(logFile)):
        sys.exit("Can't find log file " + logFile)

    with open(logFile, 'r') as inF:
        lines = inF.readlines()
        for line in lines:
            # Split the line into tokens based on spaces
            tokens = line.strip().split(" ")

            # Record the date, which applies to subsequent lines. This is either provided as TIMESTAMP or Start-Date
            # (until overwritten by the next TIMESTAMP or Start-Date)
            if line.find("Start-Date") > -1:
                start = tokens.index("Start-Date:")
                year = tokens[start + 4]
                month = tokens[start + 2]
                day = tokens[start + 3]
                date = datetime.datetime.strptime(year + " " + month + " " + str(day), '%Y %b %d')
            elif line.find("TIMESTAMP") > -1:
                date = datetime.datetime.strptime(tokens[3], '%m/%d/%Y')

            # Detect when a license is checked in/out
            if line.find("OUT:") > -1 or line.find("IN:") > -1:
                time = tokens[0]
                action = tokens[2].replace(":","")
                license = tokens[3].replace('"','')
                username = tokens[4]

                # Ignore results within +/- 10 seconds of this one, to avoid duplication
                actiondate = datetime.datetime.strptime(str(date.month) + "/" + str(date.day) + "/" + str(date.year)
                    + " " + time, '%m/%d/%Y %H:%M:%S')
                beforedate = str(actiondate - datetime.timedelta(seconds=10))
                afterdate = str(actiondate + datetime.timedelta(seconds=10))

                # Check whether this result already exists, and add it if not
                query = "SELECT * FROM " + dbTable + " WHERE servername='" + serverName + "' AND action_date >= '" \
                        + beforedate + "' AND action_date <= '" + afterdate + "' AND license='" + license \
                        + "' AND action='" + action + "' AND username='" + username + "'"
                cursor.execute(query)
                recordExists = (cursor.rowcount > 0)
                if not recordExists:
                    SQL = "INSERT INTO " + dbTable
                    SQL += " (servername, action_date, action_time, license, action, username) "
                    SQL += "VALUES (%s, %s, %s, %s, %s, %s);"
                    data = (serverName, actiondate, time, license, action, username)
                    cursor.execute(SQL, data)
                    conn.commit()
                    print (" ".join([serverName, action, license, username]))

# Close the database connections
try:
    conn.commit()
    cursor.close()
    conn.close()
except:
    print("There was a problem closing the database connection")
    pass