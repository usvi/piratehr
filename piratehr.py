#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, Blueprint, request, Response, session, g, redirect, url_for, abort, send_file
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

def json_response(data, status = 200, **kwargs):
	"""All responses sent by the API should be formatted with this, e.g.
	return json_response(dict(somefield=123, otherfield='foo'))
	return json_response({'description':'No permission to access the requested user'}, 403)
	return json_response(dict(description='...'), 401, {'WWW-Authenticate': 'Basic realm="JSON auth required"'})
	"""
	# Conversion function is needed for datetime objects :/
	def jsonconvert(obj):
		if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date): return obj.isoformat()
		return str(obj)
	resp = Response(json.dumps(data, default=jsonconvert), status=status, mimetype='application/json')
	for k, v in kwargs.get('headers', {}).items(): resp.headers[k] = v
	return resp

class init_error_responses_327823:  # class abused to bound variables
	"""Make error responses use JSON."""
	from werkzeug.exceptions import default_exceptions
	from werkzeug.exceptions import HTTPException
	make_json_error = lambda ex: json_response(dict(description=str(ex)), ex.code)
	for code in default_exceptions.iterkeys():
		if code != 500: app.errorhandler(code)(make_json_error)
	# Use HTTP Basic auth (json object in password field)
	app.errorhandler(401)(lambda ex: json_response(
	  dict(description='Authenticate with HTTP Basic json:{auth object}'), 401,
	  {'WWW-Authenticate': 'Basic realm="JSON auth required"'}
	))

def sleep_until(t):
	"""Sleep until datetime t (utc)"""
	timedelta = t - datetime.datetime.utcnow()
	duration = timedelta.seconds + timedelta.microseconds / 1E6 + timedelta.days * 86400
	if duration > 0: time.sleep(duration)
	else: app.logger.warn('sleep_until called ' + duration + ' s after the deadline')

def requires_auth(f):
	"""A decorator to verify that there is a valid user (g.user)
	Just add @requires_auth between your route and function
	"""
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.authorization
		if not auth or auth.username != 'json': return authenticate()
		g.user = appdb.Auth.authenticate(json.loads(auth.password))
		if not g.user: return authenticate()
		return f(*args, **kwargs)
	return decorated

def request_fields(*req_args):
	"""A decorator to verify that request data was supplied and that the keys
	listed exist (values may still be nulls). Just add @request_fields() or
	@request_fields('field1', 'field2') right before your function.
	"""
	def decorator(f):
		@wraps(f)
		def decorated(*args, **kwargs):
			if not g.req: return json_response(dict(description='JSON object must be passed as HTTP body with this request'), 422)
			missing = []
			for arg in req_args:
				if not g.req.has_key(arg): missing.add(arg)
			if missing: return json_response(dict(description='Mandatory request fields missing', missing_fields=missing), 422)
			return f(*args, **kwargs)
		return decorated
	return decorator
	
# The entire REST/JSON API
api = Blueprint("api", __name__, url_prefix="/api")

@api.before_request
def before_request():
	g.req = None
	g.user = None
	try: g.req = request.json
	except: g.req = request.values  # No JSON? Try HTTP form data
	if app.config['DEBUG']:
		app.logger.debug('  | API before_request processing:\n  |   ' + str(request) + '\n  |   ' + (json.dumps(g.req)[0:300] if g.req else 'No request data'))

@api.after_request
def after_request(resp):
	if app.config['DEBUG'] or resp.status >= 400: 
		datalen = resp.headers['Content-Length']
		text = '  |>>> ' + resp.status + '  '
		for k, v in resp.headers: text += k + ': ' + v + '  '
		text += '\n' + (resp.data if datalen < 600 else resp.data[0:200] + '(…)' + resp.data[-50:])
		app.logger.debug(text)
	return resp

@api.route("/new_user.json", methods=["POST"])
def create_user():
	req = g.req
	if not req: abort(422)
	user = appdb.User.create(
		legal_name = req['legal_name'],
		residence = req['residence'],
		phone = req['phone'],
		email = req['email'],
		dob = req['dob']
	)
	if not user: abort(422)
	app.logger.debug("piratehr.py: new user legal_name:" + user.legal_name + "\n" + "piratehr.py: new user uuid:" + user.uuid)
	ret = {
		'uuid': user.uuid,
		'api_url': url_for('.get_user', user_id = user.uuid, _external = True),
		'uuid_url': url_for('static', filename = "uuid/" + user.uuid, _external = True)  # UUID URIs (handled by UI in a user-friendly way)
	}
	return json_response(ret, 201, {'Location': ret['api_url']})

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
	return json_response(ret)

@api.route("/user_<user_id>.json", methods=["PUT"])
@requires_auth
def update_user(user_id):
	user = appdb.User.find(user_id)
	if not user or user != g.user: abort(403)
	if user.update(g.req): return json_response(dict(description='User information updated'))
	else: abort(422)

@api.route("/auth.json", methods=["POST"])
@request_fields('type')
def auth():
	# For security reasons we delay all responses 500 ms from this point
	responsetime = datetime.datetime.utcnow() + datetime.timedelta(milliseconds = 500)
	reqtype = g.req['type']
	if reqtype == 'login_password':
		if not g.req.has_field('login') or not g.req.has_field('password'): abort(422)
		user = appdb.User.find_by_email(g.req['login']) # FIXME: Actually verify the password
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
		if not auth: abort(403)
		return json_response(ret)
	elif reqtype == 'request_reset':
		email = g.req.get('email')
		if email:  # Reset by email
			# TODO/SECURITY: Add request to queue instead of sending it to avoid information leakage by measuring request time
			reset_list = appdb.Auth.reset_token_email(auth_request['email'])
			messenger.send_password_reset_emails(reset_list, request.url_root + "reset/")
		else: abort(422)  # No other reset modes supported at this time
		sleep_until(responsetime)
		# Always return ok here: Attacker must not get knowledge about whether we have the email or not
		return json_response(dict(description='Password reset requested'), 202)
	else:
		abort(422)

@api.route("/organization.json", methods=["PUT"])
@requires_auth
@request_fields('legal_name', 'friendly_name')
def organization_put():
	organization = appdb.Organization.create(
		legal_name=g.req['legal_name'],
		friendly_name=g.req['friendly_name'],
		parent_id=g.req.get('parent_id')
	)
	if not organization: abort(422)
	ret = {
		'id': organization.id,
		'parent_id': organization.parent_id,
		'legal_name': organization.legal_name,
		'friendly_name': organization.friendly_name
	}
	return json_response(ret, 201)

@api.route("/organization.json", methods=["GET"])
def organization_get_all():
	# FIXME: Proper error checking here?
	organizations = appdb.Organization.get_all()
	ret = []   # FIXME: Always wrap JSON in {} (security reasons)
	for organization in organizations:
		tuple = {
			'id': organization.id,
			'parent_id': organization.parent_id,
			'legal_name': organization.legal_name,
			'friendly_name': organization.friendly_name,
			'perma_name': organization.perma_name
			}
		ret.append(tuple)
	return json_response(ret)

@api.route("/organization_<perma_name>.json", methods=["GET"])
def organization_get(perma_name):
	if not perma_name: return "Invalid organization data", 422
	# FIXME: Proper error checking here?
	ret = {}
	# Main organization (from URL)
	main_org = appdb.Organization.find_by_perma(perma_name)
	if not main_org: abort(404)
	ret['main_org'] = {
		'id': main_org.id,
		'parent_id': main_org.parent_id,
		'legal_name': main_org.legal_name,
		'friendly_name': main_org.friendly_name,
		'perma_name': main_org.perma_name
	}
	# Parent organization
	parent_org = main_org.get_parent()
	if parent_org:
		ret['parent_org'] = {
			'id': parent_org.id,
			'parent_id': parent_org.parent_id,
			'legal_name': parent_org.legal_name,
			'friendly_name': parent_org.friendly_name,
			'perma_name': parent_org.perma_name
		}
	# Child organizations
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
	return json_response(ret)


@api.route("/settings.json", methods=["PUT"])
@requires_auth
@request_fields('key', 'value')
def settings_put():
	appdb.Settings.make_setting(g.req['key'], g.req['value'])
	return json_response(dict(description="Setting updated"))

@api.route("/settings.json", methods=["GET"])
@requires_auth
def settings_get():
	ret = {}
	# TODO: Read settings from database
	return json_response(ret)


if __name__ == '__main__':
	app.register_blueprint(api)
	app.run()
