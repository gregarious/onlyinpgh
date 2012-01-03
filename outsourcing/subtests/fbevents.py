from django.test import TestCase

from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Place
from onlyinpgh.outsourcing.models import FacebookOrgRecord, ExternalPlaceSource, FacebookEventRecord
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError
from onlyinpgh.outsourcing.fbevents import *

import random, logging
logging.disable(logging.CRITICAL)

# TODO: need tests for the event info pulling code?
class EventImportingTest(TestCase):
    fixtures = ['fbimport_test.json']
        
    def test_import(self):
        '''Tests the pulling and insertion of a batch of FB events'''
        eid_notice_pairs = [('110580932351209',None),   # 
                            ('185404598198638',None),   # 
                            ('35942576698',TypeError),  # page id 
                            ('9423481220941280',FacebookAPIError),      # bogus id
                            ('291107654260858',EventImportReport.EventInstanceExists),
            ]
        random.shuffle(eid_notice_pairs)

        # grab original FB records from any pages that already exist
        original_fb_records = {}
        for eid,notice in eid_notice_pairs:
            if notice is EventImportReport.EventInstanceExists:
                original_fb_records[eid] = FacebookEventRecord.objects.get(fb_id=eid)

        # run insertion code
        mgr = EventImportManager()
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
                    event = FacebookEventRecord.objects.get(fb_id=eid).event
                except FacebookEventRecord.DoesNotExist:
                    self.fail('No event record for fbid %s' % eid)
                if event != result.event_instance:
                    self.fail('No event created for fbid %s' % eid)
            else:
                # assert no model instance is returned
                self.assertIsNone(result.event_instance)
                # assert expected notice was generated
                self.assertEquals(len(result.notices),1)
                self.assertTrue(isinstance(result.notices[0],expected_notice),
                                'Expecting notice %s from importing fb page %s' % (str(expected_notice),eid))
                
                # if notice was a EventInstanceExists, be sure the original record wasn't touched
                if expected_notice is EventImportReport.EventInstanceExists:
                    self.assertEquals(original_fb_records[eid],
                                        FacebookEventRecord.objects.get(fb_id=eid))
                # otherwise, make sure no record was created at all
                else:
                    with self.assertRaises(FacebookEventRecord.DoesNotExist):
                        FacebookEventRecord.objects.get(fb_id=eid)
    
    def test_import_by_pages(self):
        '''Tests the importing of all events connected to a batch of pages'''
        pid_expected_pairs = [  ('244531268545',True),      # normal page - Altar Bar
                                ('45577318529',True),       # normal page - August Wilson Ctr
                                ('63893177312',True),       # normal page - Opus One
                                ('121994841144517',False),  # page that shouldn't have events
                                ('9423481220941280',False), # bogus fbid
                ]
        random.shuffle(pid_expected_pairs)

        start_filter = datetime(2012,1,1)
        # a lot of this will depend on live FB data. this test will be pretty 
        #  lightweight. Mostly just looking for unexpected failured.
        pids = [pid for pid,_ in pid_expected_pairs]
        mgr = EventImportManager()
        result_lists = mgr.import_events_from_pages(pids,start_filter=start_filter,import_owners=True)
        self.assertEquals(set(result_lists.keys()),
                            set(pids),
                            'unexpected number of EventImportReport groups returned')

        for pid,expected in pid_expected_pairs:
            result_list = result_lists[pid]
            if expected:
                for result in result_list:
                    # basic sanity tests
                    self.assertIsNotNone(result.event_instance)
                    self.assertEquals(result.notices,[])
                    # assert each event starts after the filter time
                    self.assertGreaterEqual(result.event_instance.dtstart,start_filter)
                    # test to make sure the origin page's linked Org ends up as the event host
                    page_linked_org = FacebookOrgRecord.objects.get(fb_id=pid).organization
                    event_owner = result.event_instance.role_set.get(role_name='host').organization
                    self.assertEquals(page_linked_org,event_owner)
            else:
                self.assertEquals([],result_list)

    def test_import_no_related(self):
        '''Tests the importing of a batch of FB events without permission to import related object'''
        owner_not_stored = '184248831671921'    # (org not in fixture)
        owner_stored = '143902725663363'        # (org in fixture already)

        before_orgs = list(Organization.objects.all())
        before_org_records = list(FacebookOrgRecord.objects.all())

        mgr = EventImportManager()
        results = mgr.import_events([owner_not_stored,owner_stored],
                                    import_owners=False)

        # ensure no event role was set for the first event since nothing existed without an import
        self.assertEquals(0,results[0].event_instance.role_set.count())

        # get the related host id Facebook id for the event that has a host already stored
        event_info = mgr.pull_event_info([owner_stored])[0]
        host_fbid = event_info['owner']['id']

        # ensure the existing org was found used to connect to the second event
        self.assertEquals(results[1].event_instance.role_set.get(role_name='host').organization,
                            FacebookOrgRecord.objects.get(fb_id=host_fbid).organization)

        # double check that the Place, Organization, and related link tables weren't touched
        self.assertEquals(before_orgs,list(Organization.objects.all()))
        self.assertEquals(before_org_records,list(FacebookOrgRecord.objects.all()))
