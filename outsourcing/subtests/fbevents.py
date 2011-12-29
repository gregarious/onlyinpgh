from django.test import TestCase

from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Place
from onlyinpgh.outsourcing.models import FacebookOrgRecord, ExternalPlaceSource, FacebookEventRecord
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError
from onlyinpgh.outsourcing.fbevents import *

import random, logging
logging.disable(logging.CRITICAL)

class EventImportingTest(TestCase):
    fixtures = ['fbimport_test.json']
        
    def test_import(self):
        '''Tests the pulling and insertion of a batch of FB pages as Places'''
        eid_notice_pairs = [('',None),   # 
                            ('',None),   # 
                            ('',TypeError),         # 
                            ('',FacebookAPIError),  # bogus id
                            ('',EventImportReport.EventInstanceExists),
            ]
        random.shuffle(eid_notice_pairs)

        # grab original FB records from any pages that already exist
        original_fb_records = {}
        for eid,notice in eid_notice_pairs:
            if isinstance(notice,EventImportReport.EventInstanceExists):
                original_fb_records[eid] = FacebookEventRecord.objects.get(fb_id=eid)

        # run insertion code
        mgr = FBEventManager()
        results = mgr.import_events([pair[0] for pair in eid_notice_pairs])
        self.assertEquals([result.fbevent_id for result in results],
                          [eid for eid,_ in eid_notice_pairs],
                          'non-parallel list of EventImportReports returned')

        for pair,result in zip(eid_notice_pairs,results):
            eid,expected_notice = pair
            if not expected_notice:
                self.assertEquals([],result.notices)
                # assert a new model instance was created and it's FB record matches what was returned
                try:
                    event = FacebookEventRecord.objects.get(fb_id=eid)
                except FacebookEventRecord.DoesNotExist:
                    self.fail('No event record for fbid %s' % eid)
                if event != result.model_instance:
                    self.fail('No event created for fbid %s' % eid)
            else:
                # assert no model instance is returned
                self.assertIsNone(result.model_instance)
                # assert expected notice was generated
                self.assertEquals(len(result.notices),1)
                self.assertTrue(isinstance(result.notices[0],expected_notice),
                                'Expecting notice %s from importing fb page %s' % (str(expected_notice),eid))
                
                # if notice was a EventInstanceExists, be sure the original record wasn't touched
                if isinstance(expected_notice,EventImportReport.EventInstanceExists):
                    self.assertEquals(original_fb_records[eid],
                                        FacebookEventRecord.objects.get(fb_id=eid))
                # otherwise, make sure no record was created at all
                else:
                    with self.assertRaises(FacebookEventRecord.DoesNotExist):
                        FacebookEventRecord.objects.get(fb_id=eid)
    
    def test_import_by_pages(self):
        '''Tests the importing of all events connected to a batch of pages'''
        pids = ['','','','']
        # a lot of this will depend on live FB data. this test will be pretty 
        #  lightweight. Mostly just looking for unexpected failured.
        mgr = FBEventManager()
        result_sets = mgr.import_events_from_pages(pids,import_related=True)
        self.assertEquals(set(result_sets.keys()),set(pids),
                          'unexpected number of EventImportReport groups returned')

        for pid,result_set in result_sets.items():
            for result in result_set:
                # basic sanity tests
                self.assertIsNotNone(result.event_instance)
                self.assertEquals(result.notices,[])
                self.assertEquals(result.referrer_id,pid)
                # test to make sure the origin page's linked Org ends up as the event host
                page_linked_org = FacebookOrgRecord.objects.get(fb_id=pid)
                event_owner = result.event_instance.role_set.get(role_name='host')
                self.assertEquals(page_linked_org,event_owner)

    def test_import_no_related(self):
        '''Tests the importing of a batch of FB events without permission to import related object.'''
        related_objects_not_stored = '' # (org and place not in fixture)
        related_objects_stored = ''     # (org and place in fixture already)

        before_orgs = list(Organization.objects.all())
        before_org_records = list(FacebookOrgRecord.objects.all())
        before_places = list(Place.objects.all())
        before_place_records = list(ExternalPlaceSource.objects.all())

        mgr = FBEventManager()
        results = mgr.import_events([related_objects_not_stored,related_objects_stored],
                                    import_related=False)

        # ensure no org/place was set for the first event since nothing existed without an import
        self.assertIsNone(results[0].model_instance.owner)
        self.assertIsNone(results[0].model_instance.place)

        # get the related host and place Facebook ids for the test pair of tests
        event_info = mgr.pull_event_info(related_objects_stored)[0]
        host_fbid = event_info['owner']['id']
        place_fbid = event_info['location']['id']

        # ensure the existing org/place was found used to connect to the second event
        self.assertEquals(results[1].model_instance.role_set(role_name='host'),
                            FacebookOrgRecord.objects.get(fb_id=host_fbid).organization)
        self.assertEquals(results[1].model_instance.place,
                            ExternalPlaceSource.facebook.get(uid=place_fbid).place)

        # double check that the Place, Organization, and related link tables weren't touched
        self.assertEquals(before_orgs,list(Organization.objects.all()))
        self.assertEquals(before_org_records,list(FacebookOrgRecord.objects.all()))
        self.assertEquals(before_places,list(Place.objects.all()))
        self.assertEquals(before_place_records,list(ExternalPlaceSource.objects.all()))