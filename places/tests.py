from django.test import TestCase
from django.core.exceptions import ValidationError

from places.models import Location, Place

class LocationModelTest(TestCase):
    def test_two_letter_us_state(self):
        """
        Tests that all US states have 2-letter entries.
        """
        # create a location and ensure US state with 1 or more than 3 letters fails. Also ensure that other countries have no such limits.
        self.fail()

    def test_geocode_bounds(self):
    	'''
    	Ensures latitude and longitude are within accepted ranges.
    	'''
    	# does an exhaustive 3x3 attempt to set various lat/long values, should only succeed once
    	for lat,lat_valid in ((-90.1,False),(90.1,False),(40.4,True)):
    		for lon,lon_valid in ((-180.1,False),(180.1,False),(-80,True)):
    			location = Location(latitude=lat,longitude=lon)
    			if lon_valid and lat_valid:
    				location.save()	# should be ok
    			else:
    				self.assertRaises(ValidationError,location.save)

    def test_minimum_information(self):
    	'''
    	Ensures a Location has a minimum amount of information before
    	it can be saved.
    	'''
    	# try to save an address without both long/lat and street address.
    	# also ensure providing either one or the other is ok
    	self.fail()

    def test_address_normalization(self):
    	'''
    	Ensures all street addresses saved in the DB are normalized.
    	'''
    	# Try to save a non-normalized address and see if it gets normalized
    	# include interesting cases like apartment numbers
    	self.fail()

    def test_missing_field_completion(self):
    	'''
    	Various tests to ensure missing fields are filled if enough
    	information is given.
    	'''
    	# do a bunch of tests here with some fairly easy pieces of information
    	self.fail()