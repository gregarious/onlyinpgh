import os
from icalendar import Calendar, Event

from onlyinpgh.outsourcing.places import smart_text_resolve
from onlyinpgh.places.models import Location

import logging
logging.disable('CRITICAL')

def run():
	fns = ['/home/greg/Desktop/bikepgh.ics',
			]
	
	for fn in fns:
		cache = {}
		cal = Calendar.from_string(open(fn,'rb').read())
		for e in cal.walk('vevent'):
			l = e.get('location')
			if l:
				l = l.lower().strip().encode('utf8')
				# TODO: look into whether ics file stores encoding?
				if l in cache:
					continue
				# TODO: maybe not use fixed seed? just make some kind of geocoding bounding box filter in the ical importer
				# maybe flag if geocoding is outside filter?
				result = smart_text_resolve(l,seed_location=Location(state='PA'))
				cache[l] = result


				print result.text
				print '\t', result.place or result.location
				print '\t', result.parse_status
