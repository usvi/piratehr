#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, send_file
from functools import wraps
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

# Subclass a RestResource and configure it
api = Blueprint("api", __name__, url_prefix="/api")

# A decorator to verify that there is a valid user (g.user)
# Just add @requires_auth between your route and function
def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.authorization
		if not auth or auth.username != 'json': return authenticate()
		g.user = appdb.Auth.authenticate(json.loads(auth.password))
		if not g.user: return authenticate()
		return f(*args, **kwargs)
	return decorated
    
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
		'uuid_url': url_for('static', filename = "uuid/" + user.uuid, _external = True)  # UUID URIs (handled by UI in a user-friendly way)
	}
	return json.dumps(ret), 201, {'Location': ret['api_url'] }

@api.route("/user_<user_id>.json", methods=["GET"])
@requires_auth
def get_user(user_id):
	user = appdb.User.find(user_id)
	if not user or user != g.user: abort(403)
	# TODO: The following code should be
	#   (a) eliminated if possible, or at least
	#   (b) moved elsewhere (appdb.py?)
	ret = {
		'uuid': user.uuid,
		'api_url': url_for('.get_user', user_id = user.uuid, _external = True),
		'uuid_url': url_for('static', filename = "uuid/" + user.uuid, _external = True),
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
@requires_auth
def update_user(user_id):
	# do your stuff here
	return "PUT" + user_id, 200

@api.route("/I_accidentally_the_whole_database", methods=["DELETE"])
#@requires_auth
def clear_database():
	appdb.clear_database()
	return "DELETED", 200

def authenticate():
	"""Sends a 401 response that enables basic auth"""
	return json.dumps({'description':'You need to login username=json, JSON auth in password'}), 401,
	{'WWW-Authenticate': 'Basic realm="JSON auth required"', 'Content-Type': 'application/json'}

@api.before_request
def before_request():
	app.logger.debug(request)
	g.req = None
	g.user = None
	try: g.req = request.json
	except: pass  # Ignore anything raised by request.json
	g.req = g.req or request.values

def sleep_until(t):
	timedelta = t - datetime.datetime.utcnow()
	duration = timedelta.seconds + timedelta.microseconds / 1E6 + timedelta.days * 86400
	if duration > 0: time.sleep(duration)
	else: app.logger.warn('sleep_until called ' + duration + ' s after the deadline')

@api.route("/auth.json", methods=["POST"])
def auth():
	req = g.req
	if not req: return "Invalid auth request", 422
	responsetime = datetime.datetime.utcnow() + datetime.timedelta(milliseconds = 500)
	login = req['login']
	if req['type'] == "login_password":
		if not req['login'] or not req['password']: return "Fields login or password missing", 422
		user = appdb.User.find_by_email(login) # FIXME: Actually verify the password
		auth = None
		ret = None
		if (len(user) == 1):
			user = user[0]
			auth = appdb.Auth.create_session(user)
			ret = {
				'token': auth.token_content,
				'uuid': user.uuid,
				'name': user.name
			}
		# TODO: if len(user) > 1 reset all their passwords
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
@requires_auth
def organization_put():
	req = g.req
	if not req or req.get('legal_name') == None or req.get('friendly_name') == None: return "Invalid organization data", 422
	organization = appdb.Organization.create(legal_name=req.get('legal_name'), friendly_name=req.get('friendly_name'), parent_id=req.get('parent_id'))
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
def organization_get_all():
	print "organization_get_all"
	# FIXME: Proper error checking here?
	organizations = appdb.Organization.get_all()
	ret = []
	for organization in organizations:
		tuple = {
			'id': organization.id,
			'parent_id': organization.parent_id,
			'legal_name': organization.legal_name,
			'friendly_name': organization.friendly_name,
			'perma_name': organization.perma_name
			}
		ret.append(tuple)
	return json.dumps(ret), 200

@api.route("/organization_<perma_name>.json", methods=["GET"])
def organization_get(perma_name):
        if not perma_name: return "Invalid organization data", 422
        # FIXME: Proper error checking here?
        ret = {}
        main_org = appdb.Organization.find_by_perma(perma_name)
        if not main_org: return "No such organization", 404
        ret['main_org'] = {
                        'id': main_org.id,
                        'parent_id': main_org.parent_id,
                        'legal_name': main_org.legal_name,
                        'friendly_name': main_org.friendly_name,
                        'perma_name': main_org.perma_name
                        }
        parent_org = main_org.get_parent()
        if parent_org:
                ret['parent_org'] = {
                        'id': parent_org.id,
                        'parent_id': parent_org.parent_id,
                        'legal_name': parent_org.legal_name,
                        'friendly_name': parent_org.friendly_name,
                        'perma_name': parent_org.perma_name
                        }
        all_child_orgs = main_org.get_children()
        if all_child_orgs:
                ret['child_orgs'] = []
                for child_org in all_child_orgs:
                        ret['child_orgs'].append({
                                        'id': child_org.id,
                                        'parent_id': child_org.parent_id,
                                        'legal_name': child_org.legal_name,
                                        'friendly_name': child_org.friendly_name,
					'perma_name': child_org.perma_name
                                        })
        return json.dumps(ret), 200


@api.route("/settings.json", methods=["PUT"])
@requires_auth
def settings_put():
	print "settings_put"
	req = g.req
	if not req: return "Invalid settings data", 422
	if req['key'] == None or req['value'] == None: return "Invalid settings data", 422
	appdb.Settings.make_setting(req['key'], req['value'])
	return "PUT", 200 # FIXME: Stricter error checks?, JSON response

@api.route("/settings.json", methods=["GET"])
@requires_auth
def settings_get():
	print "settings_get()" #
	return "GET", 200 # FIXME: JSON response


if __name__ == '__main__':
	app.register_blueprint(api)
	app.run()
