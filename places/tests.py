from django.test import TestCase
from django.core.exceptions import ValidationError

from onlyinpgh.places.models import *

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

class CloseLocationManagerTest(TestCase):
    def setUp(self):
        Location.objects.create(address='5467 Penn Ave',town='Pittsburgh',state='PA',
                                postcode='15206',latitude=40.464751,longitude=-79.93344)
        Location.objects.create(address='5469 Penn Ave',town='Pittsburgh',state='PA',
                                postcode='15206',latitude=40.464598,longitude=-79.933881)
        Location.objects.create(address='5151 Penn Ave',town='Pittsburgh',state='PA',
                                postcode='15206',latitude=40.464948,longitude=-79.940899)

    def test_get_close(self):
        lat,lng = 40.464237,-79.932940
        try:
            Location.close_manager.get_close(address='5467 Penn Ave',latitude=lat,longitude=lng)
        except Location.DoesNotExist:
            self.fail('close_get query failed.')

        # try two tests with the bounds too narrow to find. these should fail to find objects
        with self.assertRaises(Location.DoesNotExist):
            Location.close_manager.get_close(address='5467 Penn Ave',latitude=lat,longitude=lng,
                                        _close_options={'lat_error':1e-4})
        with self.assertRaises(Location.DoesNotExist):
            Location.close_manager.get_close(address='5467 Penn Ave',latitude=lat,longitude=lng,
                                        _close_options={'lng_error':1e-4})

        with self.assertRaises(Location.MultipleObjectsReturned):
            Location.close_manager.get_close(postcode='15206',latitude=lat,longitude=lng,
                                        _close_options={'assert_single_match':True})

    def test_get_close_or_create(self):
        lat,lng = 40.464237,-79.932940
        l,created = Location.close_manager.get_close_or_create(address='5467 Penn Ave',latitude=lat,longitude=lng)
        self.assertFalse(created)
        l,created = Location.close_manager.get_close_or_create(latitude=lat,longitude=lng)
        self.assertFalse(created)
        
        l,created = Location.close_manager.get_close_or_create(address='5468 Penn Ave',latitude=lat,longitude=lng)
        self.assertTrue(created)
        self.assertEquals(l.latitude,lat)
        self.assertEquals(l.longitude,lng)
        
