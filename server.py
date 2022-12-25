import sqlite3
import json
from flask import Flask, request, Response, render_template

# Prepare Flask
app = Flask(__name__)

# Function to construct SQL query and return statuses from SQLite DB 
def fetch_statuses(order, hours, query):

	# Setup DB connection
	con = sqlite3.connect("feditrends.db")
	con.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
	con.execute('pragma journal_mode=wal')
	cur = con.cursor()

	# Construct SQL query
	sql = "SELECT status_json "
	sql+= "FROM statuses_indexed "
	sql+= "WHERE datetime(created_at) >=datetime('now', '-" + str(hours) + " Hour') "

	if query != "":
		sql+= "AND statuses_indexed MATCH '" + query + "' "

	if order == "pop":
		sql+= "ORDER BY (reblogs_count + favourites_count) DESC ";

	else:
		sql+= "ORDER BY created_at DESC "

	sql+= "LIMIT 100;";

	print(sql)

	statuses = cur.execute(sql)
	return statuses.fetchall()

# The /api endpoint, supporting ?order=X, ?hours=Y, and ?query=Z parameters
@app.route("/api")
def api_response():

	# An errors list we'll append to and render back to user if input is malformed
	errors = []

	# Validate ?order= variable and use default if not present
	order = request.args.get('order', 'pop', type=str)
	if not (order in ["pop", "chrono"]):
		errors.append("Unsupported ?order= value. Use either =pop or =chrono.")

	# Validate ?hours= variable and use default if not present
	hours = request.args.get('hours', 3, type=int)
	if not (hours >= 1 and hours <= 24):
		errors.append("Unsupported ?hours= value. Use a value between 1 and 24.")

	# Validate ?query= variable and use default if not present
	query = request.args.get('query', '', type=str)
	if query != '':
		if not (query.isalnum() is True and len(query) >= 2 and len(query) <= 25):
			errors.append("Unsupported ?query= value. Use a single alphanumeric keyword between 2 and 25 characters in length, with no spaces or special characters.")

	# There are errors, stop here and render them back to the user as JSON
	if len(errors) > 0:
		return errors

	# No errors, proceed with making the SQL query and returning results as JSON
	else:
		statuses = fetch_statuses(order, hours, query)
		rendered = render_template("statuses.json", statuses=statuses)
		json_response = Response(response=rendered, status=200, mimetype="application/json")
		json_response.headers["Content-Type"] = "application/json; charset=utf-8"
		return json_response

# Defualt root "/" path, returns HTML from static "statuses.html" file. This is setup as an example only. In production, you will want to rework this to serve the file (and all static files) from a web server (eg. Nginx) rather than via Flask.
@app.route("/")
def index():
    return """
    	<h1>feditrends example</h1>
    	<p>You can interact directly with the API at <a href="/api">/api</a> or use the sample user interface at <a href="/static/statuses.html">/static/statuses.html</a></p>
    	<p>In production, you'll want to put this all behind a more robust web server where you can configure your paths however you like</p>
    """