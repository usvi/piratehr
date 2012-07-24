#!/usr/bin/python
# -*- coding: utf-8 -*-

#from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, send_file
import appdb
import datetime
import smtplib
from email.mime.text import MIMEText


def send_password_reset_emails(reset_list): # reset_list contains list of User,Auth tuples
	for recipient, token in reset_list:
		print recipient.email + "  :" + token.token_content


