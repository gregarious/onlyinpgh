"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import random, datetime

from django.test import TestCase

from onlyinpgh.utils.testing import load_test_json
from onlyinpgh.events import outsourcing
from onlyinpgh.events.models import *

import logging
logging.disable(logging.CRITICAL)

class FBEventPulling(TestCase):    
    def test_fb_page_event_pull(self):
        '''
        Tests code that pulls all events info from a page.
        '''
        page_ids = ['40796308305',      # coca-cola's UID
                    '121994841144517',  # place that will probably never have any events
                    '828371892334123']  # invalid fbid
        # add 100 random ids to the list to ensure batch code is working well
        page_ids.extend([str(random.randint(1e13,1e14)) for i in range(100)])
        random.shuffle(page_ids)

        pid_events_map = outsourcing.gather_event_info(page_ids)
        self.assertEquals(set(pid_events_map.keys()),set(page_ids))

        # can't really assert anything about some third party page's events. be content
        # with just testing that there's a few of them and the first one has some 
        # event-specific fields
        valid_events = pid_events_map['40796308305']
        self.assertGreater(len(valid_events),4)       # should be more than 4? why not.
        for event in valid_events:
            self.assertIn('start_time',event.keys())
            self.assertIn('owner',event.keys())

        # these two should return empty lists        
        self.assertEquals(pid_events_map['121994841144517'],[])
        self.assertEquals(pid_events_map['828371892334123'],[])

        # ignore the rest of the requests -- they were just to test batch

class FBEventInsertion(TestCase):
    fixtures = ['events/testfb.json']
    
    def test_fb_new_event_live(self):
        '''
        Tests that the live-download Facebook event process works.
        '''
        event_fbid = '143239769119840'        # pgh marathon event
        event_count_before = Event.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(FacebookEventRecord.DoesNotExist):
            FacebookEventRecord.objects.get(fb_id=event_fbid)
        
        outsourcing.event_fbid_to_event(event_fbid)
        
        self.assertEquals(Event.objects.count(),event_count_before+1)
        # now the FBPageRecord should exist
        try:
            FacebookEventRecord.objects.get(fb_id=event_fbid)
        except FacebookEventRecord.DoesNotExist:
            self.fail('FacebookEventRecord not found')

    def test_fb_new_event(self):
        '''
        Tests that all fields from a Facebook page to event are inserted 
        correctly.
        
        (uses predefined page both to test cache functionality and to ensure
        data is as expected)
        '''
        event_fbid = '286153888063194'        # Oxford 5k
        event_cache = {event_fbid: load_test_json('events','oxford_5k.json')}
        event_count_before = Event.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(FacebookEventRecord.DoesNotExist):
            FacebookEventRecord.objects.get(fb_id=event_fbid)

        # TODO: after refactoring, also provide the cached fb page for mr. smalls. that way we can test 
        #       for organization/place properties (see below TODO)
        outsourcing.event_fbid_to_event(event_fbid,fbevent_cache=event_cache)
        
        self.assertEquals(Event.objects.count(),event_count_before+1)
        try:
            event = Event.objects.get(name=u'Oxford Athletic Club Freaky 5K')
        except Event.DoesNotExist:
            self.fail('Event not inserted')

        try:
            # make sure the stored FBEventRecord has the correct Event set
            event_on_record = FacebookEventRecord.objects.get(fb_id=event_fbid).associated_event
            self.assertEquals(event_on_record,event)
        except Event.DoesNotExist:
            self.fail('FacebookEventRecord not found!')            

        # check properties of event were stored correctly (see http://graph.facebook.com/291107654260858)
        # event goes from 10/29/11 13:30 16:30 (UTC time)
        self.assertEquals(event.dtstart,datetime.datetime(2011,10,29,13,30))
        self.assertEquals(event.dtend,datetime.datetime(2011,10,29,16,30))
        self.assertTrue(event.description.startswith(u'Join the Steel City Road Runners Club'))

        # TODO: test place and organization settings after refactoring and allowing cached pages

    def test_fb_existing_event(self):
        '''
        Tests that an event is not created if an existing event already exists.
        '''
        event_fbid = '291107654260858'         # mr. smalls event (already exists via fixture)
        event_cache = {event_fbid: load_test_json('events','mr_smalls_event.json')}
        event_count_before = Event.objects.count()
        record_count_before = FacebookEventRecord.objects.count()

        outsourcing.event_fbid_to_event(event_fbid,fbevent_cache=event_cache)
        # assert some 'already exists' error is raised
        self.fail('not yet implemented')
        self.assertEquals(event_count_before,Organization.objects.count())

        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookEventRecord.objects.count())

    def test_fb_bad_event(self):
        '''
        Tests that a nonexistant FB event insertion attempt fails gracefully.
        '''
        event_fbid = '139288502700092394'     # should be bogus
        event_count_before = Event.objects.count()
        record_count_before = FacebookEventRecord.objects.count()

        outsourcing.event_fbid_to_event(event_fbid)
        # assert some facebook error is raised
        self.fail('not yet implemented')
        self.assertEquals(event_count_before,Organization.objects.count())

        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookEventRecord.objects.count())
