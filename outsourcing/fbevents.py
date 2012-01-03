from django.db import transaction

from onlyinpgh.outsourcing.apitools import facebook
from onlyinpgh.outsourcing.apitools.facebook import FacebookAPIError

from onlyinpgh.outsourcing import fbpages
from onlyinpgh.events import categorize

from onlyinpgh.places.models import Place, Location
from onlyinpgh.events.models import Event, Role
from onlyinpgh.identity.models import Organization
from onlyinpgh.outsourcing.models import FacebookEventRecord, FacebookOrgRecord, ExternalPlaceSource

from onlyinpgh.outsourcing.places import resolve_place, resolve_location

from onlyinpgh.utils.time import localtoutc

from itertools import chain
from datetime import datetime

import json, copy, logging, pytz

outsourcing_log = logging.getLogger('onlyinpgh.outsourcing')

EST = pytz.timezone('US/Eastern')

# TODO: should be in apitools.faceboob somewhere
def _run_batch(batch):
    batch_response = facebook.oip_client.run_batch_request(batch)
    responses = []
    for resp,batch_req in zip(batch_response,batch):
        try:
            resp = facebook.oip_client.postprocess_response(batch_req.to_GET_format(),resp)
        except FacebookAPIError as e:
            resp = e
        responses.append(resp)
    return responses

def fbtime_to_datetime(fbtime_str):
    '''
    Translate Facebook-formatted start_time or end_time field to datetime.

    Will return ValueError if the time string has an unexpected format.
    '''
    return datetime.strptime(fbtime_str,'%Y-%m-%dT%H:%M:%S')

def get_full_event_infos(event_ids):
    event_details = []
    cmds = []

    # TODO: repetitive. should be in apitools.faceboob somewhere
    for eid in event_ids:
        cmds.append(facebook.BatchCommand(eid,{'metadata':1}))
        if len(cmds) == 50:
            event_details.extend(_run_batch(cmds))
            cmds = []
    if len(cmds) > 0:
        event_details.extend(_run_batch(cmds))

    return event_details

def get_page_event_stubs(page_ids):
    '''
    Return a dict mapping page_ids to all event stubs they contain.

    Any API errors are suppressed and will simply return empty lists.
    '''
    page_event_lists = []
    cmds = []

    # TODO: repetitive. should be in apitools.faceboob somewhere. 
    # TODO: also FacebookAPIErrors as possible responses still sucks.
    for pid in page_ids:
        cmds.append(facebook.BatchCommand('%s/events'%str(pid)))
        if len(cmds) == 50:
            # just throw out FacebookAPIError responses
            responses = [ resp if isinstance(resp,dict) else {}
                                for resp in _run_batch(cmds) ]
            page_event_lists.extend( r.get('data',[]) for r in responses )
            cmds = []
    if len(cmds) > 0:
        # just throw out FacebookAPIError responses
        responses = [ resp if isinstance(resp,dict) else {}
                                for resp in _run_batch(cmds) ]
        page_event_lists.extend( r.get('data',[]) for r in responses )

    # TODO: REMOVE
    assert len(page_ids) == len(page_event_lists)
    return dict(zip(page_ids,page_event_lists))

def _get_owner(page_id,create_new=False):
    '''
    Tries to resolve an Organization linked to the given fb page id. Will
    create a new model instance if necessary and requested.
    '''
    try:
        return FacebookOrgRecord.objects.get(fb_id=page_id).organization
    except FacebookOrgRecord.DoesNotExist:            
        if create_new:
            # try to import an Organization to act as the event owner
            import_report = fbpages.import_org(page_id)
            # log any notices
            for notice in import_report.notices:
                outsourcing_log.info('Notice during creation of owner: %s' % str(notice))
            return import_report.model_instance
    return None

def _process_place_cache_support(event_info,resolve_cache):
    venue = event_info.get('venue',{})
    place_name = event_info.get('location','').strip()

    place = resolve_cache.query(place_name,venue)
    if not place:
        place = _process_place(event_info)
        resolve_cache.store(place_name,venue,place)
    
    return place

def _process_place(event_info):
    '''
    Attempts to tease a Place out of the given event_info. 

    May return either an already stored Place or a non-stored one (check 
    the pk value to tell the difference).

    Important! If Place is not yet stored, neither is Location inside
    it. Ensure the inner Location is saved first!
    '''
    # TODO: add some debug logging?
    venue = event_info.get('venue',{})
    place_name = event_info.get('location','').strip()

    if venue.get('id'):
        # best case is that our venue is identified by a Facebook ID
        try:
            return ExternalPlaceSource.facebook.get(uid=venue.get('id')).place
        except ExternalPlaceSource.DoesNotExist:
            pass

    # id didn't work, so lets get our hands dirty with some resolve/geocoding API calls
    if venue or place_name:
        location = fbpages.fbloc_to_loc(venue)
        
        # if there's no address or geocoding, we'll need to talk to outside services
        if not location.address:
            # try to build a seed to resolve with
            seed_loc = copy.deepcopy(location)
            
            # in the absense of city/state info, assume location is in same city/state as owner
            if not seed_loc.town or not seed_loc.state:
                fbowner = event_info.get('owner',{})
                if fbowner.get('id'):
                    try:
                        owner_place = ExternalPlaceSource.facebook.get(uid=fbowner.get('id')).place
                    except ExternalPlaceSource.DoesNotExist:
                        owner_place = None
                    if owner_place:
                        if not seed_loc.town:
                            seed_loc.town = owner_place.location.town
                        if not seed_loc.state:
                            seed_loc.state = owner_place.location.state

            seed_place = Place(name=place_name,location=seed_loc)
            resolved_place = resolve_place(seed_place)
            if resolved_place:
                # throw awy everything but the location
                location = resolved_place.location

        # really want geolocation, go to Google Geocoding for it if we need it
        if location.longitude is None or location.latitude is None:
            seed_loc = copy.deepcopy(location)
            resolved_location = resolve_location(seed_loc)
            if resolved_location: 
                location = resolved_location

        return Place(name=place_name,location=location)
            
    # worst case: we assume the event is happening at the location specified by the
    #   owners fbid (assuming this fbid is already linked to a place)
    fbowner_id = event_info.get('owner',{}).get('id')
    if fbowner_id:
        # TODO: try harder to resolve owner place? isolated event creation will always fail here
        try:
            return ExternalPlaceSource.facebook.get(uid=fbowner_id).place
        except ExternalPlaceSource.DoesNotExist:
            pass
    
    return None

@transaction.commit_on_success
def store_fbevent(event_info,event_image=None,
                    create_owners=True,
                    resolve_cache=None):
    '''
    Takes a dict of properties retreived from a Facebook Graph API call for
    a page and stores a Place from the information. The following 
    fields in the dict are used:
    - id          (required)
    - type        (required with value 'event' or a TypeError will be thrown)
    - name        (required)
    - start_time  (required. assumed to be in EST at the moment)
    - end_time    (required. assumed to be in EST at the moment)
    - description
    - venue       (dict with location values)
    - location    (simple string place name)
    - owner       (dict with stub info about organizer)

    No new Event will be returned if either an identical one already
    exists in the db, or a FacebookEventEntry already exists for the given 
    Facebook id. An INFO message is logged to note the attempt to store an 
    existing page as a Place.

    event_image is a URL to an image to use for this event. The Facebook 
    event object doesn't store it's picture directly, instead it stores it 
    as a connection to the event. If this argument is not provided, the 
    live service will be queried to retreive it.

    If create_owners is True, a Facebook-linked model instance will be
    created for the owner.

    The resolve_cache is an optional instance of a VenueResolveCache
    objects. See docs for it for details.
    '''
    fbid = event_info.get('id')
    if fbid is None:
        raise TypeError("Cannot store object without 'event' type.")

    # look to see if event already exists. return with it if so.
    try:
        event = FacebookEventRecord.objects.get(fb_id=fbid).event
        outsourcing_log.info('Existing fb event found for fbid %s'%str(fbid))
        return event
    except FacebookEventRecord.DoesNotExist:
        pass
    
    # ensure this is actually an event
    if event_info.get('type') != 'event':
        raise TypeError("Cannot store object without 'event' type.")

    ename = event_info.get('name').strip()
    # need to log events that don't have names
    if not ename:
        outsourcing_log.warning('No name for event with fbid %s' % fbid)

    event = Event(name=event_info['name'],
                    description=unicode(event_info.get('description','')),
                    url='http://www.facebook.com/%s' % fbid)

    # process times
    try:
        dtstart_est = EST.localize(fbtime_to_datetime(event_info.get('start_time')))
        dtend_est = EST.localize(fbtime_to_datetime(event_info.get('end_time')))
    except ValueError as e:
        raise ValueError('Bad start/end time for event fbid %s: %s' % (str(fbid),str(e)))
        
    event.dtstart = localtoutc(dtstart_est,return_naive=True)
    event.dtend = localtoutc(dtend_est,return_naive=True)

    # process image
    if event_image is None:
        try:
            event.image_url = facebook.oip_client.graph_api_picture_request(fbid)
        except IOError as e:
            outsourcing_log.error('Error retreiving picture for event %s: %s' % (str(eid),str(e)))
        
    # process place
    if resolve_cache:
        event.place = _process_place_cache_support(event_info,
                                                    resolve_cache=resolve_cache)
    else:
        event.place = _process_place(event_info)
    
    if event.place and event.place.pk is None:
        # TODO: ensure unique locations stored
        event.place.location.save()
        event.place.save()

    event.save()

    # create a FB record
    FacebookEventRecord.objects.create(fb_id=fbid,event=event)

    # add event categories as EventMeta objects
    categorize.add_event_oldtypes(event)
    
    # now set the event owner
    fbowner_id = event_info.get('owner',{}).get('id')
    if fbowner_id:
        owner = _get_owner(fbowner_id,create_new=create_owners)
        if owner:
            role = Role.objects.create(role_name='host',
                                        organization=owner,
                                        event=event)
        
    return event

class VenueResolveCache(object):
    def __init__(self):
        self._cache = {}

    def _to_key(self,name,fbloc):
        # TODO: revisit this hash
        return (name,tuple(sorted(fbloc.items())))

    def query(self,venue_name,venue_fbloc):
        return self._cache.get(self._to_key(venue_name,venue_fbloc))

    def store(self,venue_name,venue_fbloc,place):
        self._cache[self._to_key(venue_name,venue_fbloc)] = place


class EventImportReport(object):
    # notices can be expected to be among the following:
    #   - TypeError (when page is not a valid page for the model type being created)
    #   - FacebookAPIError (for successful responses with unexpected content)
    #   - IOError (if problem getting response from server)
    #   - EventImportReport.RelatedObjectCreationError (e.g. if Org couldn't be created inside Place creation)
    #   - EventImportReport.EventInstanceExists (if FBPageManager attempts to create an object already being managed)
    def __init__(self,fbevent_id,event_instance,notices=[]):
        self.fbevent_id = fbevent_id
        self.event_instance = event_instance
        self.notices = notices

    class RelatedObjectCreationError(Exception):
        def __init__(self,related_object,error):
            '''
            Related object is any string, error is Exception that occurred
            while object creation was being attempted.
            '''
            self.related_object = related_object
            self.error = error
            super(EventImportReport.RelatedObjectCreationError,self).__init__()

        def __str__(self):
            return 'RelatedObjectCreationError: %s failed with error: "%s"' % \
                    (str(self.related_object),str(self.error))

    class EventInstanceExists(Exception):
        def __init__(self,fbid):
            self.fbid = fbid
            super(EventImportReport.EventInstanceExists,self).__init__()
        
        def __str__(self):
            return 'EventInstanceExists: Facebook page id %s' % str(self.fbid)

class EventImportManager(object):
    '''
    Class to manage the building and storage of Event model instances from 
    Facebook events.
    '''
    def __init__(self):
        # each page ids requested will ultimately be put in one (and only one) of these buckets:
        self._cached_event_infos = {}       # fbevent_id:{event_info}
        self._unavailable_events = {}       # fbevent_id:error
        self._cached_page_estub_lists = {}  # page_id:[fbevent_stubs]

    def pull_event_info(self,fbevent_ids,use_cache=True):
        '''
        Returns a list of fb event info dicts pulled from the live FB 
        service.

        If use_cache is True, any available cached event information 
        stored in this manager will be used.
        '''
        # if we can use the cache, pull any cached ids from the API request
        if use_cache:
            ids_to_pull = set(fbevent_ids)-set(self._cached_event_infos.keys())
        else:
            ids_to_pull = fbevent_ids
        
        try:
            page_infos = get_full_event_infos(ids_to_pull)
        except IOError as e:
            outsourcing_log.error('IOError on batch event info pull: %s' % str(e))
            # spread the IOError to all requests
            page_infos = [e]*len(ids_to_pull)

        # update the cached items
        for pid,info in zip(ids_to_pull,page_infos):
            # each "info" is either a successful page info response, or 
            #  an Exception. put them into the correct bnuckets
            if isinstance(info,Exception):
                self._unavailable_events[pid] = info
            else:
                self._cached_event_infos[pid] = info

        # return the responses in the same order as the requests
        return [self._cached_event_infos.get(eid,self._unavailable_events.get(eid))
                    for eid in fbevent_ids]

    def pull_event_info_from_pages(self,page_ids,start_filter=None,use_cache=True):
        '''
        Returns a map of page_id to a list of fb event infos, one per 
        page id input.

        If start_filter is provided, events occuring before the given 
        datetime will not be pulled.
        '''
        # if we can use the cache, pull any cached ids from the API request
        if use_cache:
            pids_to_check = set(page_ids) - set(self._cached_page_estub_lists.keys())
        else:
            pids_to_check = page_ids
        
        try:
            page_estubs_map = get_page_event_stubs(pids_to_check)
            # store all results in the cache
            self._cached_page_estub_lists.update(page_estubs_map)
            # everything should be in the cache now: use only it below
        except IOError as e:
            outsourcing_log.error('IOError on batch event stub pull: %s' % str(e))
            # if we're using the cache, there's still a chance to recover some events from cache
            # if not, just return now
            if not use_cache:
                return {pid:[] for pid in page_ids}

        # build list of relevant time-filtered event ids from contents of cache
        page_eids_map = {}
        for pid in page_ids:
            stubs = self._cached_page_estub_lists.get(pid,[])
            if start_filter:
                stubs = [stub for stub in stubs
                            if fbtime_to_datetime(stub['start_time']) >= start_filter ]
            page_eids_map[pid] = [stub['id'] for stub in stubs]

        # flatten list of eids
        all_eids = list(chain.from_iterable(page_eids_map.values()))

        # finally get the full events
        fbevents = self.pull_event_info(all_eids,use_cache=use_cache)

        # got a flat list of all the events: now group them by source pages
        eid_fbevent_map = dict(zip(all_eids,fbevents))  # for faster accessing
        page_events_map = { pid:[eid_fbevent_map[eid] for eid in eids] 
                                for pid,eids in page_eids_map.items() }

        return page_events_map

    def _store_event(self,fbevent,event_image,import_owners=True,resolve_cache=None):
        eid = fbevent['id']
        # first off -- if event is already stored, we're done -- no overwriting as of now
        try:
            FacebookEventRecord.objects.get(fb_id=eid)
            return EventImportReport(eid,None,
                        notices=[EventImportReport.EventInstanceExists(eid)])
        except FacebookEventRecord.DoesNotExist:
            pass

        # try to store, and catch TypeErrors from info not being a 'event'
        try:
            event = store_fbevent(fbevent,
                                    event_image,
                                    create_owners=import_owners,
                                    resolve_cache=resolve_cache)
            return EventImportReport(eid,event)
        except TypeError as e:
            return EventImportReport(eid,None,notices=[e])

    def import_events(self,fbevent_ids,use_cache=True,import_owners=True):
        '''
        Inserts Events for a batch of fbevent_ids from Facebook.

        Will skip over creating any Events already tracked by a 
        FacebookEventRecord instance and return a result with a 
        EventInstanceExists set as the error.

        If use_cache is True, any available cached event information 
        stored in this manager will be used.

        If import_owners is True, a new Organization will be created
        for the event owner if it not yet linked to the relevant fbid.

        Returns a parallel list of EventImportReport objects.
        '''
        # TODO: could do something here to filter out fbevent ids that we 
        #       already have info for before we pull them
        fbevent_infos = self.pull_event_info(fbevent_ids,use_cache=use_cache)
        fbevent_pics = []

        for eid in fbevent_ids:
            try:
                fbevent_pics.append(facebook.oip_client.graph_api_picture_request(eid))
            except IOError as e:
                outsourcing_log.error('Error retreiving picture for event %s: %s' % (str(eid),str(e)))
                fbevent_pics.append('')
        
        reports = []
        for eid,info,pic in zip(fbevent_ids,fbevent_infos,fbevent_pics):
            if not isinstance(info,Exception):
                reports.append(self._store_event(info,
                                                    pic,
                                                    import_owners=import_owners))
            else:
                reports.append(EventImportReport(eid,None,[info]))
        return reports

    def import_events_from_pages(self,page_ids,start_filter=None,use_cache=True,import_owners=True):
        '''
        Inserts Places for a batch of page_ids from Facebook. Returns a 
        dict of lists of EventImportReport objects.

        If start_filter is provided, events occuring before the given 
        datetime will not be imported.
        
        If querying of page fails, no error will be procuded, just an 
        empty list in it's slot in the return list.

        See import_events for notes about options.
        '''
        # TODO: could do something here to filter out fbevent ids that we 
        #       already have info for before we pull them
        page_fbevents_map = self.pull_event_info_from_pages(page_ids,
                                                            start_filter=start_filter,
                                                            use_cache=use_cache)
        
        page_reports_map = {}
        for pid,fbevents in page_fbevents_map.items():
            venue_cache = VenueResolveCache()   # used to prevent redundant resolve calls for a 
                                                # series of events at the same location
            reports = []
            for fbevent in fbevents:
                # TODO: don't like fbevent being a possible exception. revisit.
                if isinstance(fbevent,Exception):
                    reports.append( EventImportReport(None,None,[fbevent]) )
                else:
                    eid = fbevent['id']
                    try:
                        pic = facebook.oip_client.graph_api_picture_request(eid)
                    except IOError as e:
                        outsourcing_log.error('Error retreiving picture for event %s: %s' % (str(eid),str(e)))
                        pic = ''
                    reports.append( self._store_event( fbevent,
                                                        pic,
                                                        import_owners=import_owners,
                                                        resolve_cache=venue_cache))
            page_reports_map[pid] = reports
        return page_reports_map

def import_event(event_id,import_owners=True):
    '''
    Quick import of an Event given an fb event id. Returns an 
    EvenImportReport.
    '''
    mgr = EventImportManager()
    return mgr.import_events([event_id],import_owners=import_owners)[0]
