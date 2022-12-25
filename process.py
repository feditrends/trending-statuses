import datetime
from time import sleep
import logging
import json
import sqlite3
import socket
import requests
import requests.packages.urllib3.util.connection as urllib3_cn
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Hack to for IPv4 for Requests, to avoid IPv6 timeout issues
def allowed_gai_family():
    family = socket.AF_INET    # force IPv4
    return family
 
urllib3_cn.allowed_gai_family = allowed_gai_family

# Setup database connection
con = sqlite3.connect("feditrends.db")
con.execute('pragma journal_mode=wal')
cur = con.cursor()

### STEP 1: EXTRACT
### First, we need to fetch the trending statuses from all the instances we wish to scan. We started by making sure we have a "statuses" table to ready to go in our SQLite database, then iterate through a list of instances in "instances.txt" and insert the fetched statues into the table.

# Create "statuses" table if it doesn't exist already
extract_create_sql = """
	CREATE TABLE IF NOT EXISTS statuses (
		url TEXT,
		created_at TEXT,
		content_text TEXT,
		reblogs_count INTEGER,
		favourites_count INTEGER,
		status_json JSON
	);
"""

cur.execute(extract_create_sql)
con.commit()

# Read list of instances from "instances.txt" file (one per line)
instances = [line.rstrip() for line in open('instances.txt')]

logging.info("Beginning snapshot")
  
# Iterate through instances, grab statuses and insert them in database
for instance in instances:

	logging.info("Processing %s", instance)

	statuses = []

	# Make the instance HTTP request using Requests
	try:

		# Construct URL
		statuses_url = "https://" + instance + "/api/v1/trends/statuses"

		# Loop 12 times for 12 * 40 = 480 statuses in total, per instance
		for i in range(0, 12):

			# Set request parameters
			params = {
				'limit': 40,
				'offset': i * 40
			}

			new_statuses = requests.get(url = statuses_url, params = params, headers = {'Connection': 'close'}, timeout=10)

			statuses = statuses + new_statuses.json()

			# Sleep for 100ms so we're not bombarding the server
			sleep(0.1)

		# Loop through statuses, extract data, and insert into database
		for index, status in enumerate(statuses, start=1):

			extract_insert_sql = """
				INSERT INTO statuses (url, created_at, content_text, reblogs_count, favourites_count, status_json) 
				VALUES (?, ?, ?, ?, ?, ?)
			"""

			statusRecord = {
				'url': status['url'],
				'created_at': status['created_at'],
				'content_text': json.dumps(BeautifulSoup(status['content'], 'html.parser').get_text(), ensure_ascii=False),
				'reblogs_count': int(status['reblogs_count']),
				'favourites_count': int(status['favourites_count']),
				'status_json': json.dumps(status, ensure_ascii=False),
			}

			cur.execute(extract_insert_sql, tuple(statusRecord.values()))
			con.commit()

	# Catch any HTTP exceptions from Requests
	except requests.exceptions.RequestException as e:
			logging.error("Error: %s", e)

	logging.info("Completed %s", instance)

logging.info("Snapshot complete")

### STEP 2: AGGREGATE
###  Now we have a fresh batch of statuses in the "statuses" table, plus any previously top-ranking statuses from the past 24 hours, the next step is to run an aggregate query across all these records and dump them into a temporary table "statuses_temp" which we'll then use to construct our search index table and overwrite the statuses table before the next run.

logging.info("Creating aggregate table")

aggregate_drop_sql = """
	DROP TABLE IF EXISTS statuses_temp;
"""

aggregate_create_sql = """
	CREATE TABLE statuses_temp AS

	SELECT 
		  url,
		  created_at,
		  content_text,
		  reblogs_count,
		  favourites_count,
		  status_json
	FROM
	(SELECT 
	  *,
	  row_number() over (
		partition by url 
		order by 
		  (reblogs_count + favourites_count) desc
	  ) as rownum 
	  FROM statuses) ranked
	WHERE ranked.rownum = 1
	AND datetime(created_at) >=datetime('now', '-24 Hour');
"""

cur.execute(aggregate_drop_sql)
cur.execute(aggregate_create_sql)
con.commit()
logging.info("Temporary aggregate table created")

### STEP 3: Index
###  Our aggregate table is created, so now we need to load the data into a new virtual table called "statuses_indexed" that is indexed for full-text search on the "context_text" column. This will provide a fast way to search and sort results for the API

logging.info("Preparing full-text search table")

# SQL to drop the old table and data
index_drop_sql = """
	DROP TABLE IF EXISTS statuses_indexed;
"""

# SQL to create the new table
index_create_sql = """
	CREATE VIRTUAL TABLE statuses_indexed
	USING FTS5(content_text, created_at UNINDEXED, reblogs_count UNINDEXED, favourites_count UNINDEXED, status_json UNINDEXED);
"""

cur.execute(index_drop_sql)
cur.execute(index_create_sql)
con.commit()

logging.info("Full-text search table cleared and ready to be populated")

# Fetch all statuses for insert
index_fetch_sql = """
	SELECT content_text, created_at, reblogs_count, favourites_count, status_json
	FROM statuses_temp;
"""

index_results = cur.execute(index_fetch_sql)
index_statuses = index_results.fetchall()

# Insert statuses into full-text search table
con.executemany(
    "INSERT INTO statuses_indexed (content_text, created_at, reblogs_count, favourites_count, status_json) VALUES (:content_text, :created_at, :reblogs_count, :favourites_count, :status_json);", index_statuses)

con.commit()

logging.info("Full-text search table populated")

### STEP 4: Clean-up
### Now that we're all done, we will overwrite the statuses table with the aggregated set, remove the temporary table and perform a VACUUM to free up disk space.

logging.info("Beginning clean-up process")

clean_sql = """
	BEGIN;

	DROP TABLE IF EXISTS statuses;

	CREATE TABLE statuses AS
	SELECT *
	FROM statuses_temp;

	DROP TABLE IF EXISTS statuses_temp;

	COMMIT;
"""

cur.executescript(clean_sql)
con.commit()

logging.info("Clean-up completed")
con.execute("VACUUM")
con.close()