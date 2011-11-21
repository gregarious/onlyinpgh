import os, json, time
from django.test import TestCase
from django.core.exceptions import ValidationError

from places.models import Location, Place, LocationLookupNotice
from places.external import GGAgent, GGResponse, APIFailureError

SAMPLE_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'test_json')

class LocationModelTest(TestCase):
    @property
    def valid_location_base(self):
        '''
        property to return a basic Location object that is known to be valid
        for use in tests
        '''
        return Location(country='US',
                        state='PA',
                        town='Pittsburgh',
                        neighborhood=None,
                        postcode='15213',
                        address='4620 Henry Street',
                        latitude=40.446487,
                        longitude=-79.948524)

    def test_base_is_valid(self):
        '''Ensures the location used as the basis of many tests is valid'''
        self.valid_location_base.save()

    def test_valid_country_format(self):
        '''Tests that all country codes have either 0 or 2 characters'''
        # locations with 1 or >2 letters are no good
        invalid_countries = ['U','USA','United States']
        for invalid_country in invalid_countries:
            l = self.valid_location_base
            l.country = invalid_country
            self.assertRaises(ValidationError,l.save)

        valid_countries = ['','US']
        for valid_country in valid_countries:
            l = self.valid_location_base
            l.country = valid_country
            l.save()

    def test_valid_state_format(self):
        '''Tests that all states have either 0 or 2 characters'''
        invalid_states = ['P','PAX','Pennsylvania']
        for invalid_state in invalid_states:
            l = self.valid_location_base
            l.state = invalid_state
            self.assertRaises(ValidationError,l.save)

        valid_states = ['','PA']
        for valid_state in valid_states:
            l = self.valid_location_base
            l.state = valid_state
            l.save()

    def test_geocode_bounds(self):
        '''
        Ensures latitude and longitude are within accepted ranges.
        '''
        # does an exhaustive 3x3 attempt to set various lat/long values, should only succeed once
        for lat,lat_valid in ((-90.1,False),(90.1,False),(40.4,True)):
            for lon,lon_valid in ((-180.1,False),(180.1,False),(-80,True)):
                location = Location(latitude=lat,longitude=lon)
                if lon_valid and lat_valid:
                    location.save()    # should be ok
                else:
                    with self.assertRaises(ValidationError):
                        location.save()

    def test_complete_geocode(self):
        '''Ensures any Location with a longitude has a latitude and vice-versa.'''
        l = self.valid_location_base
        l.longitude = None
        self.assertRaises(ValidationError,l.save)                
        l = self.valid_location_base
        l.latitude = None
        self.assertRaises(ValidationError,l.save)                

class GoogleGeocodingTest(TestCase):
    '''
    Tests 3 major features of the wrapper around the Google Geocidng API that
    is used to normalize/resolve locations:
      1. Handling of request preprocessing
      2. General API response expectations
      3. Notice generation for non-perfect lookups
    '''
    def setUp(self):
        self.api = GGAgent()
    
    def _quickrun(self,address):
        '''shortcut to return the best result for the given address query'''
        time.sleep(.2)      # ironically, we sleep for a bit in quickrun. don't want to go over API limit
        return self.api.run_query(address).best_result()

    def _read_test_json(self,fn):
        with open(os.path.join(SAMPLE_JSON_DIR,fn)) as fp:
            return json.load(fp)

    def test_query_options(self):
        '''Tests all API request options behave as expected (no sensor test currently)'''
        # test bounding box search: adapted from http://code.google.com/apis/maps/documentation/geocoding/#Viewports
        result_nobounds = self.api.run_query('Winnetka',bounds=None).best_result()
        self.assertEquals(result_nobounds.get_address_component('administrative_area_level_1'),'IL')
        result_bounds = self.api.run_query('Winnetka',bounds=((34.17,-118.60),(34.23,-118.50))).best_result()
        self.assertEquals(result_bounds.get_address_component('administrative_area_level_1'),'CA')

        # test region search: adapted from http://code.google.com/apis/maps/documentation/geocoding/#RegionCodes
        result_us = self.api.run_query('Toledo',region='us').best_result()
        self.assertEquals(result_us.get_address_component('country'),'US')
        result_es = self.api.run_query('Toledo',region='es').best_result()
        self.assertEquals(result_es.get_address_component('country'),'ES')
    
    def test_preprocessing(self):
        '''Tests preprocessing to avoid particular quirks of Google API'''
        # test removal of parenthesis
        self.assertEquals(
            self.api.preprocess_address('210 Atwood St. (2nd Fl)'), 
            '210 Atwood St. ')
        self.assertEquals(
            self.api.preprocess_address('(super (embedded)) 100 Elm St.'),
            ' 100 Elm St.')
        # test translation of pound sign to "Unit "
        self.assertEquals(
            self.api.preprocess_address('6351 Walnut St. #5'),
            '6351 Walnut St. Unit 5')

        # tests that a PreprocessingOccurred is generated
        result = self._quickrun('6351 Walnut St., #5, Pittsburgh, PA')
        self.assertTrue(result.contains_notice('PreprocessingOccurred'))
    

    def test_multiple_address_components(self):
        '''ensures handling of results with duplicate address components works correctly'''
        result = GGResponse(self._read_test_json('pittsburgh.json')).best_result()
        # ensure multiple results are returned if asked for
        self.assertEquals(len(result.get_address_component('political',allow_multiple=True)),4)
        # ensure exception is thrown if multiple results aren't asked for
        with self.assertRaises(KeyError):
            result.get_address_component('political')

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
        self.assertTrue(result.contains_notice('PartialMatch'))

        # test that all address numbers become integers and abbreviation of "Drive"
        result = self._quickrun('One Schenley Drive, Pittsburgh, PA')
        self.assertEquals(result.get_address_component('street_number'),    '1')
        self.assertEquals(result.get_address_component('route'),            'Schenley Dr')

        # tests named building lookup
        result = self._quickrun('Cathedral of Learning, Pittsburgh, PA')
        self.assertEquals(result.get_address_component('establishment'), 'Cathedral of Learning')

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
        self.assertTrue(result.contains_notice('PartialMatch'))
    
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
        with self.assertRaises(KeyError):
            result.get_address_component('floor')

        # test 'room' results aren't returned
        result = self._quickrun('Posvar Hall, Room 1501')
        self.assertNotIn('room',result['types'])
        with self.assertRaises(KeyError):
            result.get_address_component('room')

        # test 'post_box' results aren't returned
        result = self._quickrun('P.O. Box 5452, Pittsburgh, PA 15206')
        self.assertNotIn('post_box',result['types'])
        with self.assertRaises(KeyError):
            result.get_address_component('post_box')

    def test_notice_generation(self):
        '''ensure the correct API response notices get generated'''
        # sanity test: ensure if we don't build a GGResult with notices, none are returned
        with self.assertRaises(APIFailureError):
            result = GGResponse(self._read_test_json('400-craig-st.json')).best_result()
            result.notices

        ### cycle thru the following files and test that all the given notices are generated
        json_notice_pairs = (
            ('forbes-halket-intersection.json',   ['PartialMatch']),
            ('400-craig-st.json',                 ['PartialMatch','MultipleResults']),
            ('400-craig-st-no-partial.json',      ['MultipleResults','~PartialMatch']),
            ('cathedral.json',                    ['NoStreetAddress']),
            ('north-oakland.json',                ['NonConcreteAddress']))
        
        for fn,notices in json_notice_pairs:
            response = GGResponse(self._read_test_json(fn),LocationLookupNotice())
            result = response.best_result()
            for notice in notices:
                if notice.startswith('~'):
                    notice = notice[1:]
                    self.assertFalse(result.contains_notice(notice),
                                        msg="Unexpected '%s' notice from sample JSON '%s'" % (notice,fn))
                else:
                    self.assertTrue(result.contains_notice(notice),
                                        msg="No expected '%s' notice from sample JSON '%s'" % (notice,fn))
        
        # dummy LocationLookupNotice stub won't work here: must make actual live calls to test 
        #  notices that involve comparing request to response
        result = self._quickrun('6351 Walnut St. #5')
        self.assertTrue(result.contains_notice('PreprocessingOccurred'))

    def test_api_error_handling(self):
        '''ensure geocoding wrapper raises APIFailureErrors when appropriate'''
        json_failures = ('failure-over-query-limit.json','failure-request-denied.json','failure-invalid-request.json')
        for fn in json_failures:
            with self.assertRaises(APIFailureError):
                GGResponse(self._read_test_json(fn))

    def test_zero_results_handling(self):
        '''ensure geocoding wrapper gracefully handles zero results returned'''
        response = GGResponse(self._read_test_json('zero-results.json'))
        self.assertEquals(len(response.results),0)


# these belong elsewhere -- not testing basic Location assertions
    # def test_address_normalization(self):
    #     '''
    #     Ensures all street addresses saved in the DB are normalized.
    #     '''
    #     # Try to save a non-normalized address and see if it gets normalized
    #     # include interesting cases like apartment numbers
    #     self.fail()

    # def test_missing_field_completion(self):
    #     '''
    #     Various tests to ensure missing fields are filled if enough
    #     information is given.
    #     '''
    #     # do a bunch of tests here with some fairly easy pieces of information
    #     self.fail()