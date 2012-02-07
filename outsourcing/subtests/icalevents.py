from django.test import TestCase

from onlyinpgh.outsourcing.icalevents import FeedImporter, EventImportReport

from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Place
from onlyinpgh.events.models import Event, Role
from onlyinpgh.outsourcing.models import ICalendarFeed, VEventRecord

from datetime import datetime
from pytz import timezone

import random, logging, os
logging.disable(logging.CRITICAL)

def _to_feed_path(fn):
	return os.path.join(os.path.dirname(__file__),'test_ical',fn)

# values from the first event in test.ics used for validation and manual VEvent storage
test_event = {'name': 				'The Bicycle Thief',
			  'description_stub': 	'One of the most influential, memorable',
			  'dtstart':			datetime(2011,11,20,23,0),
			  'dtend': 				datetime(2011,11,21,1,0),
			  'uid': 				'tl0mpin4693ilfgprlggl6ls0g@google.com',
			  'dtmodified':			datetime(2011,11,17,17,59,52),
			  }

class ICalEventTest(TestCase):
	def setUp(self):
		self.init_ev_count = Event.objects.count()
		self.init_vev_count = VEventRecord.objects.count()

	def assertNoticeIn(self,report,notice_class,count=None):
		'''
		Asserts the given notice class is present in report.notices.

		If a count is given, the number of notices of this type must match
		exactly.
		'''
		relevant_notices = [n for n in report.notices
							if isinstance(n,notice_class)]
		
		# either assert at least one, or an exact count if provided
		if count is None:
			self.assertGreaterEqual(len(relevant_notices),1)
		else:
			self.assertEquals(len(relevant_notices,count))

	def test_new_feed(self):
		test_org = Organization.objects.create(name="TestOrg")
		importer = FeedImporter.from_url(url='file://'+_to_feed_path('test.ics'),
										 organization=test_org)
		reports = list(importer.import_new())

		# ensure all events were created
		self.assertEquals(len(reports),4)
		self.assertEquals(Event.objects.count(),self.init_ev_count+4)
		self.assertEquals(VEventRecord.objects.count(),self.init_vev_count+4)
		for r in reports:
			event = r.vevent_record.event
			self.assertIsNotNone(event)

		# test the first event fully
		event = reports[0].vevent_record.event
		# event starts on 11/20/2011 at 23:00 UTC, ends 2 hours later
		self.assertEquals(event.dtstart,test_event['dtstart'])
		self.assertEquals(event.dtend,test_event['dtend'])

		self.assertEquals(event.name,test_event['name'])
		self.assertTrue(event.description.startswith(test_event['description_stub']))

		# ensure the test_org is hosting the event
		self.assertEquals(test_org,Role.hosts.get(event=event).organization)

		# assert the OTB place was created and the expected notice was created about it
		otb = Place.objects.get(name__startswith='OTB',
								location__address__startswith='2518 E')
		self.assertEquals(event.place,otb)

		rstatus_notices = [n for n in reports[0].notices
							if isinstance(n,EventImportReport.LocationResolveStatus)]
		self.assertEquals(len(rstatus_notices),1)
		self.assertEquals(rstatus_notices[0].status,'RESOLVED_FIELD0_NAME_FIELD1_ADDRESS')


		# finally test the first VEventRecord
		record = VEventRecord.objects.get(event=event)
		self.assertEquals(record.uid,test_event['uid'])
		self.assertEquals(record.feed,importer.feed_instance)
		self.assertEquals(record.dtmodified,test_event['dtmodified'])

	def test_new_feed_start_filter(self):
		importer = FeedImporter.from_url(url='file://'+_to_feed_path('test.ics'))

		cutoff = datetime(2011,11,19)	# only 2 events occur after this
		reports = list(importer.import_new(start_filter=cutoff))

		# ensure just two events were created
		self.assertEquals(len(reports),2)
		self.assertEquals(Event.objects.count(),self.init_ev_count+2)
		for r in reports:
			event = r.vevent_record.event
			self.assertIsNotNone(event)
			self.assertGreaterEqual(event.dtstart,cutoff)

	def test_update_feed(self):
		fn = _to_feed_path('test.ics')
		importer = FeedImporter.from_url(url='file://'+_to_feed_path('test.ics'))

		# manually create the first event from the test.ics feed
		dummy_event = Event.objects.create(name=test_event['name'],
											dtstart=test_event['dtstart'],
											dtend=test_event['dtend'])
		VEventRecord.objects.create(feed=importer.feed_instance,
									uid=test_event['uid'],
									dtmodified=test_event['dtmodified'],
									event=dummy_event
									)
		
		# ensure the data is as expected before the test
		self.assertEquals(Event.objects.count(),self.init_ev_count+1)
		self.assertEquals(VEventRecord.objects.count(),self.init_vev_count+1)

		# ensure only three events are added
		reports = list(importer.import_new())
		self.assertEquals(Event.objects.count(),self.init_ev_count+4)
		self.assertEquals(VEventRecord.objects.count(),self.init_vev_count+4)

		# find the report for the event that already existed
		for r in reports:
			if r.vevent_record.event == dummy_event:
				# assert an RecordExists notice was created
				self.assertNotEqual(r.notices,[])
				self.assertNoticeIn(r,EventImportReport.RecordExists)

	def test_timezone_handling(self):
		fn = _to_feed_path('test.ics')
		importer = FeedImporter.from_url(url='file://'+_to_feed_path('timezone.ics'))
		reports = list(importer.import_new())

		# events start at 19:00 relative to the following timezones:
		# 1: Pacific (3am UTC), 2: Eastern (12am UTC), 3: UTC, 4: Unknown
		expected_dtstarts = [ 	datetime(2011, 11, 21, 3, 0),
								datetime(2011, 11, 21, 0, 0),
								datetime(2011, 11, 20, 19, 0),
							]
		for report,exp in zip(reports[:3],expected_dtstarts):
			self.assertEquals(report.vevent_record.event.dtstart,exp)
		
		# the last event has a made up timezone that won't process
		self.assertNoticeIn(reports[3],EventImportReport.UnknownTimezone)

		# finally try an ics file that has no default timezone (no X-WR-TIMEZONE)
		importer = FeedImporter.from_url(url='file://'+_to_feed_path('timezone-nodefault.ics'))
		reports = list(importer.import_new())
		self.assertNoticeIn(reports[0],EventImportReport.UnavailableTimezone)
