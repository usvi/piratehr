#!/bin/bash

set -e

echo Drop and re-create the database
mysql piratehr -upiratehr -ppiratehr <<EOF
drop database piratehr;
create database piratehr;
EOF

echo Restart the application
touch piratehr.py

sleep 5

echo Settings 1
curl -X PUT http://localhost:5000/api/settings.json --data "key=smtp_server&value=mail.inet.fi"
echo

echo Settings 2
curl -X PUT http://localhost:5000/api/settings.json --data "key=email_reset_from&value=no-reply@nowhere.tld"
echo

echo Test User: Donald Duck
curl -X POST http://localhost:5000/api/new_user.json --data "legal_name=Donald%20Duck&residence=Duckburg%2C%20Florida&phone=&email=donald@duck&dob=1950-01-01"
echo

echo Test User 1
curl -X POST http://localhost:5000/api/new_user.json --data "legal_name=Test%20User%201&residence=%C3%84k%C3%A4slompolo%2C%20Finland&phone=%2B358123456&email=user@nowhere.tld&dob=1980-12-31"
echo

echo Test User 2
curl -X POST http://localhost:5000/api/new_user.json --data "legal_name=Test%20User%202&residence=%C3%84k%C3%A4slompolo%2C%20Finland&phone=%2B358123456&email=user@nowhere.tld&dob=1980-12-31"
echo

echo Done.


