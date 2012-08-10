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
@request_fields('name', 'residence', 'dob')
def create_user():
	user = appdb.User.create(
		legal_name = g.req['name'],
		residence = g.req['residence'],
		phone = g.req.get('phone'),
		email = g.req.get('email'),
		dob = g.req['dob']
	)
	if not user: return json_response(dict(description='User could not be created. Check your input data.'), 422)
	ret = {
		'uuid': user.uuid,
		'api_url': url_for('.get_user', user_id = user.uuid, _external = True),
		'uuid_url': url_for('static', filename = "uuid/" + user.uuid, _external = True),  # UUID URIs (handled by UI in a user-friendly way)
		'auth': authentication.create_session(user)
	}
	return json_response(ret, 201, headers=dict(Location=ret['api_url']))

@api.route("/user_<user_id>.json", methods=["GET"])
@requires_auth
def get_user(user_id):
	user = appdb.User.find(user_id)
	if not user or user != g.user: abort(403)
	addresses = appdb.Address.get_by_user(user)
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
		'last_seen': user.last_seen,
		'addresses': addresses,
	}
	return json_response(ret)

@api.route("/user_<user_id>.json", methods=["PUT"])
@requires_auth
def update_user(user_id):
	user = appdb.User.find(user_id)
	if not user or user != g.user: abort(403)
	if user.update(g.req): return json_response(dict(description='User information updated'))
	else: return json_response(dict(description='User could not be updated. Check your input data.'), 422)

@api.route("/auth.json", methods=["POST"])
@request_fields('type')
def auth_post():
	reqtype = g.req['type']
	if reqtype == 'login_password':
		login = g.req.get('login')
		password = g.req.get('password')
		if not login or not password:
			return json_response(dict(description='Mandatory request fields missing',missing_fields=['login','password']), 422)
		auth_obj = authentication.login_password(login, password)
		if not auth_obj: abort(403)
		return json_response(auth_obj)
	elif reqtype == 'login_token':
		token = g.req.get('token')
		auth_obj = authentication.login_token(token)
		if not auth_obj: abort(403)
		return json_response(auth_obj)
	else:
		return json_response(dict(description='Invalid type requested.'), 422)

@api.route("/auth_change_password.json", methods=["POST"])
@requires_auth
@request_fields('uuid', 'new_password')
def auth_change_password():
	uuid = g.req.get('uuid')
	new_password = g.req.get('new_password')
	new_password_again = g.req.get('new_password_again');
	if not uuid: return json_response(dict(description='Field uuid must be specified'), 422);
	user = appdb.User.find(uuid)
	if not user or user.id != g.user.id: abort(403)  # TODO: Access control to allow admins to change other users' passwords?
	if not new_password: return json_response(dict(description='Field new_password must be specified'), 422);
	if g.req.has_key('new_password_again') and new_password_again != new_password:
		return json_response(dict(description='Passwords do not match'), 422)
	if len(new_password) < 8: return json_response(dict(description='Passwords must be at least 8 characters long'), 422)
	authentication.set_password(user, new_password)
	return json_response(dict(description='Password set'))


@api.route("/auth_reset.json", methods=["POST"])
@request_fields('email')
def auth_reset():
	# TODO/SECURITY: Add request to queue instead of sending it to avoid information leakage by measuring request time
	reset_list = appdb.Auth.reset_token_email(g.req['email'])
	messenger.send_password_reset_emails(reset_list, url_for('static', filename = 'reset/', _external = True))
	# Always return ok here: Attacker must not get knowledge about whether we have the email or not
	return json_response(dict(description='Password reset requested'), 202)


@api.route("/memberships.json", methods=["GET"])
@requires_auth
def membership_get_all():
	memberships = {}
	for org in appdb.Organization.get_all():
		tuple = {
			'legal_name': org.legal_name,
			'friendly_name': org.friendly_name,
			'perma_name': org.perma_name,
			'status': 'null'
		}
		memberships[org.id] = tuple
	for membership,memorg in appdb.Membership.find_by_uuid(g.user.uuid):
		tuple = {
			'legal_name': memorg.legal_name,
			'friendly_name': memorg.friendly_name,
			'perma_name': memorg.perma_name,
			'status': membership.status
		}
		memberships[memorg.id] = tuple
	return json_response(memberships, 200)

@api.route("/membership_<org_perma_name>.json", methods=["POST"])
@requires_auth
@request_fields('operation')
def membership_change(org_perma_name):
	# FIXME: Check errors actually
	if g.req['operation'] == 'apply':
		appdb.Membership.add(org_perma_name, g.user.uuid)
		return json_response(dict(description='Test.'), 202)
	if g.req['operation'] == 'unsubscribe':
		appdb.Membership.delete_status(org_perma_name, g.user.uuid, 'unsubscribed')
		return json_response(dict(description='Test.'), 200)
	if g.req['operation'] == 'cancel':
		appdb.Membership.delete_status(org_perma_name, g.user.uuid, 'cancelled')
		return json_response(dict(description='Test.'), 200)
	if g.req['operation'] == 'resign' :
		appdb.Membership.delete_status(org_perma_name, g.user.uuid, 'resigned')
		return json_response(dict(description='Test.'), 200)
	return json_response(dict(description='Failed.'), 400)

@api.route("/organizations.json", methods=["GET"])
def organization_get_all():
	# TODO: Organization parent/child relations as JSON tree
	organizations = appdb.Organization.get_all()
	ret = []
	for organization in organizations:
		tuple = {
			'legal_name': organization.legal_name,
			'friendly_name': organization.friendly_name,
			'perma_name': organization.perma_name
		}
		ret.append(tuple)
	return json_response({'organizations':ret})

@api.route("/organization_<perma_name>.json", methods=["PUT"])
@requires_auth
@request_fields('legal_name', 'friendly_name')
def organization_put(perma_name):
	# FIXME: Proper permissions checking required
	if g.req.has_key('perma_name'):
		if g.req['perma_name'] != perma_name:
			return json_response(dict(description='Supplied (optional) perma_name does not match URL'), 422)
	organization = appdb.Organization.find_by_perma(perma_name);
	if not organization:
		# Does not exist, create new
		if not appdb.Organization.create(perma_name, g.req):
			return json_response(dict(description='Failed to create organization. Check input data.'), 422)
		return json_response(dict(description='Organization created'), 201)
	if organization.update(g.req): return json_response(dict(description='Organization information updated'))
	return json_response(dict(description='Failed to update organization. Check input data.'), 422)

@api.route("/organization_<perma_name>.json", methods=["GET"])
def organization_get(perma_name):
	# FIXME: Proper error checking here?
	org = appdb.Organization.find_by_perma(perma_name)
	if not org: abort(404)
	ret = {
		'legal_name': org.legal_name,
		'friendly_name': org.friendly_name,
		'perma_name': org.perma_name
	}
	parent_org = org.get_parent()
	if parent_org: ret['parent_name'] = parent_org.perma_name
	return json_response(ret, 200)


@api.route("/applications_list_<perma_name>.json", methods=["GET"])
@requires_auth
def organization_get_applications(perma_name): # FIXME: Error & ACL checking
	applications = appdb.Organization.get_applications(g.user.uuid, perma_name)
	ret = []
	for user in applications:
		tuple = {
			'legal_name': user.legal_name,
			'dob': user.dob,
			'residence': user.residence,
			'phone': user.phone,
			'email': user.email,
			'uuid': user.uuid
		}
		ret.append(tuple)
	return json_response(ret, 200)

@api.route("/applications_process_<perma_name>.json", methods=["POST"])
@requires_auth
@request_fields('uuid', 'orgapplicationprocess', 'orgapplicationtransfer')
def organization_process_applications(perma_name):
	if not appdb.User.manage_memberships(g.user.uuid, perma_name):
		return json_response(dict(description='Access denied while trying to process applications.'), 403)
	applications = 0;
	print "GGGGGGGGGGGG"
	print repr(g.req.get('uuid'))
	for uuid in g.req.get('uuid'):
		appdb.Membership.process_application(perma_name, uuid,  g.req.get('orgapplicationprocess'), g.req.get('orgapplicationtransfer'))
		applications += 1
		print "ZZZZZZZZZZZZ"
		print applications
	return json_response(dict(description='Processed ' + str(applications) + ' applications.'), 200)

@api.route("/settings.json", methods=["PUT"])
@requires_auth  # FIXME: Require admin user/password
@request_fields()
def settings_put():
	if not appdb.Settings.put(g.req):
		return json_response(dict(description='Unable to store settings. Check your request.'), 422)
	return json_response(dict(description="Settings updated"))

@api.route("/settings.json", methods=["GET"])
@requires_auth  # FIXME: Require admin user/password
def settings_get():
	return json_response(appdb.Settings.get_all())
	
@api.route("/I_accidentally_the_whole_database.json", methods=['DELETE'])
def clear_database():
	# FIXME: Security-wise this is obviously flawed
	appdb.clear_database();
	return json_response({})

