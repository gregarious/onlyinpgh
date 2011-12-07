"""
Unit tests for all API tools
"""

from django.test import TestCase
from onlyinpgh.apitools.facebook import get_basic_access_token, oip_client

class FacebookGraphTest(TestCase):
    def test_basic_access_token(self):
        '''
        Tests basic access token retrieval
        '''
        from onlyinpgh.apitools.facebook import OIP_APP_ID, OIP_APP_SECRET, OIP_ACCESS_TOKEN
        token = get_basic_access_token(OIP_APP_ID,OIP_APP_SECRET)
        self.assertEquals(token,OIP_ACCESS_TOKEN)

    def test_graph_lookup(self):
        '''
        Tests simple object lookup
        '''
        # Dependant on FB data. These are examples given on the Graph API
        # documentation page. If this test fails, check this site.
        # https://developers.facebook.com/docs/reference/api/
        page = oip_client.graph_api_object(40796308305)
        self.assertEquals(page['name'],'Coca-Cola')

        user = oip_client.graph_api_object('btaylor')
        self.assertEquals(user['name'],'Bret Taylor')

    def test_graph_query(self):
        '''
        Tests simple graph query (those that return arrays of data)
        '''
        # Dependant on FB data. These are examples given on the Graph API
        # documentation page. If this test fails, check this site.
        # https://developers.facebook.com/docs/reference/api/

        # test a Graph API search for posts
        results = oip_client.graph_api_query('search',type='post',q='watermelon',max_pages=1)
        # ensure that someone, anyone, is talking about watermelon publicly
        self.assertGreater(len(results),0)
        # just check that first result is a post because it has a 'from' key
        self.assertIn('from',results[0].keys())
        
        # test a connection query
        results = oip_client.graph_api_query('cocacola/events',limit=2,max_pages=3)
        # ensure paging and limit worked (contingent of course on Coke having 6 events)
        self.assertEquals(len(results),6)
        # just check that first result is an event because it has a 'start_time' field
        self.assertIn('start_time',results[0].keys())
        
    def test_place_search(self):
        '''
        Tests that place radius gathering code works
        '''
        # Dependant on FB data. Test built to search for Heinz Field and PNC Park within
        # 500 meters of a specific point.Could fail if geocoding info, building name, etc. 
        # changes in facebook data
        page_names = [page['name'] for page in oip_client.gather_place_pages((40.446,-80.014),500)]
        self.assertIn(u'PNC Park',page_names)
        self.assertIn(u'Heinz Field',page_names)
        
        page_names = [page['name'] for page in oip_client.gather_place_pages((40.446,-80.014),500,'pnc')]
        self.assertIn(u'PNC Park',page_names)
        self.assertNotIn(u'Heinz Field',page_names)

    def test_event_query(self):
        '''
        Tests that event gathering code works
        '''
        # can't really assert anything about some third party page's events. be content
        # with just testing that there's a few of them and the first one has some 
        # event-specific fields
        events = oip_client.gather_event_info(40796308305)   #coca-cola's UID
        self.assertGreater(len(events),4)       # should be more than 4? why not.
        for event in events:
            self.assertIn('start_time',event.keys())
            self.assertIn('owner',event.keys())

class FactualResolveTest(TestCase):
    def test_successful_request(self):
        '''
        Tests JSON response from a few Resolve API calls known to work
        '''
        self.fail('not yet implemented')

    def test_unsuccessful_request(self):
        '''
        Tests JSON response from a few Resolve API calls known to not work
        '''
        self.fail('not yet implemented')
    
    def test_response_to_object(self):
        '''
        Ensures JSON response gets packaged successfully into places models
        '''
        self.fail('not yet implemented')

class GoogleGeocodingTest(TestCase):

    # TODO: move some places.external tests here
    pass