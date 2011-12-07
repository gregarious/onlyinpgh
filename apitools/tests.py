"""
Unit tests for all API tools
"""

from django.test import TestCase
from onlyinpgh.apitools.facebook import get_basic_access_token, oip_client, BatchCommand
import json

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
        page = oip_client.graph_api_objects('40796308305')
        self.assertEquals(page['name'],'Coca-Cola')
        page = oip_client.graph_api_objects(40796308305)
        self.assertEquals(page['name'],'Coca-Cola')

        users = oip_client.graph_api_objects(['btaylor','zuck'])
        self.assertEquals(users[0]['name'],'Bret Taylor')
        self.assertEquals(users[1]['name'],'Mark Zuckerberg')

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

    def test_batch_request(self):
        '''
        Tests batch API interface
        '''
        # Dependant on FB data. These are examples ones similar to those 
        # listed on the Graph API BatchRequest documentation:
        # https://developers.facebook.com/docs/reference/api/batch

        ### 
        # Main test consists of querying for events associated with Coca-Cola,
        # results are tested to be sure certain event-specific fields are 
        # returned. The status code of the full response is also returned

        # Also, we want to test the behavior of the "omit_response_on_success" 
        # variable so we run it twice. Once where the first response is omitted 
        # and we expect the full batch response to have a None first object, and 
        # once where it is not omitted we expect it to have a list of event stubs.
        for omit_first_response in (True,False):
            batch_request = [ BatchCommand('cocacola/events',
                                            options={'limit':5},
                                            name='get-events',
                                            omit_response_on_success=omit_first_response),
                              BatchCommand('',
                                            options={'ids':'{result=get-events:$.data.*.id}'}),
                            ]
        full_response = oip_client.run_batch_request(batch_request,process_response=False)
        self.assertEquals(len(full_response),2)
        
        first_resp,second_resp = full_response
        # test result of first command
        if omit_first_response:
            self.assertIsNone(first_resp)
        else:
            body = json.loads(first_resp['body'])
            for stub in body['data']:
                self.assertIn('start_time',stub)    # duck test for event stub
        
        # test response from second command
        self.assertEquals(second_resp['code'],200)
        body = json.loads(second_resp['body'])
        for event in body.values():
            # test that results are events via "duck-typing" test
            self.assertIn('start_time',event)
            self.assertIn('owner',event)

        ### 
        # Also test the behavior when process_response is left to be True
        # This is a simpler command that requests Coca-Cola's user object and 
        # its first 5 events in one go. Leaving process_response to True in the
        # run_batch_request() call should yield responses with already-JSON parsed
        # body content only
        batch_request = [ BatchCommand('cocacola'),
                          BatchCommand('cocacola/events',
                                            options={'limit':5}),
                        ]
        responses = oip_client.run_batch_request(batch_request)
        self.assertEquals(len(responses),2)
        self.assertIn('username',responses[0])  # first response is a single user object
        for event in responses[1]['data']:     # second response is a map of {id:event stubs}
            self.assertIn('name',event)
            self.assertIn('start_time',event)

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