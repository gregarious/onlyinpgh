from onlyinpgh.apitools.facebook import BatchCommand, FacebookAPIError
from onlyinpgh.apitools.facebook import oip_client as fb_client
from onlyinpgh.places import outsourcing as place_outsourcing
from onlyinpgh.apitools.facebook import GraphAPIClient

from onlyinpgh.events import categorize

from onlyinpgh.places.models import Place, Location
from onlyinpgh.events.models import Event, FacebookEventRecord, Role


from copy import deepcopy
import json, time, datetime

from pytz import timezone
utc = timezone('utc')
est = timezone('US/Eastern')

import logging
dbglog = logging.getLogger('onlyinpgh.debugging')

# TODO: ALL TEMPORARY HACKS
# map from (venue,place_name)
hacked_event_cache = {}
def check_event_cache(venue,place_name):
    key = (str(venue),place_name)
    return hacked_event_cache.get(key)
def save_to_event_cache(venue,place_name,place):
    key = (str(venue),place_name)
    hacked_event_cache[key] = place

def debug_loc_print(l):
    return '%s, %s, %s %s (%.3f,%.3f)' % \
                (l.address,l.town,l.state,l.postcode,l.latitude or 0,l.longitude or 0)

def debug_place_print(place):
    return '%s: %s' % (place.name,debug_loc_print(place.location))

# TODO: add condition that doesn't create new place/orgs. also add test for it
def event_fbid_to_event(event_fbid,referer_fbid=None,create_new=True,fbevent_cache={}):
    try:
        record = FacebookEventRecord.objects.get(fb_id=event_fbid)
        if record.associated_event or not create_new:
            dbglog.info('found existing event for fbid %s'%event_fbid)
            return record.associated_event
    except FacebookEventRecord.DoesNotExist:
        record = FacebookEventRecord(fb_id=event_fbid)
        
    fbevent = None
    if referer_fbid:
        referer_events = fbevent_cache.get(referer_fbid,[])
        try:
            fbevent = (e for e in referer_events if e['id'] == event_fbid).next()
        except StopIteration:
            pass

    if fbevent:
        dbglog.debug('retreiving event info from cache')
    else:
        try:
            dbglog.debug('retreiving event info from facebook')
            fbevent = fb_client.graph_api_objects(event_fbid)
        except FacebookAPIError as e:
            dbglog.error('Facebook error occured!')
            dbglog.error(str(e))
            return None

    if 'name' not in fbevent:
        dbglog.error('no name for event with fbid %s' % event_fbid)
        return None

    event = Event(name=fbevent['name'],
                    description=fbevent.get('description',''),
                    url='http://www.facebook.com/%s' % event_fbid)
    try:
        # TODO: look into dateutil package
        dtstart_est = est.localize(datetime.datetime.strptime(fbevent.get('start_time'),
                                                                "%Y-%m-%dT%H:%M:%S"))
        event.dtstart = utc.normalize(dtstart_est.astimezone(utc)).replace(tzinfo=None)
    except ValueError:
        dblog.error('bad start time (%s) for event fbid %s' % (fbevent.get('start_time'),event_fbid))
        return
    try:
        dtend_est = est.localize(datetime.datetime.strptime(fbevent.get('end_time'),
                                                            "%Y-%m-%dT%H:%M:%S"))
        event.dtend = utc.normalize(dtend_est.astimezone(utc)).replace(tzinfo=None)
    except ValueError:
        dblog.error('bad end time (%s) for event fbid %s' % (fbevent.get('end_time'),event_fbid))
        return

    # wrap this in something else
    import urllib
    try:
        event.image_url = urllib.urlopen('http://graph.facebook.com/%s/picture?type=normal'%event_fbid).url
    except IOError as e:
        dbglog.warning('Facebook IOError "%s" while retreiving image: sleeping 3 secs...'%str(e))
        time.sleep(3)
        event.image_url = urllib.urlopen('http://graph.facebook.com/%s/picture?type=normal'%event_fbid).url
        
    venue = fbevent.get('venue',{})
    place_name = fbevent.get('location','').strip()

    # figure out the event place
    place = None
    if venue.get('id'):
        # best case is that our venue is identified by a Facebook ID
        # TODO: we ignore place_name here. should this be a concern?
        dbglog.debug('retriving place via venue ID')
        place = place_outsourcing.page_id_to_place(venue.get('id'))
    elif venue or place_name:
        dbglog.debug('resolving place via API calls')
        place = check_event_cache(venue,place_name)
        if place:
            dbglog.debug('found place in hack cache')
        else:
            # if we at least have a venue or location string, we can work with it
            location = place_outsourcing.fbloc_to_loc(venue)
        
            # if there's no address or geocoding, we'll need to talk to outside services
            if not location.address:
                # TODO: insert more factual logic? (i.e. saving uid, setting place to this uid, etc.)
                dbglog.debug('attempting factual resolve')
                seed_loc = deepcopy(location)
                # give some hints on city/state from the owner if it exists
                fbowner = fbevent.get('owner',{})
                if fbowner.get('id'):
                    if not seed_loc.town or not seed_loc.state:
                        dbglog.debug('fetching organization with fbid %s for place seed hints' % fbowner['id'])
                        owner_place = place_outsourcing.page_id_to_place(fbowner['id'],create_new=False)
                        if owner_place:
                            if not seed_loc.town:
                                dbglog.debug('adding town "%s" to factual seed' % owner_place.location.town)
                                seed_loc.town = owner_place.location.town
                            if not seed_loc.state:
                                dbglog.debug('adding state "%s" to factual seed' % owner_place.location.state)
                                seed_loc.state = owner_place.location.state
                            # TODO: zip too? or a biut too much?
                seed_place = Place(name=place_name,location=seed_loc)
                resolved_place = place_outsourcing.resolve_place(seed_place)
                if resolved_place:
                    dbglog.debug('successful Factual resolve: "%s" => "%s"' % \
                                    (debug_place_print(seed_place),debug_place_print(resolved_place)))
                    location = resolved_place.location
                    # TODO: should we just throw away the resolved name?
            # really want geolocation, go to Google Geocoding for it if we need it
            if location.longitude is None or location.latitude is None:
                dbglog.debug('attempting geocode')
                seed_loc = deepcopy(location)
                resolved_location = place_outsourcing.resolve_location(seed_loc)
                if resolved_location: 
                    location = resolved_location
                    dbglog.debug('successful geocoding: "%s" => "%s"' % \
                                    (debug_loc_print(seed_loc),debug_loc_print(resolved_location)))

            if location:
                # TODO: put this into the manager or a Location.save override
                location,created = Location.objects.get_or_create(
                                        address=location.address,
                                        postcode=location.postcode,
                                        town=location.town,
                                        state=location.state,
                                        country=location.country,
                                        neighborhood=location.neighborhood,
                                        latitude=location.latitude,
                                        longitude=location.longitude)
                if created:
                    dbglog.debug('saved new location "%s"' % debug_loc_print(location))
                else:
                    dbglog.debug('retrieved existing location "%s"' % debug_loc_print(location))

            try:
                place,created = Place.objects.get_or_create(
                                        name=place_name,
                                        location=location)
                if created:
                    dbglog.info('created new place for fbid %s: "%s"' % (event_fbid,debug_place_print(place)))
                else:
                    dbglog.info('retreived existing place for fbid %s: "%s"' % (event_fbid,debug_place_print(place)))
                save_to_event_cache(venue,place_name,place)
            except Warning as w:
                dbglog.warning('while saving place for fbid %s: %s' % (event_fbid,str(w)))
                # TODO: soooo apparently the place gets saved, but then the id gets removed? wtf.
                # This means we can't save the record. hm.
                return
            
    # worst case: we assume the event is happening at the referer's location (if applicable)
    elif referer_fbid:
        dbglog.debug('retriving place via referer fbid %s' % referer_fbid)
        place = place_outsourcing.page_id_to_place(referer_fbid)

    # finally set the place
    event.place = place

    # and save the event!
    event.save()

    # add event categories
    categorize.add_event_oldtypes(event)

    # TODO: revisit
    try:
        estr = unicode(event)
    except UnicodeDecodeError:
        estr = '<UNICODE ERROR>'
    dbglog.info('created new event for fbid %s: "%s"' % (event_fbid,estr))
    
    # Complete the FB record we started building up above
    record.associated_event = event
    record.save()

    # now into the roles: owner and referer:
    fbowner = fbevent.get('owner',{})
    if fbowner.get('id'):
        dbglog.debug('resolving owner %s' % fbowner['id'])
        owner = place_outsourcing.page_id_to_organization(fbowner['id'])
        if not owner:
            dbglog.error('could not retreive owner information with fbid %s' % fbowner['id'])
        # TODO: revisit
        try:
            ostr = unicode(owner)
        except UnicodeDecodeError:
            ostr = '<UNICODE ERROR>'
        dbglog.info('creating owner for "%s": "%s"' % (estr,ostr))
        role = Role.objects.create(role_name='creator',
                                    organization=owner,
                                    event=event)
    else:
        dbglog.notice('no owner listed for fbid %s' % event_fbid)

    # also store the referer if it is different from the owner
    if referer_fbid is not None and fbowner.get('id') != referer_fbid:
        ref = place_outsourcing.page_id_to_organization(referer_fbid)
        if not owner:
            dbglog.error('could not retreive referer information with fbid %s' % referer_fbid)
        # TODO: revisit
        try:
            rstr = unicode(ref)
        except UnicodeDecodeError:
            rstr = '<UNICODE ERROR>'
        dbglog.info('creating referer for "%s": "%s"' % (estr,rstr))

        role = Role.objects.create(role_name='referer',
                                    organization=ref,
                                    event=event)
    return event

def gather_event_info(page_ids):
    '''
    Returns a mapping of page_ids to a list of all events connected to
    each respective page.
    '''
    #import pickle
    #err_f = open('/Users/gdn/Sites/onlyinpgh/events/event_batch.pickle','w')
    results = {}

    # helper function to run a batch of requests and add them to the results
    def _run_batch(ir_map):
        # create a master list of all batch commands
        all_batch_reqs = []
        for page_id,req in ir_map.items():
            all_batch_reqs.extend(req)
        try:
            # run the batch
            full_response = fb_client.run_batch_request(all_batch_reqs,process_response=False)
        except Exception as e:
            # temporary catch-all to log problem to disk
            # pickle.dump(BatchErrContext(e,all_batch_reqs,full_response,None,None,None),err_f)
            # TODO: handle better?
            for page_id in ir_map.keys():
                results[page_id] = []

        # cycles through results 2 at a time
        for i,page_id in enumerate(ir_map.keys()):
            try:
                first_response = json.loads(full_response[2*i]['body'])
                if 'data' not in first_response or len(first_response['data']) == 0:
                    # if the first response has no data, there are no events
                    results[page_id] = []
                else:
                    # body of second request is JSON array of ids mapped to events
                    id_event_map = json.loads(full_response[2*i+1]['body'])
                    results[page_id] = id_event_map.values()
            except Exception as e:
                # temporary catch-all to log problem to disk
                # pickle.dump(BatchErrContext(e,all_batch_reqs,full_response,
                #            full_response[2*i],full_response[2*i+1],page_id),
                #            err_f)
                results[page_id] = []

    # cycle through 
    id_requests_map = {}
    dbglog.info('running about %d batches' % (len(page_ids)/25+1))
    ctr = 0
    for page_id in page_ids:
        id_requests_map[page_id] = (
                    BatchCommand('%s/events'%str(page_id),
                                    options={'limit':1000},
                                    name='get-events-%s'%str(page_id),
                                    omit_response_on_success=False),
                    BatchCommand('',
                                    options={'ids':'{result=get-events-%s:$.data.*.id}'%str(page_id)}),
                    )
        
        # 50 is Facebook's batch request limit. send this batch off at 25 (2 per page)
        if len(id_requests_map) == 25:
            ctr += 1
            dbglog.info('running batch %d'%ctr)
            time.sleep(.2)
            _run_batch(id_requests_map)
            id_requests_map = {}    # reset and start over
    
    # if there's still some requests not run, do it now
    if len(id_requests_map) > 0:
        ctr += 1
        dbglog.info('running batch %d'%ctr)
        time.sleep(.2)
        _run_batch(id_requests_map)

    #err_f.close()

    return results
