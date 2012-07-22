#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, render_template, flash
import json
import appdb

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

# Subclass a RestResource and configure it
api = Blueprint("api", __name__, url_prefix="/api")

@api.route("/new-user.json", methods=["POST"])
def create_user():
	user = appdb.User.create(
		legal_name='John Doe',
		residence='City, County',
		phone='123456',
		email='',
		dob='1985-12-31')
	if not user: return "Invalid user data", 422
	ret = {
		'uuid': user.uuid,
		'url': url_for('static', filename = "user/" + user.uuid, _external = True)
		}
	return json.dumps(ret), 201, {'Location': ret['url'] }

@api.route("/user_<user_id>.json", methods=["GET"])
def get_user(user_id):
	user = appdb.User.find(user_id)
	if user == None: abort(404)
	ret = {
		'login': user.login,
		'uuid': user.uuid
		}
	return json.dumps(ret), 200

@api.route("/user_<user_id>.json", methods=["PUT"])
def update_user(user_id):
	# do your stuff here
	return "PUT" + user_id, 200

@api.route("/I_accidentally_the_whole_database", methods=["DELETE"])
def clear_database():
	appdb.clear_database()
	return "DELETED", 200

# you can use the "need_auth" decorator to do things for you
#@need_auth(authentifier_callable, "project") # injects the "project" argument if authorised
def delete(self, user_id):
	# do your stuff
	return "DELETED", 200

if __name__ == '__main__':
	app.register_blueprint(api)
	app.run()


