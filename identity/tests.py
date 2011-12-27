from django.test import TestCase

from onlyinpgh.utils.testing import load_test_json
from onlyinpgh.identity.outsourcing import page_id_to_organization
from onlyinpgh.identity.models import *

from onlyinpgh.places.models import FacebookPageRecord

import logging
logging.disable(logging.CRITICAL)

class FBOrganizationInsertion(TestCase):
    fixtures = ['events/testfb.json']

    def test_fb_new_org_live(self):
        '''
        Tests that the live-download Facebook page to organization process 
        works.
        '''
        page_id = '139288502700'        # pgh marathon page
        org_count_before = Organization.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(FacebookPageRecord.DoesNotExist):
            FacebookPageRecord.objects.get(fb_id=page_id)
        
        page_id_to_organization(page_id)
        
        self.assertEquals(Organization.objects.count(),org_count_before+1)
        # now the FBPageRecord should exist
        try:
            FacebookPageRecord.objects.get(fb_id=page_id)
        except FacebookPageRecord.DoesNotExist:
            self.fail('FacebookPageRecord not found')

    def test_fb_new_org(self):
        '''
        Tests that all fields from a Facebook page to org are inserted 
        correctly.
        
        (uses predefined page both to test cache functionality and to ensure
        data is as expected)
        '''
        page_id = '139288502700'        # pgh marathon page
        page_cache = {page_id: load_test_json('identity','pgh_marathon_page.json')}
        org_count_before = Organization.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(FacebookPageRecord.DoesNotExist):
            FacebookPageRecord.objects.get(fb_id=page_id)
        with self.assertRaises(Organization.DoesNotExist):
            Organization.objects.get(name=u'Dick\'s Sporting Goods Pittsburgh Marathon')

        page_id_to_organization(page_id,page_cache=page_cache)
        
        self.assertEquals(Organization.objects.count(),org_count_before+1)
        try:
            org = Organization.objects.get(name=u'Dick\'s Sporting Goods Pittsburgh Marathon')
        except Organization.DoesNotExist:
            self.fail('Organization not inserted')

        try:
            # make sure the stored FBPageRecord has the correct organization set
            org_on_record = FacebookPageRecord.objects.get(fb_id=page_id).organization
            self.assertEquals(org_on_record,org)
        except FacebookPageRecord.DoesNotExist:
            self.fail('FacebookPageRecord not found!')            
        self.assertEquals(org.avatar,'http://profile.ak.fbcdn.net/hprofile-ak-snc4/41606_139288502700_4851430_s.jpg')

    def test_fb_existing_org(self):
        '''
        Tests that an org is not created if an existing org already exists.
        '''
        page_id = '30273572778'         # mr. smalls page (already exists via fixture)
        page_cache = {page_id: load_test_json('identity','mr_smalls_page.json')}
        org_count_before = Organization.objects.count()
        record_count_before = FacebookPageRecord.objects.count()

        page_id_to_organization(page_id,page_cache=page_cache)
        # assert some 'already exists' error is raised
        self.fail('not yet implemented')
        self.assertEquals(org_count_before,Organization.objects.count())

        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookPageRecord.objects.count())

    def test_fb_bad_org(self):
        '''
        Tests that a nonexistant or user FB page insertion attempt fails gracefully.
        '''
        bogus_id = '139288502700092394'     # should be bogus
        org_count_before = Organization.objects.count()
        record_count_before = FacebookPageRecord.objects.count()

        with self.assertRaises(FacebookAPIError):
            page_id_to_organization(bogus_id)
    
        # assert some facebook error is raised
        self.assertEquals(org_count_before,Organization.objects.count())
        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookPageRecord.objects.count())
        with self.assertRaises(FacebookPageRecord.DoesNotExist):
            FacebookPageRecord.objects.get(fb_id=bogus_id)
            
        user_id = '14205248'    # my facebook id
        # TODO: ensure user pages don't get inserted
        with self.assertRaises(FacebookAPIError):
            page_id_to_organization(user_id)
        # assert some 'non org page' error is raised
        self.fail('not yet implemented')
        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookPageRecord.objects.count())
        with self.assertRaises(FacebookPageRecord.DoesNotExist):
            FacebookPageRecord.objects.get(fb_id=user_id)
