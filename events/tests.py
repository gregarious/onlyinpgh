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
        for batch in [True,False]:  # try both batched and unbatched requests
            page_names = [page['name'] for page in outsourcing.gather_place_pages((40.446,-80.014),500,batch_requests=batch)]
            self.assertIn(u'PNC Park',page_names)
            self.assertIn(u'Heinz Field',page_names)
        
        page_names = [page['name'] for page in outsourcing.gather_place_pages((40.446,-80.014),500,'pnc')]
        self.assertIn(u'PNC Park',page_names)
        self.assertNotIn(u'Heinz Field',page_names)

        # test that [] is returned if no pages exist
        no_pages = outsourcing.gather_place_pages((40.446,-80.014),500,'fiuierb2bkd7y')
        self.assertEquals(no_pages,[])

    def test_event_query(self):
        '''
        Tests that event gathering code works
        '''
        # can't really assert anything about some third party page's events. be content
        # with just testing that there's a few of them and the first one has some 
        # event-specific fields
        events = outsourcing.gather_event_info('40796308305')   #coca-cola's UID
        self.assertGreater(len(events),4)       # should be more than 4? why not.
        for event in events:
            self.assertIn('start_time',event.keys())
            self.assertIn('owner',event.keys())
        
        events = outsourcing.gather_event_info('121994841144517')   # Sarverville Cemetary -- should have no events
        self.assertEquals(events,[])

        # TODO: add assertRaises for gather_event_info with invalid page id