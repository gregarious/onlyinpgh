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

class FBPlacePullingTest(TestCase):
    def test_fb_place_search(self):
        '''
        Tests that place radius gathering code works
        '''
        # Dependant on FB data. Test built to search for Heinz Field and PNC Park within
        # 500 meters of a specific point.Could fail if geocoding info, building name, etc. 
        # changes in facebook data
        for batch in [True,False]:  # try both batched and unbatched requests
            page_names = [page['name'] for page in pl_outsourcing.gather_fb_place_pages((40.446,-80.014),500,batch_requests=batch)]
            self.assertIn(u'PNC Park',page_names)
            self.assertIn(u'Heinz Field',page_names)
        
        page_names = [page['name'] for page in pl_outsourcing.gather_fb_place_pages((40.446,-80.014),500,'pnc')]
        self.assertIn(u'PNC Park',page_names)
        self.assertNotIn(u'Heinz Field',page_names)

        # test that [] is returned if no pages exist
        no_pages = pl_outsourcing.gather_fb_place_pages((40.446,-80.014),500,'fiuierb2bkd7y')
        self.assertEquals(no_pages,[])

    def test_fb_page_place_pull(self):
        '''
        Tests code that batch pulls all page info.
        '''
        page_ids = ['50141015898']        # voluto coffee page
        # add 120 random ids to the list to ensure batch code is working well
        page_ids.extend([str(random.randint(1e13,1e14)) for i in range(120)])
        random.shuffle(page_ids)

        page_details = pl_outsourcing.get_full_place_pages(page_ids)

        self.assertEquals(len(page_ids),len(page_details))
        # can't really assert anything about some third party page's events. be content
        # with just testing that there's a few of them and the first one has some 
        # event-specific fields
        page = page_details[page_ids.index('50141015898')]
        self.assertIn('location',page.keys())
        self.assertIn('name',page.keys())
        
        # don't bother checking out details -- rest should be junk

class FBPlaceInsertion(TestCase):
    # TODO: recreate fixture
    # fixtures = ['events/testfb.json']

    def test_fb_place_fetch(self):
        '''
        Tests that the live-download Facebook page to place process 
        works.
        '''
        page_id = '50141015898'        # voluto coffee page
        page_count_before = Place.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(ExternalPlaceSource.DoesNotExist):
            ExternalPlaceSource.objects.get(service='fb',uid=page_id)
        
        pl_outsourcing.place_from_fb(page_id)
        
        self.assertEquals(Place.objects.count(),page_count_before+1)
        # now the FBPageRecord should exist
        try:
            ExternalPlaceSource.objects.get(service='fb',uid=page_id)
        except ExternalPlaceSource.DoesNotExist:
            self.fail('ExternalPlaceSource not found')

    def test_fb_place_insertion(self):
        '''
        Tests that all fields from a Facebook page to place are inserted 
        correctly.
        
        (uses predefined page both to test cache functionality and to ensure
        data is as expected)
        '''
        voluto_page = load_test_json('fb_page_voluto.json')

        page_count_before = Place.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(ExternalPlaceSource.DoesNotExist):
            ExternalPlaceSource.objects.get(service='fb',uid=voluto_page['id'])
        with self.assertRaises(Place.DoesNotExist):
            Place.objects.get(name=u'Voluto Coffee')
        with self.assertRaises(Organization.DoesNotExist):
            Organization.objects.get(name=u'Voluto Coffee')
        
        # add voluto's place page
        pl_outsourcing.store_fbpage_place(voluto_page)
        
        # ensure the place got added as well as the FB record linking it
        self.assertEquals(Place.objects.count(),page_count_before+1)
        try:
            place = Place.objects.get(name=u'Voluto Coffee')
        except Place.DoesNotExist:
            self.fail('Place not inserted')
        try:
            # make sure the stored FBPageRecord has the correct place set
            record = ExternalPlaceSource.objects.get(service='fb',uid=voluto_page['id'])
            self.assertEquals(record.place,place)
        except ExternalPlaceSource.DoesNotExist:
            self.fail('ExternalPlaceSource not found!')      
            
        # ensure the Voluto org entry also got created and linked up with FB
        try:
            org = Organization.objects.get(name=u'Voluto Coffee')
            self.assertEquals(place.owner,org)
        except Organization.DoesNotExist:
            self.fail('Organization not created with new Place.')

        # test various place meta properties are set correctly
        self.assertEquals('volutocoffee.com',
                            PlaceMeta.objects.get(place=place,meta_key='url').meta_value)
        self.assertEquals('412-661-3000',
                            PlaceMeta.objects.get(place=place,meta_key='phone').meta_value)
        self.assertEquals('http://profile.ak.fbcdn.net/hprofile-ak-snc4/50514_50141015898_6026239_s.jpg',
                            PlaceMeta.objects.get(place=place,meta_key='image_url').meta_value)

        # now try adding a new place but disallowing the owner to be created
        bigdog_page = load_test_json('fb_page_big_dog.json')
        org_count_before = Organization.objects.count()
        pl_outsourcing.store_fbpage_place(bigdog_page,create_owner=False)
        try:
            place = Place.objects.get(name=u'Big Dog Coffee')
        except Place.DoesNotExist:
            self.fail('Place not inserted')
        self.assertIsNone(place.owner)
        self.assertEquals(org_count_before,Organization.objects.count())

    def test_fb_existing_place_insertion(self):
        '''
        Tests that an place is not created if an existing place already exists.
        '''
        existing_page = load_test_json('fb_page_mr_smalls.json') # (already exists via fixture)
        
        page_count_before = Place.objects.count()
        record_count_before = ExternalPlaceSource.objects.count()

        pl_outsourcing.store_fbpage_place(existing_page)
        
        self.fail('need to create new fixture')
        # ensure neither a new place nor a new FB record was created
        self.assertEquals(page_count_before,Place.objects.count())
        self.assertEquals(record_count_before,ExternalPlaceSource.objects.count())

    def test_fb_bad_place_insertion(self):
        '''
        Tests that a nonexistant or user FB page insertion attempt fails gracefully.
        '''
        bogus_id = '139288502700092394'     # should be bogus
        page_count_before = Place.objects.count()
        record_count_before = ExternalPlaceSource.objects.count()

        with self.assertRaises(FacebookAPIError):
            pl_outsourcing.place_from_fb(bogus_id)

        self.assertEquals(page_count_before,Place.objects.count())
        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,ExternalPlaceSource.objects.count())
        with self.assertRaises(ExternalPlaceSource.DoesNotExist):
            ExternalPlaceSource.objects.get(service='fb',uid=bogus_id)

        placeless_page_id = '139288502700'    # pgh marathon page id (has no location)
        with self.assertRaises(TypeError):
            pl_outsourcing.place_from_fb(placeless_page_id)
        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,ExternalPlaceSource.objects.count())
        with self.assertRaises(ExternalPlaceSource.DoesNotExist):
            ExternalPlaceSource.objects.get(service='fb',uid=placeless_page_id)
