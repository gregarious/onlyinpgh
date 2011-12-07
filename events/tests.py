"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from onlyinpgh.events import outsourcing

class OutsourcingTest(TestCase):
    def test_place_search(self):
        '''
        Tests that place radius gathering code works
        '''
        # Dependant on FB data. Test built to search for Heinz Field and PNC Park within
        # 500 meters of a specific point.Could fail if geocoding info, building name, etc. 
        # changes in facebook data
        page_names = [page['name'] for page in outsourcing.gather_place_pages((40.446,-80.014),500)]
        self.assertIn(u'PNC Park',page_names)
        self.assertIn(u'Heinz Field',page_names)
        
        page_names = [page['name'] for page in outsourcing.gather_place_pages((40.446,-80.014),500,'pnc')]
        self.assertIn(u'PNC Park',page_names)
        self.assertNotIn(u'Heinz Field',page_names)

    def test_event_query(self):
        '''
        Tests that event gathering code works
        '''
        # can't really assert anything about some third party page's events. be content
        # with just testing that there's a few of them and the first one has some 
        # event-specific fields
        events = outsourcing.gather_event_info(40796308305)   #coca-cola's UID
        self.assertGreater(len(events),4)       # should be more than 4? why not.
        for event in events:
            self.assertIn('start_time',event.keys())
            self.assertIn('owner',event.keys())