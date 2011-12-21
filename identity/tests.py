from django.test import TestCase

from onlyinpgh.utils.testing import load_test_json
from onlyinpgh.identity.outsourcing import page_id_to_organization
from onlyinpgh.identity.models import *

import logging
logging.disable(logging.CRITICAL)

class FBOrganizationInsertion(TestCase):
    fixtures = ['events/testfb.json']

    def test_fb_new_org_live(self):
        '''
        Tests that the live-download Facebook page to organization process 
        works.
        '''
        before_count = Organization.objects.count()
        page_id_to_organization('139288502700')
        self.assertEquals(Organization.objects.count(),before_count+1)

    def test_fb_new_org_detail(self):
        '''
        Tests that all fields from a Facebook page to org are inserted 
        correctly.
        
        (uses predefined page both to test cache functionality and to ensure
        data is as expected)
        '''
        page_cache = {'139288502700': load_test_json('places','pgh_marathon_page.json')}
        before_count = Organization.objects.count()
        page_id_to_organization('139288502700',page_cache=page_cache)
        
        self.assertEquals(Organization.objects.count(),before_count+1)
        try:
            org = Organization.objects.get(name=u'Dick\'s Sporting Goods Pittsburgh Marathon')
        except Organization.DoesNotExist:
            self.fail('Organization not inserted')
        self.assertEquals(org.avatar,'http://profile.ak.fbcdn.net/hprofile-ak-snc4/41606_139288502700_4851430_s.jpg')

    def test_fb_existing_org(self):
        '''
        Tests that an org is not created if an existing org already exists.
        '''
        page_cache = {'30273572778': load_test_json('places','mr_smalls_page.json')}
        before_count = Organization.objects.count()
        page_id_to_organization('30273572778',page_cache=page_cache)
        # assert some 'already exists' error is raised
        self.fail('not yet implemented')
        self.assertEquals(before_count,Organization.objects.count())

    def test_fb_bad_org(self):
        '''
        Tests that a nonexistant or user FB page insertion attempt fails gracefully.
        '''
        before_count = Organization.objects.count()
        page_id_to_organization('139288502700092394')   # should be bogus
        self.fail('not yet implemented')
        # assert some facebook error is raised
        self.assertEquals(before_count,Organization.objects.count())

        # TODO: ensure user pages don't get inserted
        page_id_to_organization('14205248')   # my facebook id
        # assert some 'non org page' error is raised
        self.fail('not yet implemented')