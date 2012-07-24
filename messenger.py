#!/usr/bin/python
# -*- coding: utf-8 -*-

#from flask import Flask, Blueprint, request, session, g, redirect, url_for, abort, send_file
import appdb
import datetime
import smtplib
from email.mime.text import MIMEText


def send_password_reset_emails(reset_list): # reset_list contains list of User,Auth tuples
	s = smtplib.SMTP('mail.inet.fi')
	for recipient, token in reset_list:
		#print recipient.email + "  :" + token.token_content
		#msg = MIMEText("Somebody has requested a password reset username " + recipient.name + ". You have the following token: " + token.token_content)
		msg = MIMEText("Somebody has requested a password reset username " + recipient.legal_name + ". You have the following token: " + token.token_content)
		msg['Subject'] = "Password reset from PirateHR"
		msg['From'] = "example@example.com"
		msg['To'] = recipient.email
		s.sendmail("piratehr@piraattipuolue.fi", [recipient.email], msg.as_string())
		print "Sent mail to " + recipient.email
	s.quit()

