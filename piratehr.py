#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, send_file
import json
import appdb
import datetime
import time
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
	req = g.req
	if not req: return "Invalid user data", 422
	user = appdb.User.create(
		legal_name = req['legal_name'],
		residence = req['residence'],
		phone = req['phone'],
		email = req['email'],
		dob = req['dob']
	)
	if not user: return "Invalid user data", 422
	app.logger.debug("piratehr.py: new user legal_name:" + user.legal_name + "\n" + "piratehr.py: new user uuid:" + user.uuid)
	ret = {
		'uuid': user.uuid,
		'api_url': url_for('.get_user', user_id = user.uuid, _external = True),
		'user_url': url_for('static', filename = "user/" + user.uuid, _external = True)
	}
	return json.dumps(ret), 201, {'Location': ret['api_url'] }

@api.route("/user_<user_id>.json", methods=["PROPFIND"])
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

@api.before_request
def before_request():
	app.logger.debug(request)
	g.req = None
	g.user = None
	try: g.req = request.json
	except: pass  # Ignore anything raised by request.json
	app.logger.warn(type(request.json));
	g.req = g.req or request.values
	app.logger.warn(type(g.req));
	if g.req:
		auth = g.req.get('auth', None)
		app.logger.warn(type(auth))
		if auth:
			g.user = appdb.Auth.authenticate(json.loads(auth))
			if not g.user: return "Invalid authentication", 401

def sleep_until(t):
	timedelta = t - datetime.datetime.utcnow()
	duration = timedelta.seconds + timedelta.microseconds / 1E6 + timedelta.days * 86400
	if duration > 0: time.sleep(duration)
	else: app.logger.warn('sleep_until called ' + duration + ' s after the deadline')

@api.route("/auth.json", methods=["POST"])
def auth():
	req = g.req
	if not req: return "Invalid auth request", 422
	responsetime = datetime.datetime.utcnow() + datetime.timedelta(milliseconds = 1500)
	login = req['login']
	if req['type'] == "login_password":
		if not req['login'] or not req['password']: return "Fields login or password missing", 422
		user = appdb.User.find_by_email(login)
		auth = None
		ret = None
		if (len(user) == 1):
			user = user[0]
			auth = appdb.Auth.create_session(user)
			ret = {
				'auth': {
					'token': auth.token_content,
					'uuid': user.uuid,
					'name': user.name
				}
			}
		sleep_until(responsetime)
		if not auth: return "Authorization failed", 403
		return json.dumps(ret), 200
	elif req['type'] == "request_reset":
		if auth_request['email'] != None: # Asking for password reset by email.
			# TODO/SECURITY: Add request to queue instead of sending it to avoid information leakage by measuring request time
			reset_list = appdb.Auth.reset_token_email(auth_request['email'])
			messenger.send_password_reset_emails(reset_list, request.url_root + "reset/")
		sleep_until(responsetime)
		# Always return ok here: Attacker must not get knowledge about whether we have the email or not
		return json.dumps({"status":"Password reset requested"}), 202
	else:
		return "Auth type not specified or not supported", 422


@api.route("/organization.json", methods=["PUT"])
def organization_put():
	req = g.req
	if not req or req['legal_name'] == None: return "Invalid organization data", 422
	organization = appdb.Organization.create(legal_name=req['legal_name'], friendly_name=req['friendly_name'])
	if not organization: return "Invalid organization data", 422
	print "New organization: " + organization.legal_name + "/" + organization.friendly_name
	ret = {
		'id': organization.id,
		'parent_id': organization.parent_id,
		'legal_name': organization.legal_name,
		'friendly_name': organization.friendly_name
	}
	return json.dumps(ret), 201


@api.route("/organization.json", methods=["GET"])
def organization_get():
	print "organization_get"
	# FIXME: Proper error checking here?
	organizations = appdb.Organization.get_all()
	ret = []
	for organization in organizations:
		tuple = {
			'id': organization.id,
			'parent_id': organization.parent_id,
			'legal_name': organization.legal_name,
			'friendly_name': organization.friendly_name
			}
		ret.append(tuple)
	return json.dumps(ret), 200



@api.route("/settings.json", methods=["PUT"])
def settings_put():
	print "settings_put"
	req = g.req
	if not req: return "Invalid settings data", 422
	if req['key'] == None or req['value'] == None: return "Invalid settings data", 422
	appdb.Settings.make_setting(req['key'], req['value'])
	return "PUT", 200 # FIXME: Stricter error checks?, JSON response

@api.route("/settings.json", methods=["GET"])
def settings_get():
	print "settings_get()" #
	return "GET", 200 # FIXME: JSON response

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


if __name__ == '__main__':
	app.register_blueprint(api)
	app.run()
