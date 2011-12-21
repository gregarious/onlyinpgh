"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import random

from django.test import TestCase
from onlyinpgh.events import outsourcing

class FBBaseInterfaceTest(TestCase):
    def test_fb_event_pull(self):
        '''
        Tests that single event pulling code works
        '''
        outsourcing.event = '291107654260858'
    
    def test_fb_page_event_pull(self):
        '''
        Tests code that pulls all events info from a page.
        '''
        page_ids = ['40796308305',      # coca-cola's UID
                    '121994841144517',  # place that will probably never have any events
                    '828371892334123']) # invalid fbid
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
        self.assertEquals(events['121994841144517'],[])
        self.assertEquals(events['828371892334123'],[])

        # ignore the rest of the requests -- they were just to test batch

class FBEventInsertion(TestCase):
    def test_fb_new_event(self):
        '''
        Tests that a truly new event is inserted correctly.
        '''
        self.fail('not yet implemented')

    def test_fb_existing_event(self):
        '''
        Tests that an event is not created if an existing event already exists.
        '''
        self.fail('not yet implemented')

    def test_fb_bad_event(self):
        '''
        Tests that a nonexistant FB event insertion attempt fails gracefully.
        '''
        self.fail('not yet implemented')      