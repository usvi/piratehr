#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, g
from sqlalchemy import *
from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime, timedelta
from base64 import urlsafe_b64encode


Base = declarative_base()


class Settings(Base):
	__tablename__ = 'settings'
	key = Column(String(64), primary_key=True)
	value = Column(String(4032))
	def __init__(self, key, value):
		self.key = key
		self.value = value
	def __repr__(self):
		return '<%s=%s>' % (self.key, self.value)
	@staticmethod
	def put(settings_dict):
		for k in settings_dict:
			v = settings_dict[k]
			# FIXME: key/value sanity checks
			g.db.merge(Settings(k, v))
		g.db.commit()
		return True
	@staticmethod
	def get_all():
		result_dict = {}
		for row in g.db.query(Settings).all():
			result_dict[row.key] = row.value # Don't really know why direct .all() return fails...
		return result_dict


class User(Base):
	__tablename__ = 'user'
	id = Column(Integer, nullable=False, primary_key=True) # Internal database ID
	uuid = Column(String(128), nullable=False, unique=True) # UUID4
	login = Column(String(128), unique=True) # Login name, can be used in URLs
	name = Column(String(128), nullable=False) # Name/nick the user wants to be called and displayed as
	legal_name = Column(String(256), nullable=False) # Legal name as in governmental records
	residence = Column(String(128)) # Users's place of residence. City/town/municipality + country
	location = Column(String(128)) # User's gps coordinates
	address_id = Column(Integer, ForeignKey('address.id', onupdate="RESTRICT", ondelete="RESTRICT"), unique=True) # Current address of user from Address table
	phone = Column(String(128)) # User's phone number, preferably in international format
	email = Column(String(256)) # User's active email address
	dob = Column(Date, nullable=False) # User's official date of birth
	ssn = Column(String(128), unique=True) # Official social security number of the user
	joined = Column(DateTime, nullable=False) # Time when user initially joined
	last_seen = Column(DateTime, nullable=False) # Time when user was last seen active on system
	@staticmethod
	def create(legal_name, residence, phone, email, dob):
		# Try to guess name out of legal_name
		tmp = legal_name.split()
		if len(tmp) > 2: name = tmp[0] + ' ' + tmp[-1]
		else: name = legal_name
		# Create new user
		user = User()
		user.uuid = str(uuid.uuid4())
		user.residence = residence
		user.legal_name = legal_name
		user.name = name
		user.joined = datetime.utcnow()
		user.last_seen = user.joined
		user.dob = dob
		if(len(email) < 4 and len(phone) < 4): return None # Elementary check for contact info
		user.email = email
		user.phone = phone
		g.db.add(user)
		if g.db.commit() == None: return user
		return False
	def update(self, data):
		if data.has_key('uuid') and data['uuid'] != self.uuid: return False
		if data.has_key('login'): self.login = data['login']
		if data.has_key('residence'): self.residence = data['residence']
		if data.has_key('legal_name'): self.legal_name = data['legal_name']
		if data.has_key('name'): self.name = data['name']
		if data.has_key('location'): self.location = data['location']
		if data.has_key('phone'): self.phone = data['phone']
		if data.has_key('email'): self.email = data['email']
		if data.has_key('dob'): self.dob = data['dob']
		if data.has_key('ssn'): self.ssn = data['ssn']
		if not self.validate():
			g.db.rollback()
			return False
		g.db.commit()
		return True
	def validate(self):
		return True  # FIXME
	@staticmethod
	def find(uuid):
		return g.db.query(User).filter_by(uuid=uuid).first()
	@staticmethod
	def find_by_email(email):
		return g.db.query(User).filter_by(email=email).all()
	@staticmethod
	def manage_organization(uuid, perma_name, operation_description): # FIXME: Log with operation_description!
		# Check whether we gan manage the data for the organization. Needs board level access.
		user = User.find(uuid)
		if not user:
			return False
		organization = Organization.find_by_perma(perma_name)
		while organization:
			# Check for possible membership. If got, check that it is of status 'member' and of something else than non-priv position.
			# FIXME: Organizations are completely  independent; there is no hiearchy. The code should be changed to reflect.
			membership = Membership.get(organization.perma_name, uuid)
			if membership and membership.status == 'member' and (membership.position == 'chair' or membership.position == 'vice_chair'\
										or membership.position == 'secretary' or membership.position == 'board'):
				return True
			organization = organization.get_parent()
		return False # Ok, the topmost organization didn't have privileged membership for user. Access denied.

class Address(Base):
	__tablename__ = 'address'
	id = Column(Integer, primary_key=True) # Id of this address
	user_id = Column(Integer, ForeignKey('user.id', onupdate="RESTRICT", ondelete="RESTRICT", use_alter=True, name="user_id_altc"), nullable=False) # Reference to the id of the user having this address
	line1 = Column(String(128), nullable=False) # First address line; name of the recipient
	line2 = Column(String(128)) # Second address line; company, etc
	street = Column(String(128)) # Street address
	zipcode = Column(String(64), nullable=False) # ZIP number in international format
	city = Column(String(64), nullable=False) # City/town/municipality of the recipient
	state = Column(String(64)) #  State, if applicable
	country = Column(String(64), nullable=False) # Country
	def data_in_dict(self):
		return dict(
			line1 = self.line1,
			line2 = self.line2,
			street = self.street,
			zipcode = self.zipcode,
			city = self.city,
			state = self.state,
			country = self.country
		)
	
	@staticmethod
	def get_by_user(user):
		ret = []
		addr = g.db.query(Address).filter_by(user_id = user.id)
		for a in addr:
			ret.insert(a.data_in_dict(), 0 if user.address_id == a.id else -1)
		return ret

class Auth(Base):
	__tablename__ = 'auth'
	id = Column(Integer, primary_key=True) # Id of this token
	user_id = Column(Integer, ForeignKey('user.id'), nullable=False, primary_key=True) # Reference to the id of the user having this token
	token_type = Column(Enum('session', 'pw_hash', 'pw_reset', 'facebook', 'openid', name='token_types'), nullable=False, primary_key=True) # Auth type
	token_content = Column(String(512)) # Auth token content
	expiration_time = Column(DateTime) # Expiration of the token
	__table_args__ = (UniqueConstraint('user_id', 'token_type'),)

	def store(self):
		# Remove duplicates
		g.db.query(Auth).filter_by(user_id=self.user_id).filter_by(token_type=self.token_type).delete()
		g.db.merge(self)
		g.db.commit()

	@staticmethod
	def find_by_email(email, token_type): #return g.db.query(Auth).filter_by(user_id=user_id, token_type=token_type).first()
		return g.db.query(User, Auth).filter(User.id==Auth.user_id).filter(User.email==email).filter(Auth.token_type==token_type).all()
	
	@staticmethod
	def reset_token_email(email): # 1. Figure out missing token users 2. Modify rest of the tokens 3. Make missing tokens
		# I guess session.merge() is unusable because unique constraints are not automatically enforced by sqlalchemy
		missing_token_users = g.db.query(User).filter(User.email==email).all() # All users; we pick out users who have already a token
		existing_token_tuples = Auth.find_by_email(email, 'pw_reset')
		for temp_tuple in existing_token_tuples:
			if temp_tuple.User in missing_token_users:
				missing_token_users.remove(temp_tuple.User) # Modify token
				temp_tuple.Auth.token_content = urlsafe_b64encode(bytes(uuid.uuid4()))
				temp_tuple.Auth.expiration_time = datetime.utcnow() + timedelta(days=30)
		for new_token_user in missing_token_users:
			new_token = Auth() # This user needs new token
			new_token.user_id = new_token_user.id
			new_token.token_type = 'pw_reset'
			new_token.token_content = urlsafe_b64encode(bytes(uuid.uuid4()))
			new_token.expiration_time = datetime.utcnow() + timedelta(days=30)
			g.db.add(new_token)
			existing_token_tuples.append((new_token_user,new_token))
		g.db.commit()
		return existing_token_tuples
	
	@staticmethod
	def find_token_by_user(user, token_type):
		auth = g.db.query(Auth).filter_by(user_id=user.id).filter_by(token_type=token_type).first()
		if not auth: return None
		return auth.token_content
	
	@staticmethod
	def use_token(token_type, token_content):
		auth = g.db.query(Auth).filter_by(token_type=token_type).filter_by(token_content=token_content).first()
		if not auth: return None
		user = g.db.query(User).filter_by(id=auth.user_id).first()
		g.db.delete(auth)
		g.db.commit()
		return user
		
	@staticmethod
	def create_session(user):
		auth = Auth()
		auth.user_id = user.id
		auth.token_type = 'session'
		auth.token_content = urlsafe_b64encode(bytes(uuid.uuid4()))
		auth.expiration_time = datetime.utcnow() + timedelta(days=1)
		auth.store()
		return auth.token_content
	
	@staticmethod
	def authenticate(auth_req):
		if auth_req.has_key('uuid') and auth_req.has_key('token'):  # Session token
			u = g.db.query(User).join(Auth) \
			  .filter(User.uuid == auth_req['uuid']) \
			  .filter(Auth.token_type == 'session') \
			  .filter(Auth.token_content == auth_req['token']) \
			  .first()
			if not u: return None
			u.last_seen = datetime.utcnow()
			g.db.commit()
			return u
		# Other (per request) authentication methods may be added here
		else: return None


class Organization(Base):
	__tablename__ = 'organization'
	id = Column(Integer, primary_key=True) # Id of this organization
	parent_id = Column(Integer, ForeignKey('organization.id', onupdate="RESTRICT", ondelete="RESTRICT")) # Reference to the 
	group_id = Column(Integer, unique=False) # Group id. User can be a member of only one group_id
	legal_name = Column(String(128), nullable=False, unique=True) # Full legal name of the organization
	friendly_name = Column(String(128), nullable=False, unique=True) # Friendly short name of the organization
	perma_name = Column(String(128), nullable=False, unique=True) # Permanent name identifier of the organization. Admin-mutable (in the future).
	@staticmethod
	def create(perma_name, data):
		org = Organization()
		org.perma_name = perma_name
		g.db.add(org)
		return org.update(data)
	def update(self, data):
		if data.has_key('perma_name') and data['perma_name'] != self.perma_name: return False
		if data.has_key('friendly_name'): self.friendly_name = data['friendly_name']
		if data.has_key('legal_name'): self.legal_name = data['legal_name']
		if data.has_key('group') and data['group'] == -1:
			# We might need new id. But lets not change it if its the only one
			if len(g.db.query(Organization).filter(Organization.group_id==self.group_id).all()) > 1:
				# Ok, we actually need the new id.
				max_group_org = g.db.query(Organization).order_by(Organization.group_id.desc()).first()
				if not max_group_org:
					self.group_id = 1
				else:
					self.group_id = max_group_org.group_id + 1
		elif data.has_key('group'):
			self.group_id = data['group']
		if data.get('parent_name'):
			p = Organization.find_by_perma(data['parent_name'])
			if not p: return False
			self.parent_id = p.id
		if not self.validate():
			g.db.rollback()
			return False
		
		g.db.commit()
		return True
	def validate(self):
		# FIXME: Thorough validation.
		# FIXME: ACL when setting parent
		# FIXME: Check NULL parents
		# FIXME: After groups we might have memberships in sibling organizations.
		# Case 1: ALL new siblings must have the same parent as this
		new_siblings = self.get_siblings()
		for sibling in new_siblings:
			if sibling.parent_id != self.parent_id:
				return False
		return True
	@staticmethod
	def generate_perma_name(friendly_name): # FIXME: We should enforce this here, not rely on javascript
		import unicodedata
		import re
		if type(friendly_name) == int:
			friendly_name = str(friendly_name)
		perma_name = friendly_name.lower()
		perma_name = perma_name.replace(" ", "_")
		perma_name = unicodedata.normalize('NFKD', unicode(perma_name)).encode('ascii','ignore')
		perma_name = "".join(re.findall('[a-z0-9_-]+', perma_name)) # FIXME: is the last '-' in pattern ok?
		return perma_name
	@staticmethod
	def get_all():
		return g.db.query(Organization).all()
	@staticmethod
	def find_by_perma(perma_name):
		return g.db.query(Organization).filter_by(perma_name=perma_name).first()
	def get_parent(self):
		return g.db.query(Organization).filter_by(id=self.parent_id).first()
	def get_children(self):
		return g.db.query(Organization).filter_by(parent_id=self.id).all()
	def get_siblings(self):
		return g.db.query(Organization).filter_by(group_id=self.group_id).all()
	@staticmethod
	def get_applications(uuid, perma_name):
		# Data needed: Full name, DOB, Residence, Phone, email, uuid, application id
		return g.db.query(User).filter(Membership.status=='applied').filter(Membership.user_id==User.id).\
			filter(Membership.organization_id==Organization.id).filter(Organization.perma_name==perma_name).order_by(Membership.id).all()
	

class Membership(Base):
	__tablename__ = 'membership'
	id = Column(Integer, primary_key=True) # Id of this membership
	user_id = Column(Integer, ForeignKey('user.id', onupdate="RESTRICT", ondelete="RESTRICT"), nullable=False) # User id this membership applies to
	organization_id = Column(Integer, ForeignKey('organization.id', onupdate="RESTRICT", ondelete="RESTRICT"), nullable=False) # Organization this membership applies to
	status = Column(Enum('applied', 'member', 'honorary_member', 'expelled', 'resigned', 'cancelled', 'email' , 'unsubscribed', name='status_types'), nullable=True) # Status type
	position = Column(Enum('nonpriv', 'chair', 'vice_chair', 'secretary', 'board' , name='position_types'), nullable=True) # Position type
	activist = Column(Boolean) # Sign of active membership. We send more email if this is ticked.
	title = Column(String(128)) # Description of a special position in the organization
	application = Column(Text, nullable=False) # As information for the board of the organization (includes UUID + name also)
	applied_time = Column(DateTime, nullable=False) # Time of membership application
	accepted_time = Column(DateTime) # Time of membership acceptance
	terminated_time = Column(DateTime) # Time of membership termination
	resignation_reason = Column(Text) # Reason for resignation
	@staticmethod
	def find_by_uuid(uuid): # Finds all memberships of the user
		# SELECT * FROM membership JOIN (SELECT organization_id, MAX(id) AS max_id FROM membership GROUP BY organization_id) AS foo WHERE membership.id = foo.max_id;
		# 19:14 < agronholm> so make that subselect into a subquery(), join it to the main query and filter
		#
		user = User.find(uuid)
		if not user: return None
		subquery = g.db.query(func.max(Membership.id).label('id')).filter(Membership.user_id == user.id).group_by(Membership.organization_id).subquery()
		return g.db.query(Membership, Organization).filter(Membership.organization_id==Organization.id).join(subquery, subquery.c.id == Membership.id).order_by(Organization.id).all()
	@staticmethod
	def get(perma_name, uuid):
		return g.db.query(Membership).filter(User.id==Membership.user_id).filter(User.uuid==uuid).filter(Organization.id==Membership.organization_id).\
			filter(Organization.perma_name==perma_name).order_by(Membership.id.desc()).first()
	@staticmethod
	def add(perma_name, uuid): # If we have old membership, update it ONLY if it is in state (applied)
		# FIXME: Use transactions here and also elsewhere where deemed necessary(???).
		user = User.find(uuid)
		organization = Organization.find_by_perma(perma_name)
		if not user or not organization: return None
		# Got organization and user. Try to get membership. If does not exist, create.
		membership = g.db.query(Membership).filter(Membership.user_id==user.id).filter(Membership.organization_id==organization.id).\
			order_by(Membership.id.desc()).first() # Just in case return latest only.
		if not membership or membership.status != 'applied':
			membership = Membership()
			membership.user_id = user.id
			membership.organization_id = organization.id
			g.db.add(membership)
		# Check that there are no old applications.
		existing_memberships = g.db.query(Membership).filter(Membership.user_id==user.id).filter(Organization.group_id==organization.group_id).\
			filter(Membership.organization_id==Organization.id).filter(Membership.status=='applied').all()
		if len(existing_memberships) > 0:
			g.db.rollback()
			return None
		# Membership exists now as object at least.
		membership.status = 'applied'
		membership.application = user.uuid + ":" + user.legal_name
		membership.applied_time = datetime.utcnow()
		g.db.commit()
	@staticmethod
	def delete_status(perma_name, uuid, status): # If we have old membership, update it
		membership = Membership.get(perma_name, uuid)
		if not membership: return None
		membership.status = status
		membership.terminated_time = datetime.utcnow()
		g.db.commit()
	@staticmethod
	def process_application(perma_name, uuid, status, transfer_perma): # status is once of accept, reject, transfer
		membership = Membership.get(perma_name, uuid)
		if not membership:
			return None
		if status == 'accept':
			membership.status = 'member'
			membership.position = 'nonpriv'
			membership.accepted_time = datetime.utcnow()
		elif status == 'reject':
			Membership.delete_status(perma_name, uuid, 'expelled')
		elif status == 'transfer':
			transfer_org = Organization.find_by_perma(transfer_perma)
			membership.organization_id = transfer_org.id
		else:
			return None
		g.db.commit()
	
class MetaDef(Base):
	__tablename__ = 'metadef'
	id = Column(Integer, primary_key=True) # Id of this metadata definition
	organization_id = Column(Integer, ForeignKey('organization.id', onupdate="RESTRICT", ondelete="RESTRICT"), nullable=False) # Organization owning this metadata
	label = Column(String(128), nullable=False, unique=True) # Label of the metadata
	type = Column(Enum('string', 'checkbox', 'date', name='meta_types'), nullable=False) # Metadata type
	readonly = Column(Boolean, nullable=False) # Is the metadata editable by the user


class MetaData(Base):
	__tablename__ = 'metadata'
	id = Column(Integer, primary_key=True) # Id of this metadata entry
	metadef_id = Column(Integer, ForeignKey('metadef.id', onupdate="RESTRICT", ondelete="RESTRICT"), primary_key=True) # Metadata definition this data applies to
	user_id = Column(Integer, ForeignKey('user.id', onupdate="RESTRICT", ondelete="RESTRICT"), primary_key=True) # User this data applies to
	value = Column(Text) # The actual metadata


class Log(Base):
	__tablename__ = 'log'
	id = Column(Integer, primary_key=True) # Id of this log entry
	time = Column(DateTime, nullable=False) # Time of this log entry
	ip = Column(String(64), nullable=False) # IP address of the request generating this log entry
	logged_user_id = Column(Integer, ForeignKey('user.id', onupdate="RESTRICT", ondelete="RESTRICT"), nullable=False) # User id of the user performing the action
	target_user_id = Column(Integer, ForeignKey('user.id', onupdate="RESTRICT", ondelete="RESTRICT")) # User id this log entry applies to
	target_organization_id = Column(Integer, ForeignKey('organization.id', onupdate="RESTRICT", ondelete="RESTRICT")) # Organization this log entry applies to
	target_membership_id = Column(Integer, ForeignKey('membership.id', onupdate="RESTRICT", ondelete="RESTRICT")) # Membership this log entry applies to
	type = Column(Enum('view', 'change', 'delete', 'other', name='log_types'), nullable=False) # Log entry type
	description = Column(Text) # Free format log entry description

# Without this, MySQL will silently insert invalid values in the
# database, causing very long debugging sessions in the long run
def fix_mysql_connect(dbapi_con, connection_record):
	cur = dbapi_con.cursor()
	cur.execute("SET SESSION sql_mode='TRADITIONAL'")
	cur = None

def init(app):
	global engine;
	engine = create_engine(app.config['DATABASE'], echo=app.config['DATABASE_DEBUG'], pool_recycle=60)
	if app.config['DATABASE'][0:5] == 'mysql': event.listen(engine, 'connect', fix_mysql_connect)
	Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
	Base.metadata.create_all(bind=engine)  # Create tables etc.
	@app.before_request
	def before_request():
		"""Make sure we are connected to the database each request."""
		g.db = Session()
	@app.teardown_request
	def teardown_request(exception):
		"""Closes the database again at the end of the request."""
		g.db.close()
		g.db = None


def clear_database():
	"""Remove all tables and data."""
	Base.metadata.drop_all(bind=engine)  # Create tables etc.
	Base.metadata.create_all(bind=engine)  # Create tables etc.

