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
		'api_url': url_for('.get_user', user_id = user.uuid, _external = True),
		'user_url': url_for('static', filename = "user/" + user.uuid, _external = True)
	}
	return json.dumps(ret), 201, {'Location': ret['api_url'] }

@api.route("/user_<user_id>.json", methods=["GET"])
def get_user(user_id):
	user = appdb.User.find(user_id)
	if user == None: abort(404)
	# TODO: The following code should be
	#   (a) eliminated if possible, or at least
	#   (b) moved elsewhere (appdb.py?)
	ret = {
		'uuid': user.uuid,
		'api_url': url_for('.get_user', user_id = user.uuid, _external = True),
		'user_url': url_for('static', filename = "user/" + user.uuid, _external = True),
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
	if not auth_request: return "Invalid auth data", 422
	if auth_request['type'] == "request_reset":
		if auth_request['email'] != None: # Asking for password reset by email.
			reset_list = appdb.Auth.reset_token_email(auth_request['email'])
			messenger.send_password_reset_emails(reset_list, request.url_root + "reset/")
		return "POST", 200 # Always return ok here: Attacker must not get knowledge about whether we have the email or not
	else:
		return "Invalid auth data", 422


@api.route("/organization.json", methods=["PUT"])
def organization_put():
	print "organization_put"
	organization_data = unpack_request(request)
	if organization_data == None or organization_data['legal_name'] == None: return "Invalid organization data", 422
	organization = appdb.Organization.create(legal_name=organization_data['legal_name'], friendly_name=organization_data['friendly_name'])
	if not organization: return "Invalid organization data", 422
	print "New organization: " + organization.legal_name + "/" + organization.friendly_name
	ret = {
		'legal_name': organization.legal_name,
		'friendly_name': organization.friendly_name
	}
	return json.dumps(ret), 201


@api.route("/settings.json", methods=["PUT"])
def settings_put():
	print "settings_put"
	settings_data = unpack_request(request)
	if settings_data == None: return "Invalid settings data", 422
	if settings_data['key'] == None or settings_data['value'] == None: return "Invalid settings data", 422
	appdb.Settings.make_setting(settings_data['key'], settings_data['value'])
	return "PUT", 200 # FIXME: Stricter error checks?

@api.route("/settings.json", methods=["GET"])
def settings_get():
	print "settings_get()" #
	return "GET", 200

@api.route("/debug_<debug_param>", methods=["DEBUG"])
def do_debug(debug_param):
	print "Entering debug with param " + debug_param
	#appdb.Auth.find_by_email(debug_param, "pw_reset")
	#reset_list = appdb.Auth.reset_token_email(debug_param)
	#messenger.send_password_reset_emails(reset_list)
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
