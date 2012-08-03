#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Blueprint, request, Response, g, url_for, abort
from util import *
import authentication
import appdb
import messenger

# The entire REST/JSON API
api = Blueprint("api", __name__, url_prefix="/api")

@api.before_request
def before_request():
	g.req = None
	g.user = None
	try: g.req = request.json
	except: pass
	if not g.req: g.req = request.values  # No JSON? Try HTTP form data
	if g.config['DEBUG']:
		g.logger.debug('  | API before_request processing:\n  |   ' + str(request) + '\n  |   ' +
			(json.dumps(g.req)[0:300] if g.req else 'No request data'))

@api.after_request
def after_request(resp):
	if g.config['DEBUG'] or resp.status >= 400: 
		datalen = int(resp.headers['Content-Length'])
		text = '  |>>> ' + resp.status + '  '
		for k, v in resp.headers: text += k + ': ' + v + '  '
		text += '\n' + (resp.data if datalen < 600 else resp.data[0:200] + '(…)' + resp.data[-50:])
		g.logger.debug(text)
	return resp

@api.route("/new_user.json", methods=["POST"])
@request_fields('legal_name', 'residence', 'dob')
def create_user():
	user = appdb.User.create(
		legal_name = g.req['legal_name'],
		residence = g.req['residence'],
		phone = g.req.get('phone'),
		email = g.req.get('email'),
		dob = g.req['dob']
	)
	if not user: abort(422)
	authentication.set_password(user, 'FIXME')  # FIXME: Do not set password by default
	ret = {
		'uuid': user.uuid,
		'api_url': url_for('.get_user', user_id = user.uuid, _external = True),
		'uuid_url': url_for('static', filename = "uuid/" + user.uuid, _external = True)  # UUID URIs (handled by UI in a user-friendly way)
	}
	return json_response(ret, 201, headers=dict(Location=ret['api_url']))

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
def auth_post():
	reqtype = g.req['type']
	if reqtype == 'login_password':
		login = g.req.get('login')
		password = g.req.get('password')
		if not login or not password: abort(422)
		auth_obj = authentication.login_password(login, password)
		if not auth_obj: abort(403)
		return json_response(auth_obj)
	elif reqtype == 'request_reset':
		email = g.req.get('email')
		if email:  # Reset by email
			# TODO/SECURITY: Add request to queue instead of sending it to avoid information leakage by measuring request time
			reset_list = appdb.Auth.reset_token_email(auth_request['email'])
			messenger.send_password_reset_emails(reset_list, request.url_root + "reset/")
		else: abort(422)  # No other reset modes supported at this time
		# Always return ok here: Attacker must not get knowledge about whether we have the email or not
		return json_response(dict(description='Password reset requested'), 202)
	else:
		abort(422)

@api.route("/organization.json", methods=["PUT"])
@requires_auth
@request_fields('legal_name', 'friendly_name')
def organization_put():
	parent_id = g.req['parent_id']
	if type(parent_id) != int:
		parent_id = None
	organization = appdb.Organization.create(
		legal_name=g.req['legal_name'],
		friendly_name=g.req['friendly_name'],
		parent_id=parent_id
	)
	if not organization: abort(422)
	ret = {
		'id': organization.id,
		'parent_id': organization.parent_id,
		'legal_name': organization.legal_name,
		'friendly_name': organization.friendly_name,
		'perma_name': organization.perma_name
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
	
@api.route("/I_accidentally_the_whole_database.json", methods=['DELETE'])
def clear_database():
	appdb.clear_database();
	return json_response({})

