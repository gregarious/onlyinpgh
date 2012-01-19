import os, json, random

from django.test import TestCase
from onlyinpgh.outsourcing.subtests import load_test_json

from onlyinpgh.places.models import *
from onlyinpgh.outsourcing.models import *

from onlyinpgh.outsourcing import places as pl_outsourcing
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError

import logging
logging.disable(logging.CRITICAL)

class FactualResolutionTest(TestCase):
    '''
    Tests for resolving a full Factual-backed place
    '''
    def test_place_resolving(self):
        self.fail('not yet implemented')
        
    def test_raw_text_resolving(self):
        self.fail('not yet implemented')

class GoogleResolutionTest(TestCase):
    def test_location_resolving(self):
        # test basic address lookup -- ensure zip and geocoding info is filled in
        # https://maps.googleapis.com/maps/api/geocode/json?address=3411+Blvd+of+the+Allies&region=US&sensor=false
        resolved = pl_outsourcing.resolve_location(Location(address='3411 Blvd of the Allies'))
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
        resolved = pl_outsourcing.resolve_location(Location(address='800 penn ave',postcode='15222'))
        self.assertAlmostEquals(resolved.latitude,40.443290,places=4)   # assert equals up to 2 places
        self.assertAlmostEquals(resolved.longitude,-79.999092,places=2)
        resolved = pl_outsourcing.resolve_location(Location(address='800 penn ave',postcode='15221'))
        self.assertAlmostEquals(resolved.latitude,40.442470,4)   # assert equals up to 2 places
        self.assertAlmostEquals(resolved.longitude,-79.881871,2)        

        # tests that geocoding info properly biases searches
        # expected results are based on the following geocoding API calls:
        # http://maps.googleapis.com/maps/api/geocode/json?region=US&sensor=false&bounds=40.438000%2C-80.005000%7C40.448000%2C-79.995000&address=800+penn+ave
        # http://maps.googleapis.com/maps/api/geocode/json?region=US&sensor=false&bounds=40.437000%2C-79.905000%7C40.447000%2C-79.895000&address=800+penn+ave
        resolved = pl_outsourcing.resolve_location(Location(address='800 penn ave',latitude=40.443,longitude=-80))
        self.assertEquals(resolved.postcode,'15222')
        resolved = pl_outsourcing.resolve_location(Location(address='800 penn ave',latitude=40.442,longitude=-79.9))
        self.assertEquals(resolved.postcode,'15221')

        # bad address
        unresolved = pl_outsourcing.resolve_location(Location(address='fakey fake double false address'))
        self.assertIsNone(unresolved)

    def test_raw_text_resolving(self):
        # text raw text resolving
        resolved = pl_outsourcing.text_to_location('425 n craig street, pittsburgh, pa')
        self.assertEquals(resolved.address,'425 N Craig St')
        self.assertEquals(resolved.postcode,'15213')
        self.assertEquals(resolved.town,'Pittsburgh')
        self.assertEquals(resolved.state,'PA')
        self.assertEquals(resolved.country,'US')

        # text resolving with seed Location
        resolved = pl_outsourcing.text_to_location('800 Penn Ave',Location(town='Pittsburgh'))
        self.assertEquals(resolved.postcode,'15221')
        resolved = pl_outsourcing.text_to_location('800 Penn Ave',Location(town='Turtle Creek'))
        self.assertEquals(resolved.postcode,'15145')

        # shouldn't resolve at all: return None
        unresolved = pl_outsourcing.text_to_location('fakey fake double false address')
        self.assertIsNone(unresolved)
        
    def test_address_normalization(self):
        in_out_pairs = (
            ('400 north craig st','400 N Craig St'),
            ('6351 walnut street apt. 5','6351 Walnut St #5'),
            ('one schenley drive','1 Schenley Dr'),
            ('fakey fake double false address',None),
        )

        for unnormal,expected in in_out_pairs:
            msg = 'normalized(%s) != %s' % (unicode(unnormal),expected)
            self.assertEquals(
                pl_outsourcing.normalize_street_address(unnormal),
                expected,
                msg=msg)
