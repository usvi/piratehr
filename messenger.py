#!/usr/bin/python
# -*- coding: utf-8 -*-

#from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, send_file
import appdb
import datetime
import smtplib
from email.mime.text import MIMEText


def send_password_reset_emails(reset_list): # reset_list contains list of User,Auth tuples
	settings = appdb.Settings.get_all()
	s = smtplib.SMTP(settings['smtp_server'])
	for recipient, token in reset_list:
		#print recipient.email + "  :" + token.token_content
		msg = MIMEText("Somebody has requested a password reset username " + recipient.legal_name + ". You have the following token: " + token.token_content)
		msg['Subject'] = "Password reset from PirateHR"
		msg['From'] = settings['email_reset_from']
		msg['To'] = recipient.email
		s.sendmail(settings['email_reset_from'], [recipient.email], msg.as_string())
		print "Sent mail to " + recipient.email
	s.quit()

