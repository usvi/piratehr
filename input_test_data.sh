#!/bin/bash

curl -X PUT http://localhost:5000/api/settings.json --data "key=smtp_server&value=mail.inet.fi"
curl -X PUT http://localhost:5000/api/settings.json --data "key=email_reset_from&value=example@example.com"
