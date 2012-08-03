#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import *
from flask import g
from time import sleep
import appdb
import bcrypt

# For security reasons we delay auth responses 500 ms from initiation
def delay_timer():
	return datetime.utcnow() + timedelta(milliseconds = 500)

def sleep_until(t):
	"""Sleep until datetime t (utc)"""
	timedelta = t - datetime.utcnow()
	duration = timedelta.seconds + timedelta.microseconds / 1E6 + timedelta.days * 86400
	if duration > 0: sleep(duration)
	else: g.logger.warn('sleep_until called ' + str(-duration) + ' s after the deadline')


def login_password(login, password):
	timer = delay_timer()
	users = appdb.User.find_by_email(login)
	auth_obj = None
	if not users:
		pass
	else:
		users_passed = []
		for user in users:
			pw_hash = appdb.Auth.find_token_by_user(user, 'pw_hash')
			if not pw_hash or pw_hash != bcrypt.hashpw(password, pw_hash): continue
			users_passed.append(user)
			auth_obj = {
				'token': appdb.Auth.create_session(user),
				'uuid': user.uuid,
				'name': user.name
			}
		if len(users_passed) > 1:
			# Multiple matching users, reset all their passwords and deny login
			# TODO: reset_password(users_passed)
			auth_obj = None
	sleep_until(timer)
	return auth_obj

def login_token(token):
	timer = delay_timer()
	user = appdb.Auth.use_token('pw_reset', token)
	sleep_until(timer)
	return user

def set_password(user, password):
	auth = appdb.Auth()
	auth.user_id = user.id
	auth.token_type = 'pw_hash'
	auth.token_content = bcrypt.hashpw(password, bcrypt.gensalt(10))
	auth.expiration_time = datetime.utcnow() + timedelta(days=365)
	auth.store()

