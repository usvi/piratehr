#!/usr/bin/python
# -*- coding: utf-8 -*-

#from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, send_file
import appdb
import datetime
import smtplib
from email.mime.text import MIMEText


def send_password_reset_emails(reset_list, reset_url_base): # reset_list contains list of User,Auth tuples
	settings = appdb.Settings.get_all()
	s = smtplib.SMTP(settings['smtp_server'])
	for recipient, token in reset_list:
		#print recipient.email + "  :" + token.token_content
		msg_text = "You have requested a password reset on PirateHR for " + recipient.legal_name + ".\n\n"
		msg_text += "You can login and reset your password by using this link:\n" + reset_url_base + token.token_content + "\n\n"
		msg_text += "If you think that this is an error, you can safely ignore this message";
		msg = MIMEText(msg_text, 'plain', 'utf8')
		msg['Subject'] = "Password reset from PirateHR"
		msg['From'] = settings['email_reset_from']
		msg['To'] = recipient.email
		s.sendmail(settings['email_reset_from'], [recipient.email], msg.as_string())
		print "Sent mail to " + recipient.email
	s.quit()

