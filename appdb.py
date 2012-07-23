#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, g
from sqlalchemy import *
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Setting(Base):
	__tablename__ = 'settings'
	key = Column(String(64), primary_key=True)
	value = Column(String(4032))
	def __init__(self, key, value):
		self.key = key
		self.value = value
	def __repr__(self):
		return '<%s=%s>' % (self.key, self.value)


class User(Base):
	__tablename__ = 'user'
	id = Column(Integer, nullable=False, primary_key=True) # Internal database ID
	uuid = Column(String(128), nullable=False, unique=True) # Valid chars: ABCDEFGHJKLMNPQRSTUWXYZ23456789
	login = Column(String(128), unique=True) # Login name, can be used in URLs
	name = Column(String(128), unique=True) # Name/nick the user wants to be called and displayed as
	legal_name = Column(String(256), nullable=False) # Legal name as in governmental records
	residence = Column(String(128)) # Users's place of residence. City/town/municipality + country
	address_id = Column(Integer, ForeignKey('address.id', onupdate="RESTRICT", ondelete="RESTRICT"), unique=True) # Current address of user from Address table
	phone = Column(String(128)) # User's phone number, preferably in international format
	email = Column(String(256)) # User's active email address
	dob = Column(Date, nullable=False) # User's official date of birth
	ssn = Column(String(128), unique=True) # Official social security number of the user
	location = Column(String(128)) # User's gps coordinates
	joined = Column(DateTime, nullable=False) # Time when user initially joined
	last_seen = Column(DateTime, nullable=False) # Time when user was last seen active on system
	@staticmethod
	def create(legal_name, residence, phone, email, dob):
		import uuid
		from datetime import datetime
		user = User()
		user.uuid = uuid.uuid4()
		user.residence = residence
		user.legal_name = legal_name
		user.joined = datetime.utcnow()
		user.last_seen = user.joined
		user.dob = dob
		if(len(email) < 4 and len(phone) < 4): return None # Elementary check for contact info
		user.email = email
		user.phone = phone
		g.db.add(user)
		g.db.commit()
		return user
	@staticmethod
	def find(user_id):
		return g.db.query(User).filter_by(uuid=user_id).first()


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

		   
class Auth(Base):
	__tablename__ = 'auth'
	id = Column(Integer, primary_key=True) # Id of this token
	user_id = Column(Integer, ForeignKey('user.id'), nullable=False) # Reference to the id of the user having this token
	token_type = Column(Enum('pw_hash', 'pw_reset', 'facebook', 'openid', name='token_types'), nullable=False, primary_key=True) # Auth type
	token_content = Column(String(512)) # Auth token content
	expiration_time = Column(DateTime) # Expiration of the token
	@staticmethod
	def find_by_email(email, token_type): #return g.db.query(Auth).filter_by(user_id=user_id, token_type=token_type).first()
		users = g.db.query(User).filter_by(email=email)
		print "users:" + repr(users)
		for instance in users:
			print instance.uuid


class Organization(Base):
	__tablename__ = 'organization'
	id = Column(Integer, primary_key=True) # Id of this organization
	parent_id = Column(Integer, ForeignKey('organization.id', onupdate="RESTRICT", ondelete="RESTRICT")) # Reference to the 
	legal_name = Column(String(128), nullable=False, unique=True) # Full legal name of the organization
	friendly_name = Column(String(128)) # Friendly short name of the organization


class Membership(Base):
	__tablename__ = 'membership'
	id = Column(Integer, primary_key=True) # Id of this membership
	user_id = Column(Integer, ForeignKey('user.id', onupdate="RESTRICT", ondelete="RESTRICT"), nullable=False) # User id this membership applies to
	organization_id = Column(Integer, ForeignKey('organization.id', onupdate="RESTRICT", ondelete="RESTRICT"), unique=True) # Organization this membership applies to
	status = Column(Enum('applied', 'member', 'honorary_member', 'expelled', 'resigned' , name='status_types'), nullable=True) # Status type
	position = Column(Enum('nonpriv', 'chair', 'vice_chair', 'secretary', 'board' , name='position_types'), nullable=True) # Position type
	title = Column(String(128)) # Description of a special position in the organization
	application = Column(Text, nullable=False) # As information for the board of the organization (includes UUID + name also)
	applied_time = Column(DateTime, nullable=False) # Time of membership application
	accepted_time = Column(DateTime) # Time of membership acceptance
	terminated_time = Column(DateTime) # Time of membership termination
	resignation_reason = Column(Text) # Reason for resignation

	
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

	
def init(app):
	global engine;
	engine = create_engine(app.config['DATABASE'], echo=app.config['DATABASE_DEBUG'])
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

