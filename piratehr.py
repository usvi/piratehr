#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, send_file
import json
import appdb
import datetime
import messenger


# create our little application :)
app = Flask(__name__, static_path="/")
app.config.from_object(__name__)
app.config.from_pyfile('config.py', silent=True)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
appdb.init(app);

# Display static files at root
if app.config['DEBUG']:
	from werkzeug import SharedDataMiddleware
	import os
	app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
		'/': os.path.join(os.path.dirname(__file__), 'static')
	})

# Static routing for index.html
@app.route("/")
@app.route("/register/")
@app.route("/user/")
@app.route("/user/<path:path>")
@app.route("/org/")
@app.route("/org/<path:path>")
def index(*args, **kwargs):
	return send_file("static/index.html")

# Subclass a RestResource and configure it
api = Blueprint("api", __name__, url_prefix="/api")

@api.route("/new_user.json", methods=["POST"])
def create_user():
	
	app.logger.debug("HEADERS:" + repr(request.headers) + "\n" + "DATA:" + request.data + "\n" + "VALUES:" + repr(request.values) + "\n" + "JSON:" + repr(request.json))
	user_data = unpack_request(request)
	if not user_data: return "Invalid user data", 422
	user = appdb.User.create(
		legal_name = user_data['legal_name'],
		residence = user_data['residence'],
		phone = user_data['phone'],
		email = user_data['email'],
		dob = user_data['dob']
	)
	if not user: return "Invalid user data", 422
	app.logger.debug("piratehr.py: new user legal_name:" + user.legal_name + "\n" + "piratehr.py: new user uuid:" + user.uuid)
	ret = {
		'uuid': user.uuid,
		'url': url_for('static', filename = "user/" + user.uuid, _external = True)
	}
	return json.dumps(ret), 201, {'Location': ret['url'] }

@api.route("/user_<user_id>.json", methods=["GET"])
def get_user(user_id):
	user = appdb.User.find(user_id)
	if user == None: abort(404)
	# TODO: The following code should be
	#   (a) eliminated if possible, or at least
	#   (b) moved elsewhere (appdb.py?)
	ret = {
		'uuid': user.uuid,
		'login': user.login,
		'name': user.name,
		'legal_name': user.legal_name,
		'residence': user.residence,
		'addresses': None,
		'phone': user.phone,
		'email': user.email,
		'dob': user.dob,
		'ssn': user.ssn,
		'location': user.location,
		'joined': user.joined,
		'last_seen': user.last_seen
	}
	print user.legal_name
	# Conversion function is needed for datetime objects :/
	jsonconvert = lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else None
	return json.dumps(ret, default=jsonconvert), 200

@api.route("/user_<user_id>.json", methods=["PUT"])
def update_user(user_id):
	# do your stuff here
	return "PUT" + user_id, 200

@api.route("/I_accidentally_the_whole_database", methods=["DELETE"])
def clear_database():
	appdb.clear_database()
	return "DELETED", 200

@api.route("/auth.json", methods=["POST"])
def auth_user():
	auth_request = unpack_request(request)
	if not auth_request: return "Invalid auth request", 422
	if auth_request['type'] == "request_reset" and auth_request['email'] != None: # Asking for password reset by email.
		reset_tuples = appdb.Auth.reset_token_email(auth_request['email'])
		

@api.route("/debug_<debug_param>", methods=["DEBUG"])
def do_debug(debug_param):
	print "Entering debug with param " + debug_param
	#appdb.Auth.find_by_email(debug_param, "pw_reset")
	reset_list = appdb.Auth.reset_token_email(debug_param)
	messenger.send_password_reset_emails(reset_list)
	print "Exiting debug"
	return "DEBUG", 200

# you can use the "need_auth" decorator to do things for you
#@need_auth(authentifier_callable, "project") # injects the "project" argument if authorised
def delete(self, user_id):
	# do your stuff
	return "DELETED", 200


def unpack_request(input_request):
	if input_request.json == None:
		if input_request.values:
			return input_request.values
		else:
			return None
	else: # Unpack json
		return input_request.json


if __name__ == '__main__':
	app.register_blueprint(api)
	app.run()
