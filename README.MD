# Trending Statuses

This app will fetch trending statuses from a specified list of Mastodon instances, write them to a SQLite database in an aggregated, full-text search index, then expose a simple REST API that serves the statuses back in JSON. A sample user interface written in HTML/CSS/JS is provided for interacting with the API. 

## How to install & run

This has been tested on Python 3.10.6 but not extensively on other versions. Your mileage may vary. 

### 1. Install dependencies

`pip3 install -r requirements.txt`

### 2. Configure instance list

*(Optional)* Configure the instances you wish to process trends from in `instances.txt`. One instance per line, and just the hostname without protocol, eg. "mastodon.social". Usually, the bigger and more federated the instances, the better. The more you add, the longer processing will take however. Around 10-15 big instances works well. **The file in this repo already includes default instances, and you can leave this as-is if you'd like.** There is a lot of overlap across instances, but the processing step will handle consolidating that.

### 3. Run a snapshot

Run your first snapshot:

`python3 process.py`

This will boostrap the database and run an initial snapshot across the instances specified in `instances.txt`. The results will then be consolidated down and inserted into a full-text search indexed table which the API uses. 

In production, you'll want to periodically re-run `process.py` so that your database stays up-to-date. Running it every 15 minutes using `cron` seems to work well.

### 4. Run API server:

Run the local development server using Flask:

`flask --app server run`

You can then navigate to the URL returned in your terminal (eg. [http://127.0.0.1:5000/](http://127.0.0.1:5000/)). The API results will be rendered at the `/api` endpoint and you can view the sample user interface pointing at the API at `/static/statuses.html`

In production, you'll want to put this Flask app behind a WSGI server such as Gunicorn or Waitress. For more details, [visit the Flask docs.](https://flask.palletsprojects.com/en/2.2.x/deploying/)

## The MIT License (MIT)
Copyright (c) 2022 Jackson Palmer

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

