import os, json, time
from django.test import TestCase
from django.core.exceptions import ValidationError

from onlyinpgh.places.models import Location, Place
from onlyinpgh.places import outsourcing

import logging
logging.disable(logging.CRITICAL)

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

class FactualResolutionTest(TestCase):
    def test_place_resolving(self):
        self.fail('not yet implemented')
        
    def test_raw_text_resolving(self):
        self.fail('not yet implemented')

class GoogleResolutionTest(TestCase):
    def test_location_resolving(self):
        # test basic address lookup -- ensure zip and geocoding info is filled in
        # https://maps.googleapis.com/maps/api/geocode/json?address=3411+Blvd+of+the+Allies&region=US&sensor=false
        time.sleep(.2)
        resolved = outsourcing.resolve_location(Location(address='3411 Blvd of the Allies'))
        self.assertEquals(resolved.address,'3411 Boulevard of the Allies')
        self.assertEquals(resolved.postcode,'15213')
        self.assertEquals(resolved.town,'Pittsburgh')
        self.assertEquals(resolved.state,'PA')
        self.assertEquals(resolved.country,'US')
        self.assertAlmostEquals(resolved.latitude,40.435938,3)   # assert equals up to 2 places
        self.assertAlmostEquals(resolved.longitude,-79.958309,3)

        # test zip codes properly bias searches -- if these fail, make sure the geocoding info
        # at the following links matches the expected values below:
        # https://maps.googleapis.com/maps/api/geocode/json?address=800+penn+ave%2C+15222&region=US&sensor=false
        # https://maps.googleapis.com/maps/api/geocode/json?address=800+penn+ave%2C+15221&region=US&sensor=false
        time.sleep(.2)
        resolved = outsourcing.resolve_location(Location(address='800 penn ave',postcode='15222'))
        self.assertAlmostEquals(resolved.latitude,40.443290,places=4)   # assert equals up to 2 places
        self.assertAlmostEquals(resolved.longitude,-79.999092,places=2)
        time.sleep(.2)
        resolved = outsourcing.resolve_location(Location(address='800 penn ave',postcode='15221'))
        self.assertAlmostEquals(resolved.latitude,40.442470,4)   # assert equals up to 2 places
        self.assertAlmostEquals(resolved.longitude,-79.881871,2)        

        # tests that geocoding info properly biases searches
        # expected results are based on the following geocoding API calls:
        # http://maps.googleapis.com/maps/api/geocode/json?region=US&sensor=false&bounds=40.438000%2C-80.005000%7C40.448000%2C-79.995000&address=800+penn+ave
        # http://maps.googleapis.com/maps/api/geocode/json?region=US&sensor=false&bounds=40.437000%2C-79.905000%7C40.447000%2C-79.895000&address=800+penn+ave
        time.sleep(.2)
        resolved = outsourcing.resolve_location(Location(address='800 penn ave',latitude=40.443,longitude=-80))
        self.assertEquals(resolved.postcode,'15222')
        time.sleep(.2)
        resolved = outsourcing.resolve_location(Location(address='800 penn ave',latitude=40.442,longitude=-79.9))
        self.assertEquals(resolved.postcode,'15221')

        # bad address
        time.sleep(.2)
        unresolved = outsourcing.resolve_location(Location(address='fakey fake double false address'))
        self.assertIsNone(unresolved)

    def test_raw_text_resolving(self):
        time.sleep(.2)
        # text raw text resolving
        resolved = outsourcing.text_to_location('425 n craig street, pittsburgh, pa')
        self.assertEquals(resolved.address,'425 N Craig St')
        self.assertEquals(resolved.postcode,'15213')
        self.assertEquals(resolved.town,'Pittsburgh')
        self.assertEquals(resolved.state,'PA')
        self.assertEquals(resolved.country,'US')

        # text resolving with seed Location
        time.sleep(.2)
        resolved = outsourcing.text_to_location('800 Penn Ave',Location(town='Pittsburgh'))
        self.assertEquals(resolved.postcode,'15221')
        time.sleep(.2)
        resolved = outsourcing.text_to_location('800 Penn Ave',Location(town='Turtle Creek'))
        self.assertEquals(resolved.postcode,'15145')

        # shouldn't resolve at all: return None
        unresolved = outsourcing.text_to_location('fakey fake double false address')
        self.assertIsNone(unresolved)
        
    def test_address_normalization(self):
        in_out_pairs = (
            ('400 south bouquet st','400 S Bouquet St'),
            ('6351 walnut street apt. 5','6351 Walnut St #5'),
            ('one schenley drive','1 Schenley Dr'),
            ('fakey fake double false address',None),
        )

        for unnormal,expected in in_out_pairs:
            time.sleep(.2)
            msg = 'normalized(%s) != %s' % (unicode(unnormal),expected)
            self.assertEquals(
                outsourcing.normalize_street_address(unnormal),
                expected,
                msg=msg)

class FBBaseInterfaceTest(TestCase):
    def test_fb_place_search(self):
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

class FBPlaceInsertion(TestCase):
    def test_fb_new_place(self):
        '''
        Tests that a truly new place is inserted correctly.
        '''
        self.fail('not yet implemented')

    def test_fb_existing_place(self):
        '''
        Tests that an place is not created if an existing place already exists.
        '''
        self.fail('not yet implemented')

    def test_fb_bad_place(self):
        '''
        Tests that a nonexistant FB place insertion attempt fails gracefully.
        '''
        self.fail('not yet implemented')      