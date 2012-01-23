"""
Unit tests for all API tools
"""

from django.test import TestCase
from onlyinpgh.outsourcing.apitools.facebook import get_basic_access_token, BatchCommand
from onlyinpgh.outsourcing.apitools.google import GoogleGeocodingResponse, GoogleAPIError
from onlyinpgh.outsourcing.apitools import geocoding_client, facebook_client, factual_client

import json, time, os, logging
logging.disable(logging.CRITICAL)

class FacebookGraphTest(TestCase):
    def test_basic_access_token(self):
        '''
        Tests basic access token retrieval
        '''
        from onlyinpgh.outsourcing.apitools.facebook import OIP_APP_ID, OIP_APP_SECRET, OIP_ACCESS_TOKEN
        token = get_basic_access_token(OIP_APP_ID,OIP_APP_SECRET)
        self.assertEquals(token,OIP_ACCESS_TOKEN)

    def test_graph_lookup(self):
        '''
        Tests simple object lookup
        '''
        # Dependant on FB data. These are examples given on the Graph API
        # documentation page. If this test fails, check this site.
        # https://developers.facebook.com/docs/reference/api/
        page = facebook_client.graph_api_objects_request('40796308305')
        self.assertEquals(page['name'],'Coca-Cola')
        page = facebook_client.graph_api_objects_request(40796308305)
        self.assertEquals(page['name'],'Coca-Cola')

        users = facebook_client.graph_api_objects_request(['btaylor','zuck'])
        self.assertEquals(users[0]['name'],'Bret Taylor')
        self.assertEquals(users[1]['name'],'Mark Zuckerberg')

    def test_page_lookup(self):
        '''
        Tests lookup of Facebook pages specifically.
        '''
        # also try the page-specific helper function
        page = facebook_client.graph_api_page_request('40796308305')
        self.assertEquals(page['name'],'Coca-Cola')

        # should fail on user page lookup
        with self.assertRaises(TypeError):
            page = facebook_client.graph_api_page_request('btaylor')

    def test_graph_query(self):
        '''
        Tests simple graph query (those that return arrays of data)
        '''
        # Dependant on FB data. These are examples given on the Graph API
        # documentation page. If this test fails, check this site.
        # https://developers.facebook.com/docs/reference/api/

        # test a Graph API search for posts
        results = facebook_client.graph_api_collection_request('search',type='post',q='watermelon',max_pages=1)
        # ensure that someone, anyone, is talking about watermelon publicly
        self.assertGreater(len(results),0)
        # just check that first result is a post because it has a 'from' key
        self.assertIn('from',results[0].keys())
        
        # test a connection query
        results = facebook_client.graph_api_collection_request('cocacola/events',limit=2,max_pages=3)
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
        full_response = facebook_client.run_batch_request(batch_request,process_response=False)
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
        responses = facebook_client.run_batch_request(batch_request)
        self.assertEquals(len(responses),2)
        self.assertIn('username',responses[0])  # first response is a single user object
        for event in responses[1]['data']:     # second response is a map of {id:event stubs}
            self.assertIn('name',event)
            self.assertIn('start_time',event)

        # TODO: assert errors are thrown when invalid responses returned

class FactualResolveTest(TestCase):
    def test_successful_request(self):
        '''
        Tests response from a few Resolve API calls known to work
        '''
        # tests almost complete entry
        result = factual_client.resolve(name='primanti brothers',
                                            town='pittsburgh',state='PA',
                                            latitude=40.45,longitude=-79.98).get_resolved_result()
        self.assertIsNotNone(result)
        self.assertEquals(result['name'],'Primanti Brothers')
        self.assertEquals(result['postcode'],'15222')


        # tests simple one with incomplete name
        result = factual_client.resolve(name='otb',town='pittsburgh',state='pa').get_resolved_result()
        self.assertIsNotNone(result)
        self.assertEquals(result['name'],'OTB Bicycle Cafe')
        self.assertEquals(result['postcode'],'15203')

        # tests one that requires a more specific town to work
        result = factual_client.resolve(name='petco',town='monroeville',state='pa').get_resolved_result()
        self.assertIsNotNone(result)
        self.assertEquals(result['name'],'Petco')
        self.assertEquals(result['postcode'],'15146')

    def test_unsuccessful_request(self):
        '''
        Tests response from a few Resolve API calls known to not work
        '''

        # tests a totally out there response
        result = factual_client.resolve(name='primanti brothers',town='San Diego',state='CA').get_resolved_result()
        self.assertIsNone(result)

        # tests one too ambiguous to resolve
        result = factual_client.resolve(name='primanti brothers',town='pittsburgh',state='PA').get_resolved_result()
        self.assertIsNone(result)

    # hard to do this cause resolve() is so fuckin' IRONCLAD HARDCORE
    # def test_bad_request(self):
    #     '''
    #     Asserts exception is raised on a bad Factual request.
    #     '''
    
class GoogleGeocodingTest(TestCase):
    def setUp(self):
        self.client = geocoding_client

    def _quickrun(self,address):
        '''shortcut to return the best result (wrapped) for a simple query'''
        time.sleep(.2)      # ironically, we sleep for a bit in quickrun. don't want to go over API limit
        return self.client.run_geocode_request(address).best_result(True)

    def _open_test_json(self,fn):
        return open(os.path.join(os.path.dirname(__file__),'test_json','gg',fn))

    def _json_to_best_result(self,fn):
        response = GoogleGeocodingResponse(self._open_test_json(fn))
        return response.best_result(wrapped=True)

    def test_query_options(self):
        '''Tests all API request options behave as expected (no sensor test currently)'''
        # test bounding box search: adapted from http://code.google.com/apis/maps/documentation/geocoding/#Viewports
        result_nobounds = self.client.run_geocode_request('Winnetka',bounds=None).best_result(wrapped=True)
        self.assertEquals(result_nobounds.get_address_component('administrative_area_level_1'),'IL')
        result_bounds = self.client.run_geocode_request('Winnetka',bounds=((34.17,-118.60),(34.23,-118.50))).best_result(wrapped=True)
        self.assertEquals(result_bounds.get_address_component('administrative_area_level_1'),'CA')

        # test region search: adapted from http://code.google.com/apis/maps/documentation/geocoding/#RegionCodes
        result_us = self.client.run_geocode_request('Toledo',region='us').best_result(wrapped=True)
        self.assertEquals(result_us.get_address_component('country'),'US')
        result_es = self.client.run_geocode_request('Toledo',region='es').best_result(wrapped=True)
        self.assertEquals(result_es.get_address_component('country'),'ES')
    
    def test_preprocessing(self):
        '''Tests preprocessing to avoid particular quirks of Google API'''
        # test removal of parenthesis
        self.assertEquals(
            self.client._preprocess_address('(hello) 210 Atwood St. (2nd Fl)'), 
            ' 210 Atwood St. ')
        # test translation of pound sign to "Unit "
        self.assertEquals(
            self.client._preprocess_address('6351 Walnut St. #5'),
            '6351 Walnut St. Unit 5')

        # tests that a PreprocessingOccurred is generated
        result = self._quickrun('6351 Walnut St., #5, Pittsburgh, PA')
        #self.assertTrue(result.contains_notice('PreprocessingOccurred'))

    def test_multiple_address_components(self):
        '''ensures handling of results with duplicate address components works correctly'''
        result = GoogleGeocodingResponse(self._open_test_json('pittsburgh.json')).best_result(wrapped=True)
        # ensure multiple results are returned if asked for
        self.assertEquals(len(result.get_address_component('political',allow_multiple=True)),4)
        # ensure exception is thrown if multiple results aren't asked for
        with self.assertRaises(KeyError):
            result.get_address_component('political')
        # ensure empty list is returned works for unavaible key whene allow_multiple=True
        self.assertEquals(len(result.get_address_component('route',allow_multiple=True)),0)
        # ensure default argument works for unavaible key
        self.assertEquals(result.get_address_component('route'),None)
        self.assertEquals(result.get_address_component('route',default='boo boo kitty'),'boo boo kitty')

    def test_api_response_content(self):
        '''runs a battery of API calls against the actual live service'''
        # test abbreviation of "South" and "Street"
        result = self._quickrun('201 South Bouquet Street')
        self.assertEquals(result.get_address_component('street_number'),    '201')
        self.assertEquals(result.get_address_component('route'),            'S Bouquet St')

        # test abbreviation of "Street" and interpretation of "Apt." 
        # also that Google API still returns a "partial match" for address with a subpremise 
        result = self._quickrun('6351 Walnut Street Apt. 5, Pittsburgh, PA')
        self.assertEquals(result.get_address_component('subpremise'),       '5')
        self.assertEquals(result.get_address_component('street_number'),    '6351')
        self.assertEquals(result.get_address_component('route'),            'Walnut St') 
        #self.assertTrue(result.contains_notice('PartialMatch'))

        # test that all address numbers become integers and abbreviation of "Drive"
        result = self._quickrun('One Schenley Drive, Pittsburgh, PA')
        self.assertEquals(result.get_address_component('street_number'),    '1')
        self.assertEquals(result.get_address_component('route'),            'Schenley Dr')

        # tests named building lookup
        # NOTE: Google keeps changing response content. Stopped testing this.
        #result = self._quickrun('Carnegie Museum of Natural History, Pittsburgh, PA')
        #self.assertTrue(result.get_address_component('establishment').startswith('Carnegie Museum'))

        # tests intersection with "at"
        result = self._quickrun('Fifth at South Craig St, Pittsburgh, PA')
        self.assertIn('intersection',result['types'])
        self.assertEquals(result.get_address_component('intersection'), 'Fifth Ave & S Craig St')
        
        # tests that "Blvd" abbreviation gets expanded if not the last word in a street address
        result = self._quickrun('3518 Blvd of the Allies')
        self.assertEquals(result.get_address_component('street_number'),    '3518')
        self.assertEquals(result.get_address_component('route'),            'Boulevard of the Allies')

        # tests that a partial match is given for an address that's eambiguous because of no North/South designation
        result = self._quickrun('400 Craig St, Pittsburgh, PA, 15213')
        self.assertIn('Craig St',result.get_address_component('route'))
        #self.assertTrue(result.contains_notice('PartialMatch'))
    
        ### remaining tests are to keep an eye on the Google API to see if any useful changes occur
        ### if any of these fail, they aren't necessarily problems, it would just be useful to be
        ### notified about it because it could change some pre/post processing assumptions

        # make sure intersection results still return only one of the routes from the intersection in address_components
        result = self._quickrun('Fifth at South Craig St, Pittsburgh, PA')
        self.assertIn('intersection',result['types'])
        # (if more than one route is in the result a KeyError should be thrown)
        self.assertEquals(result.get_address_component('route'),'Fifth Ave')
        
        # test 'floor' results aren't returned
        result = self._quickrun('249 N Craig St (Floor 2), Pittsburgh, PA')
        self.assertNotIn('floor',result['types'])
        self.assertIsNone(result.get_address_component('floor'))

        # test 'room' results aren't returned
        result = self._quickrun('Posvar Hall, Room 1501')
        self.assertNotIn('room',result['types'])
        self.assertIsNone(result.get_address_component('room'))

        # test 'post_box' results aren't returned
        result = self._quickrun('P.O. Box 5452, Pittsburgh, PA 15206')
        self.assertNotIn('post_box',result['types'])
        self.assertIsNone(result.get_address_component('post_box'))

    def test_normalized_address_construction(self):
        '''tests that addresses are correctly normalized'''
        # read in some sample JSON and test what get_address spits out
        json_address_pairs = (
            ('1555-coraopolis-heights-rd-ste-4200.json','1555 Coraopolis Heights Rd #4200'),
            ('cathedral.json',                          'Cathedral of Learning'),
            ('pittsburgh-zoo.json',                     'Pittsburgh Zoo and PPG Aquarium, 7340 Butler St'),
            ('forbes-halket-intersection.json',         'Forbes Ave & Halket St'),
            ('north-oakland.json',                      '')
        )

        for fn,expected_addr in json_address_pairs:
            address = self._json_to_best_result(fn).get_street_address()
            self.assertEquals(address,expected_addr,
                                msg="Expected address '%s', got '%s', from sample JSON '%s'" % ( expected_addr, address, fn ) )

    def test_concrete_address_question(self):
        '''ensures is_address_concrete method works'''
        cathedral = self._json_to_best_result('cathedral.json')
        noakland = self._json_to_best_result('north-oakland.json')
        atwood = self._json_to_best_result('atwood.json')
        zoo = self._json_to_best_result('pittsburgh-zoo.json')

        # First test without counting numberless results as concrete: only zoo should succeed
        self.assertTrue(zoo.is_address_concrete(allow_numberless=False))
        self.assertFalse(cathedral.is_address_concrete(allow_numberless=False))
        self.assertFalse(noakland.is_address_concrete(allow_numberless=False))
        self.assertFalse(atwood.is_address_concrete(allow_numberless=False))

        # Now allow numberless, all but north oakland should succeed
        self.assertTrue(zoo.is_address_concrete())
        self.assertTrue(cathedral.is_address_concrete())
        self.assertFalse(noakland.is_address_concrete())
        self.assertTrue(atwood.is_address_concrete())
    
    def test_api_error_handling(self):
        '''ensure geocoding wrapper raises GoogleAPIError when appropriate'''
        # a bit hacky using a private function, i admit, but since request is received in 
        # same function error is raised from, we can't simulate an error situation anymore
        json_failures = ('failure-over-query-limit.json','failure-request-denied.json','failure-invalid-request.json')
        for fn in json_failures:
           with self.assertRaises(GoogleAPIError):
                self.client._package_response(self._open_test_json(fn).read())

    def test_zero_results_handling(self):
        '''ensure geocoding wrapper gracefully handles zero results returned'''
        response = GoogleGeocodingResponse(self._open_test_json('zero-results.json'))
        self.assertEquals(len(response.results),0)
        self.assertIsNone(response.best_result(),None)
