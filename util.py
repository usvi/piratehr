#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import request, Response, g
from functools import wraps
from datetime import datetime, date
from time import sleep
import appdb
import json

def init_error_responses(app):
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
	timedelta = t - datetime.utcnow()
	duration = timedelta.seconds + timedelta.microseconds / 1E6 + timedelta.days * 86400
	if duration > 0: sleep(duration)
	else: g.logger.warn('sleep_until called ' + duration + ' s after the deadline')

def json_response(data, status = 200, **kwargs):
	"""All responses sent by the API should be formatted with this, e.g.
	return json_response(dict(somefield=123, otherfield='foo'))
	return json_response({'description':'No permission to access the requested user'}, 403)
	return json_response(dict(description='...'), 401, {'WWW-Authenticate': 'Basic realm="JSON auth required"'})
	"""
	# Conversion function is needed for datetime objects :/
	def jsonconvert(obj):
		if isinstance(obj, datetime) or isinstance(obj, date): return obj.isoformat()
		return str(obj)
	resp = Response(json.dumps(data, default=jsonconvert), status=status, mimetype='application/json')
	for k, v in kwargs.get('headers', {}).items(): resp.headers[k] = v
	return resp

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

