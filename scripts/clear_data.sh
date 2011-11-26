#!/bin/sh

./manage.py sqlclear chatter checkin events identity news offers places tagging | ./manage.py dbshell
./manage.py syncdb