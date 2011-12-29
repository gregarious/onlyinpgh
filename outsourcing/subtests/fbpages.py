from django.test import TestCase

from onlyinpgh.identity.models import Organization
from onlyinpgh.outsourcing.models import FacebookOrgRecord, ExternalPlaceSource
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError
from onlyinpgh.outsourcing.fbpages import *

import random, logging
logging.disable(logging.CRITICAL)

class OrgImportingTest(TestCase):
    fixtures = ['fbimport_test.json']

    def test_import(self):
        '''Tests the importing of a batch of FB pages as Orgs'''
        mgr = FBPageManager()
        pid_notice_pairs = [('30273572778',None),   # Mr. Smalls
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
        # run insertion code
        results = mgr.import_orgs([pair[0] for pair in pid_notice_pairs])
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
        
class PlaceImportingTest(TestCase):
    fixtures = ['fbimport_test.json']
        
    def test_import(self):
        '''Tests the importing of a batch of FB pages as Places'''
        mgr = FBPageManager()
        pid_notice_pairs = [('30273572778',None),   # Mr. Smalls
                             ('139288502700',TypeError),  # Pgh Marathon (no location)
                             ('291107654260858',TypeError),  # event page
                             ('9423481220941280',FacebookAPIError),  # bogus id
                             ('53379078585',PageImportReport.ModelInstanceExists),
            ]
        random.shuffle(pid_notice_pairs)

        # grab original FB records from any pages that already exist
        original_fb_records = {}
        for pid,notice in pid_notice_pairs:
            if notice is PageImportReport.ModelInstanceExists:
                original_fb_records[pid] = ExternalPlaceSource.facebook.get(uid=pid)

        # run insertion code
        results = mgr.import_places([pair[0] for pair in pid_notice_pairs])
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
        no_owner_stored = '30273572778'   # mr. smalls (org and place not in fixture)
        owner_stored = '50141015898'      # voluto coffee (org in fixture but not place)

        before_orgs = list(Organization.objects.all())
        before_records = list(FacebookOrgRecord.objects.all())

        mgr = FBPageManager()
        results = mgr.import_places([no_owner_stored,owner_stored],import_owners=False)

        # ensure no org was created for the first page
        self.assertIsNone(results[0].model_instance.owner)
        # ensure the existing org was found for the second page, even without import
        self.assertIsNotNone(results[1].model_instance)
        self.assertEquals(results[1].model_instance.owner,
                            FacebookOrgRecord.objects.get(fb_id=owner_stored).organization)

        # double check that the Organization and FacebookOrgRecord tables weren't touched
        self.assertEquals(before_orgs,list(Organization.objects.all()))
        self.assertEquals(before_records,list(FacebookOrgRecord.objects.all()))