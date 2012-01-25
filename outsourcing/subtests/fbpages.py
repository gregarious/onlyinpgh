from django.test import TestCase

from onlyinpgh.outsourcing.fbpages import PageImportManager, PageImportReport
from onlyinpgh.outsourcing.fbpages import store_fbpage_organization, store_fbpage_place

from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Place, Meta as PlaceMeta
from onlyinpgh.outsourcing.models import FacebookOrgRecord, ExternalPlaceSource
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError

from onlyinpgh.outsourcing.subtests import load_test_json

import random, logging
logging.disable(logging.CRITICAL)

class PagePullingTest(TestCase):
    def test_pulling(self):
        '''
        Tests internal FB page info gathering code -- not model importing.
        '''
        page_ids = ['84714961156',      # Square Cafe
                    '9423481220941280'] # invalid fbid
        # add 100 random ids to the list to ensure batch code is working well
        page_ids.extend([str(random.randint(1,1e12)) for i in range(100)])

        mgr = PageImportManager()
        page_infos = mgr.pull_page_info(page_ids)
        
        self.assertEquals(len(page_infos),len(page_ids))

        # can't really assert anything about some third party pages. be content
        # with just testing that there's a few of them and the first one has some 
        # page-specific fields
        valid_info = page_infos[0]
        self.assertIn('name',valid_info.keys())
        self.assertIn('location',valid_info.keys()) # this is a Place page

        # the bogus id shouldn't be cached
        invalid_info = page_infos[1]
        self.assertTrue(isinstance(invalid_info,FacebookAPIError))

        # ignore the rest of the requests -- they were just to test batch

class OrgStorageTest(TestCase):
    '''
    Collection of tests for outsoucing.fbpages.store_fbpage_organization using fixed json data.
    '''
    fixtures = ['fbimport_test.json']

    def test_fb_org_insertion(self):
        '''
        Tests that all fields from a Facebook page to org are inserted 
        correctly.
        
        (uses predefined page both to test cache functionality and to ensure
        data is as expected)
        '''
        page_info = load_test_json('fb_page_pgh_marathon.json') # pgh marathon page
        page_id = page_info['id']

        org_count_before = Organization.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(FacebookOrgRecord.DoesNotExist):
            FacebookOrgRecord.objects.get(fb_id=page_id)
        with self.assertRaises(Organization.DoesNotExist):
            Organization.objects.get(name=u'Dick\'s Sporting Goods Pittsburgh Marathon')

        store_fbpage_organization(page_info)
        
        self.assertEquals(Organization.objects.count(),org_count_before+1)
        try:
            org = Organization.objects.get(name=u'Dick\'s Sporting Goods Pittsburgh Marathon')
        except Organization.DoesNotExist:
            self.fail('Organization not inserted')

        try:
            # make sure the stored FBPageRecord has the correct organization set
            org_on_record = FacebookOrgRecord.objects.get(fb_id=page_id).organization
            self.assertEquals(org_on_record,org)
        except FacebookOrgRecord.DoesNotExist:
            self.fail('FacebookOrgRecord not found!')            
        self.assertEquals(org.avatar,'http://profile.ak.fbcdn.net/hprofile-ak-snc4/41606_139288502700_4851430_s.jpg')

    def test_fb_existing_org_insertion(self):
        '''
        Tests that an org is not created if an existing org already exists.
        '''
        page_info = load_test_json('fb_page_mr_smalls.json') 

        org_count_before = Organization.objects.count()
        record_count_before = FacebookOrgRecord.objects.count()

        store_fbpage_organization(page_info)

        # ensure neither a new organization nor a new FB record was created
        self.assertEquals(org_count_before,Organization.objects.count())
        self.assertEquals(record_count_before,FacebookOrgRecord.objects.count())

class OrgImportingTest(TestCase):
    fixtures = ['fbimport_test.json']

    def test_import(self):
        '''Tests the importing of a batch of FB pages as Orgs'''
        mgr = PageImportManager()
        pid_notice_pairs = [('84714961156',None),   # Square Cafe
                            ('139288502700',None),  # Pgh Marathon
                            ('220439',TypeError),   # user page
                            ('291107654260858',TypeError),  # event page
                            ('9423481220941280',FacebookAPIError),  # bogus id
                            ('53379078585',PageImportReport.ModelInstanceExists),
            ]
        random.shuffle(pid_notice_pairs)

        # grab original FB records from any pages that already exist
        original_fb_records = {}
        for pid,notice in pid_notice_pairs:
            if notice is PageImportReport.ModelInstanceExists:
                original_fb_records[pid] = FacebookOrgRecord.objects.get(fb_id=pid)
        pids = [pair[0] for pair in pid_notice_pairs]

        # run insertion code
        mgr.pull_page_info(pids)    # cache pages
        results = [mgr.import_org(pid) for pid in pids]
        self.assertEquals([result.page_id for result in results],
                  [pid for pid,_ in pid_notice_pairs],
                  'non-parallel list of PageImportReports returned')

        for pair,result in zip(pid_notice_pairs,results):
            pid,expected_notice = pair
            if not expected_notice:
                self.assertEquals([],result.notices)
                # assert a new model instance was created and it's FB record matches what was returned
                try:
                    org = FacebookOrgRecord.objects.get(fb_id=pid).organization
                except FacebookOrgRecord.DoesNotExist:
                    self.fail('No organization record for fbid %s' % pid)
                if org != result.model_instance:
                    self.fail('No organization created for fbid %s' % pid)
            else:
                # assert no model instance is returned
                self.assertIsNone(result.model_instance)
                # assert expected notice was generated
                self.assertEquals(len(result.notices),1)
                self.assertTrue(isinstance(result.notices[0],expected_notice),
                                'Expecting notice %s from importing fb page %s' % (str(expected_notice),pid))
                
                # if notice was a ModelInstanceExists, be sure the original record wasn't touched
                if expected_notice is PageImportReport.ModelInstanceExists:
                    self.assertEquals(original_fb_records[pid],
                                        FacebookOrgRecord.objects.get(fb_id=pid))
                # otherwise, make sure no record was created at all
                else:
                    with self.assertRaises(FacebookOrgRecord.DoesNotExist):
                        FacebookOrgRecord.objects.get(fb_id=pid)

class PlaceStorageTest(TestCase):
    '''
    Collection of tests for outsoucing.fbpages.store_fbpage_organization using fixed json data.
    '''
    fixtures = ['fbimport_test.json']

    def test_fb_place_insertion(self):
        '''
        Tests that all fields from a Facebook page to place are inserted 
        correctly.
        '''
        voluto_page = load_test_json('fb_page_square_cafe.json')

        page_count_before = Place.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(ExternalPlaceSource.DoesNotExist):
            ExternalPlaceSource.facebook.get(uid=voluto_page['id'])
        with self.assertRaises(Place.DoesNotExist):
            Place.objects.get(name=u'Square Cafe')
        with self.assertRaises(Organization.DoesNotExist):
            Organization.objects.get(name=u'Square Cafe')
        
        # add voluto's place page
        store_fbpage_place(voluto_page)
        
        # ensure the place got added as well as the FB record linking it
        self.assertEquals(Place.objects.count(),page_count_before+1)
        try:
            place = Place.objects.get(name=u'Square Cafe')
        except Place.DoesNotExist:
            self.fail('Place not inserted')
        try:
            # make sure the stored FBPageRecord has the correct place set
            record = ExternalPlaceSource.facebook.get(uid=voluto_page['id'])
            self.assertEquals(record.place,place)
        except ExternalPlaceSource.DoesNotExist:
            self.fail('ExternalPlaceSource not found!')      
            
        # ensure the Voluto org entry also got created and linked up with FB
        try:
            org = Organization.objects.get(name=u'Square Cafe')
            self.assertEquals(place.owner,org)
        except Organization.DoesNotExist:
            self.fail('Organization not created with new Place.')

        # test various place meta properties are set correctly
        self.assertEquals('http://www.square-cafe.com',
                            PlaceMeta.objects.get(place=place,meta_key='url').meta_value)
        self.assertEquals('412.244.8002',
                            PlaceMeta.objects.get(place=place,meta_key='phone').meta_value)
        self.assertEquals('http://profile.ak.fbcdn.net/hprofile-ak-snc4/261082_84714961156_1722971382_s.jpg',
                            PlaceMeta.objects.get(place=place,meta_key='image_url').meta_value)

        # now try adding a new place but disallowing the owner to be created
        bigdog_page = load_test_json('fb_page_library.json')

        org_count_before = Organization.objects.count()
        store_fbpage_place(bigdog_page,create_owner=False)
        try:
            place = Place.objects.get(name=u'The Library')
        except Place.DoesNotExist:
            self.fail('Place not inserted')
        self.assertIsNone(place.owner)
        self.assertEquals(org_count_before,Organization.objects.count())

    def test_fb_existing_place_insertion(self):
        '''
        Tests that an place is not created if an existing place already exists.
        '''
        existing_page = load_test_json('fb_page_big_dog.json') # (already exists via fixture)
        
        page_count_before = Place.objects.count()
        record_count_before = ExternalPlaceSource.objects.count()

        store_fbpage_place(existing_page)
        
        # ensure neither a new place nor a new FB record was created
        self.assertEquals(page_count_before,Place.objects.count())
        self.assertEquals(record_count_before,ExternalPlaceSource.objects.count())

class PlaceImportingTest(TestCase):
    fixtures = ['fbimport_test.json']
        
    def test_import(self):
        '''Tests the importing of a batch of FB pages as Places'''
        mgr = PageImportManager()
        pid_notice_pairs = [('84714961156',None),   # Square Cafe
                             ('139288502700',TypeError),  # Pgh Marathon (no location)
                             ('291107654260858',TypeError),  # event page
                             ('9423481220941280',FacebookAPIError),  # bogus id
                             ('53379078585',PageImportReport.ModelInstanceExists),  # big dog
            ]
        random.shuffle(pid_notice_pairs)

        # grab original FB records from any pages that already exist
        original_fb_records = {}
        for pid,notice in pid_notice_pairs:
            if notice is PageImportReport.ModelInstanceExists:
                original_fb_records[pid] = ExternalPlaceSource.facebook.get(uid=pid)
        pids = [pair[0] for pair in pid_notice_pairs]

        # run insertion code
        mgr.pull_page_info(pids)    # cache pages
        results = [mgr.import_place(pid) for pid in pids]
        self.assertEquals([result.page_id for result in results],
                          [pid for pid,_ in pid_notice_pairs],
                          'non-parallel list of PageImportReports returned')

        for pair,result in zip(pid_notice_pairs,results):
            pid,expected_notice = pair
            if not expected_notice:
                self.assertEquals([],result.notices)
                # assert a new model instance was created and it's FB record matches what was returned
                try:
                    place = ExternalPlaceSource.facebook.get(uid=pid).place
                except ExternalPlaceSource.DoesNotExist:
                    self.fail('No place record for fbid %s' % pid)
                if place != result.model_instance:
                    self.fail('No place created for fbid %s' % pid)
            else:
                # assert no model instance is returned
                self.assertIsNone(result.model_instance)
                # assert expected notice was generated
                self.assertEquals(len(result.notices),1)
                self.assertTrue(isinstance(result.notices[0],expected_notice),
                                'Expecting notice %s from importing fb page %s' % (str(expected_notice),pid))
                
                # if notice was a ModelInstanceExists, be sure the original record wasn't touched
                if expected_notice is PageImportReport.ModelInstanceExists:
                    self.assertEquals(original_fb_records[pid],
                                        ExternalPlaceSource.facebook.get(uid=pid))
                # otherwise, make sure no record was created at all
                else:
                    with self.assertRaises(ExternalPlaceSource.DoesNotExist):
                        ExternalPlaceSource.facebook.get(uid=pid)
        
    def test_import_no_owner(self):
        '''Tests the importing of a batch of FB pages as Places without owner importing disabled.'''
        no_owner_stored = '84714961156'   # sqaure cafe (org and place not in fixture)
        owner_stored = '50141015898'      # voluto coffee (org in fixture but not place)

        before_orgs = list(Organization.objects.all())
        before_records = list(FacebookOrgRecord.objects.all())

        mgr = PageImportManager()

        # ensure no org is created 
        result = mgr.import_place(no_owner_stored,import_owners=False)
        self.assertIsNone(result.model_instance.owner)

        # ensure the existing org is found, even without import
        result = mgr.import_place(owner_stored,import_owners=False)
        self.assertIsNotNone(result.model_instance)
        self.assertEquals(result.model_instance.owner,
                            FacebookOrgRecord.objects.get(fb_id=owner_stored).organization)

        # double check that the Organization and FacebookOrgRecord tables weren't touched
        self.assertEquals(before_orgs,list(Organization.objects.all()))
        self.assertEquals(before_records,list(FacebookOrgRecord.objects.all()))