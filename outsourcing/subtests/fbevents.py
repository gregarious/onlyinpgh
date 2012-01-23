from django.test import TestCase

from onlyinpgh.identity.models import Organization
from onlyinpgh.places.models import Place
from onlyinpgh.events.models import Event
from onlyinpgh.outsourcing.models import FacebookOrgRecord, ExternalPlaceSource, FacebookEventRecord

from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError
from onlyinpgh.outsourcing.fbevents import store_fbevent, EventImportManager, EventImportReport

from onlyinpgh.outsourcing.subtests import load_test_json

import random, logging
from datetime import datetime
logging.disable(logging.CRITICAL)

class EventStorageTest(TestCase):
    '''
    Collection of tests for outsoucing.fbevents.store_fbevent using fixed json data.
    '''
    fixtures = ['fbimport_test.json']

    def test_new_event(self):
        '''
        Tests that all fields from a Facebook page to event are inserted 
        correctly.
        '''
        event_fbid = '286153888063194'        # Oxford 5k
        event_info = load_test_json('fb_event_oxford_5k.json')
        event_count_before = Event.objects.count()

        # ensure no FBPageRecord already exists for the given id
        with self.assertRaises(FacebookEventRecord.DoesNotExist):
            FacebookEventRecord.objects.get(fb_id=event_fbid)

        store_fbevent(event_info,create_owners=False)
        
        self.assertEquals(Event.objects.count(),event_count_before+1)
        try:
            event = Event.objects.get(name=u'Oxford Athletic Club Freaky 5K')
        except Event.DoesNotExist:
            self.fail('Event not inserted')

        try:
            # make ensure the stored FBEventRecord has the correct Event set
            record = FacebookEventRecord.objects.get(fb_id=event_fbid)
            self.assertEquals(record.event,event)
            # ensure the last updated time was set correctly on the event record
            self.assertEquals(record.last_updated,datetime(2011,9,23,18,27,48))
        except Event.DoesNotExist:
            self.fail('FacebookEventRecord not found!')            

        # check properties of event were stored correctly (see http://graph.facebook.com/291107654260858)
        # event goes from 10/29/11 13:30 16:30 (UTC time)
        self.assertEquals(event.dtstart,datetime(2011,10,29,13,30))
        self.assertEquals(event.dtend,datetime(2011,10,29,16,30))
        self.assertTrue(event.description.startswith(u'Join the Steel City Road Runners Club'))

    def test_existing_event(self):
        '''
        Tests that an event is not created if an existing event already exists.
        '''
        event_fbid = '291107654260858'         # mr. smalls event (already exists via fixture)
        event_info = load_test_json('fb_event_mr_smalls.json')
        event_count_before = Event.objects.count()
        record_count_before = FacebookEventRecord.objects.count()

        store_fbevent(event_info,create_owners=False)
        self.assertEquals(event_count_before,Event.objects.count())

        # ensure the Facebook record didn't get saved
        self.assertEquals(record_count_before,FacebookEventRecord.objects.count())

class EventImportingTest(TestCase):
    '''
    Collection of tests for outsourcing.fbevents.EventImportReport
    '''
    fixtures = ['fbimport_test.json']

    def test_pulling(self):
        '''
        Tests pulling of a batch of FB events -- not Event model saving
        '''
        event_ids = ['159484480801269',  # valid event page
                     '828371892334123']  # invalid fbid
        # add 100 random ids to the list to ensure batch code is working well
        event_ids.extend([str(random.randint(1,1e13)) for i in range(100)])

        mgr = EventImportManager()
        fbevents = mgr.pull_event_info(event_ids)
        self.assertEquals(len(fbevents),len(event_ids))

        valid_event = fbevents[0]
        self.assertIn('start_time',valid_event.keys())
        self.assertIn('owner',valid_event.keys())

        invalid_event = fbevents[1]
        self.assertTrue(isinstance(invalid_event,FacebookAPIError))

    def test_pulling_from_pages(self):
        '''
        Tests pulling of a batch of FB events by pages -- not Event model saving
        '''
        page_ids = ['40796308305',      # coca-cola's UID
                    '121994841144517',  # place that will probably never have any events
                    '828371892334123']  # invalid fbid
        # add 100 random ids to the list to ensure batch code is working well
        page_ids.extend([str(random.randint(1e13,1e14)) for i in range(100)])
        random.shuffle(page_ids)

        mgr = EventImportManager()
        pid_infos_map = mgr.pull_event_info_from_pages(page_ids)
        self.assertEquals(set(pid_infos_map.keys()),set(page_ids))

        # can't really assert anything about some third party page's events. be content
        # with just testing that there's a few of them and the first one has some 
        # event-specific fields
        events = pid_infos_map['40796308305']
        self.assertGreater(len(events),4)       # should be more than 4? why not.

        # some of the queries will randomly fail. trim these out and ensure less 
        # than 25% of the respopnses are failures
        failures = [ev for ev in events if isinstance(ev,FacebookAPIError)]
        if len(failures) > .25*len(events):
            self.fail('Unexpected large number of failed event pulls (%d of %d).' % (len(failures),len(events)))
        
        for event in events:
            if event not in failures:
                self.assertIn('start_time',event.keys())
                self.assertIn('owner',event.keys())

        # this one should return an empty list
        self.assertEquals(pid_infos_map['121994841144517'],[])
        self.assertEquals(pid_infos_map['828371892334123'],[])

        # ignore the rest of the requests -- they were just to test batch
    
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
        eids = [pair[0] for pair in eid_notice_pairs]
        mgr.pull_event_info(eids)
        results = [mgr.import_event(eid) for eid in eids]
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
        mgr.pull_event_info_from_pages(pids)
        result_lists = [mgr.import_events_from_page(pid,start_filter=start_filter,import_owners=True)
                            for pid in pids]
        self.assertEquals(len(result_lists),len(pids),
                            'unexpected number of EventImportReport groups returned')

        for pid_exp_pair,result_list in zip(pid_expected_pairs,result_lists):
            pid,expected = pid_exp_pair
            if expected:
                for result in result_list:
                    # basic sanity tests
                    self.assertIsNotNone(result.event_instance)
                    self.assertEquals(result.notices,[])
                    # assert each event starts after the filter time
                    self.assertGreaterEqual(result.event_instance.dtstart,start_filter)
                    # test to make sure the origin page's linked Org ends up as the event host
                    page_linked_org = FacebookOrgRecord.objects.get(fb_id=pid).organization
                    event_owner = result.event_instance.role_set.get(role_type='host').organization
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
        
        # ensure no event role is set since nothing existed without an import
        result = mgr.import_event(owner_not_stored,import_owners=False)
        self.assertEquals(0,result.event_instance.role_set.count())

        # get the related host id Facebook id for the event that has a host already stored
        event_info = mgr.pull_event_info([owner_stored])[0]
        host_fbid = event_info['owner']['id']

        # ensure the existing org was found used to connect to the second event
        result = mgr.import_event(owner_stored,import_owners=False)
        self.assertEquals(result.event_instance.role_set.get(role_type='host').organization,
                            FacebookOrgRecord.objects.get(fb_id=host_fbid).organization)

        # double check that the Place, Organization, and related link tables weren't touched
        self.assertEquals(before_orgs,list(Organization.objects.all()))
        self.assertEquals(before_org_records,list(FacebookOrgRecord.objects.all()))
