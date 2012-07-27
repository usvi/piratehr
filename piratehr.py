#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, g, send_file
from util import init_error_responses
from api import api
import appdb

# create our little application :)
app = Flask(__name__, static_path="/")
app.config.from_object(__name__)
app.config.from_pyfile('config.py', silent=True)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
app.register_blueprint(api)
init_error_responses(app);
appdb.init(app);

# Share per-request global variables here
@app.before_request
def before_request():
	g.logger = app.logger
	g.config = app.config

# Some helpers to simplify deploying in debug mode
# For performance reasons routing static content must be done externally when installed
if app.config['DEBUG']:
	# Display static files at root
	from werkzeug import SharedDataMiddleware
	import os
	app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
		'/': os.path.join(os.path.dirname(__file__), 'static')
	})
	# Static routing for index.html
	@app.route("/")
	@app.route("/uuid/<string:uuid>")
	@app.route("/register/")
	@app.route("/user/")
	@app.route("/user/<path:path>")
	@app.route("/memberships/")
	@app.route("/memberships/<path:path>")
	@app.route("/org/")
	@app.route("/org/<path:path>")
	def index(*args, **kwargs):
		return send_file("static/index.html")

if __name__ == '__main__':
	app.run()

