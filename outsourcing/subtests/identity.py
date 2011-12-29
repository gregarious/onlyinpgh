from django.test import TestCase
from onlyinpgh.outsourcing.subtests import load_test_json
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError

from onlyinpgh.outsourcing.models import FacebookOrgRecord
from onlyinpgh.identity.models import Organization

from onlyinpgh.outsourcing import identity as id_outsourcing

'''
Tests related to code in onlyinpgh.outsourcing.identity
'''
class FBOrganizationInsertion(TestCase):
    # TODO: need to recreate fixture
    #fixtures = ['testfb.json']
    def test_fb_org_fetch(self):
        '''
        Tests that the live-download Facebook page to organization process 
        works.
        '''
        page_id = '139288502700'        # pgh marathon page
        org_count_before = Organization.objects.count()
        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(FacebookOrgRecord.DoesNotExist):
            FacebookOrgRecord.objects.get(page_fbid=page_id)
        
        id_outsourcing.org_from_fb(page_id)
        
        self.assertEquals(Organization.objects.count(),org_count_before+1)
        # now the FBPageRecord should exist
        try:
            FacebookOrgRecord.objects.get(page_fbid=page_id)
        except FacebookOrgRecord.DoesNotExist:
            self.fail('FacebookOrgRecord not found')

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
            FacebookOrgRecord.objects.get(page_fbid=page_id)
        with self.assertRaises(Organization.DoesNotExist):
            Organization.objects.get(name=u'Dick\'s Sporting Goods Pittsburgh Marathon')

        id_outsourcing.store_fbpage_organization(page_info)
        
        self.assertEquals(Organization.objects.count(),org_count_before+1)
        try:
            org = Organization.objects.get(name=u'Dick\'s Sporting Goods Pittsburgh Marathon')
        except Organization.DoesNotExist:
            self.fail('Organization not inserted')

        try:
            # make sure the stored FBPageRecord has the correct organization set
            org_on_record = FacebookOrgRecord.objects.get(page_fbid=page_id).organization
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

        id_outsourcing.store_fbpage_organization(page_info)

        self.fail('need to create new fixture')        
        # ensure neither a new organization nor a new FB record was created
        self.assertEquals(org_count_before,Organization.objects.count())
        self.assertEquals(record_count_before,FacebookOrgRecord.objects.count())

    def test_fb_bad_org_insertion(self):
        '''
        Tests that a nonexistant or user FB page insertion attempt fails gracefully.
        '''
        bogus_id = '139288502700092394'     # should be bogus
        org_count_before = Organization.objects.count()
        record_count_before = FacebookOrgRecord.objects.count()

        # assert nonexistant page raises error
        with self.assertRaises(FacebookAPIError):
            id_outsourcing.org_from_fb(bogus_id)
    
        self.assertEquals(org_count_before,Organization.objects.count())
        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookOrgRecord.objects.count())
        with self.assertRaises(FacebookOrgRecord.DoesNotExist):
            FacebookOrgRecord.objects.get(page_fbid=bogus_id)
            
        # now try to insert a user page
        user_id = '14205248'    # my facebook id
        
        # assert TypeError is raised 
        with self.assertRaises(TypeError):
            id_outsourcing.org_from_fb(user_id)
        
        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookOrgRecord.objects.count())
        with self.assertRaises(FacebookOrgRecord.DoesNotExist):
            FacebookOrgRecord.objects.get(page_fbid=user_id)
