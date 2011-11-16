from django.test import TestCase

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
    	# test latitude is in [-90,90] and longitude is in [-180,180]
    	self.fail()

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