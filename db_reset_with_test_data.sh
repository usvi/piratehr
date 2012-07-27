#!/bin/bash

set -e

echo Drop and re-create the database
mysql piratehr -upiratehr -ppiratehr <<EOF
drop database piratehr;
create database piratehr;
EOF
sleep 1

echo Restart the application
touch piratehr.py

sleep 6

echo Admin User
curl -f -X POST -H "Content-Type: application/json" http://localhost:5000/api/new_user.json --data '{"legal_name":"Bastard Operator From Hell","residence":"Internet","phone":"","email":"root@localhost","dob":"1970-01-01"}'
echo

echo Authenticate him...
curl -f -X POST -H "Content-Type: application/json" http://localhost:5000/api/auth.json --data '{"type":"login_password","login":"root@localhost","password":"password"}' > auth.json
cat auth.json
echo

echo -n json: > auth.json.tmp1
cat auth.json >> auth.json.tmp1
base64 -w0 < auth.json.tmp1 > auth.json.tmp2
AUTH="Authorization: basic $(cat auth.json.tmp2)"
echo $AUTH
rm -f auth.json.tmp1 auth.json.tmp2
echo

echo Settings 1
curl -f -X PUT -H "$AUTH" -H "Content-Type: application/json" http://localhost:5000/api/settings.json --data '{"key":"smtp_server","value":"mail.inet.fi"}'
echo

echo Settings 2
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/settings.json --data "key=email_reset_from&value=no-reply@nowhere.tld"
echo

echo Test User: Donald Duck
curl -f -X POST -H "$AUTH" http://localhost:5000/api/new_user.json --data "legal_name=Donald%20Duck&residence=Duckburg%2C%20Florida&phone=&email=donald@duck&dob=1950-01-01"
echo

echo Test User 1
curl -f -X POST -H "$AUTH" http://localhost:5000/api/new_user.json --data "legal_name=Test%20User%201&residence=%C3%84k%C3%A4slompolo%2C%20Finland&phone=%2B358123456&email=user@nowhere.tld&dob=1980-12-31"
echo

echo Test User 2
curl -f -X POST -H "$AUTH" http://localhost:5000/api/new_user.json --data "legal_name=Test%20User%202&residence=%C3%84k%C3%A4slompolo%2C%20Finland&phone=%2B358123456&email=user@nowhere.tld&dob=1980-12-31"
echo

echo Test User: Dolan Duck
curl -f -X POST -H "$AUTH" http://localhost:5000/api/new_user.json --data "legal_name=Uncle%20Dolan&residence=Ylilauta%2C%20Internet&phone=&email=uncle@dolan&dob=2008-02-01"
echo

echo Test User: Gooby
curl -f -X POST -H "$AUTH" http://localhost:5000/api/new_user.json --data "legal_name=Gooby&residence=Ylilauta%2C%20Internet&phone=&email=gooby@pls&dob=2008-04-01"
echo

echo Test Org: Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Caribian%20Pirates&friendly_name=Caribian%20Pirates"
echo

echo Test Org: Hawaiin Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Hawaiian%20Pirates&friendly_name=Hawaiian%20Pirates"
echo

echo Test Org: Barbados Pirates under Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Barbados%20Pirates&friendly_name=Barbados%20Pirates&parent_id=1"
echo

echo Test Org: St Kitts and Nevis Pirates under Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20St%20Kitts%20and%20Nevis%20Pirates&friendly_name=St%20Kitts%20and%20Nevis%20Pirates&parent_id=1"
echo

echo Test Org: Montserrat Pirates under Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Montserrat%20Pirates&friendly_name=Montserrat%20Pirates&parent_id=1"
echo

echo Test Org: Grenada Pirates under Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Grenada%20Pirates&friendly_name=Grenada%20Pirates&parent_id=1"
echo

echo Test Org: Caracas Pirates under Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Caracas%20Pirates&friendly_name=Caracas%20Pirates&parent_id=1"
echo

echo Test Org: Puerto Cabello Pirates under Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Puerto%20Cabello%20Pirates&friendly_name=Puerto%20Cabello%20Pirates&parent_id=1"
echo

echo Test Org: Curacao Pirates under Caribian Pirates
curl -f -X PUT -H "$AUTH" http://localhost:5000/api/organization.json --data "legal_name=Organization%20Of%20Curacao%20Pirates&friendly_name=Curacao%20Pirates&parent_id=1"
echo

echo Done.


