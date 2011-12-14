from onlyinpgh.apitools.facebook import BatchCommand, FacebookAPIError
from onlyinpgh.apitools.facebook import oip_client as fb_client
from onlyinpgh.places import outsourcing as place_outsourcing

from onlyinpgh.places.models import Place, Location
from onlyinpgh.events.models import Event, FacebookEventRecord, Role

from copy import deepcopy
import json, time, datetime

from pytz import timezone
utc = timezone('utc')
est = timezone('US/Eastern')


test_ids = [u'123553834405202', u'171128159571410', u'122579773164', u'183027055050241', u'146817625337619', u'102805843089592', u'134786796545', u'177483835622113', u'39206713055', u'122226730263', u'122827324412158', u'32767836552', u'238844289471725', u'114684111881007', u'289028790850', u'149036438458327', u'153469736978', u'59534298851', u'126634834049032', u'90421944415', u'161796890542622', u'157691030961161', u'200106181977', u'150811018276293', u'136518339701903', u'104712989579167', u'220570274635552', u'53487807341', u'114990195221517', u'109624895040', u'128783590515514', u'184039188275260', u'182026059984', u'123741464302648', u'165006596211', u'300958408128', u'25395127498', u'235633321605', u'88277842417', u'118219938190929', u'115011611904899', u'51395287730', u'331481895725']
import pickle
def debug_load_eventmap(filename='/Users/gdn/Sites/onlyinpgh/events/all-events.pickle'):
    with open(filename) as f:
        return pickle.load(f)

def debug_save_eventmap(id_event_map,filename='/Users/gdn/Sites/onlyinpgh/events/all-events.pickle'):
    with open(filename,'w') as f:
        return pickle.dump(id_event_map,f)

def debug_process_events(id_event_map):
    for pid,events in id_event_map.items():
        for event in events:
            fbevent_id_to_event(event['id'],referer_fbid=pid,fbevent_cache=id_event_map)

def fbevent_id_to_event(fbevent_id,referer_fbid=None,create_new=True,fbevent_cache={}):
    print 'processing eventid', fbevent_id
    try:
        record = FacebookEventRecord.objects.get(fb_id=fbevent_id)
        if record.associated_event or not create_new:
            print 'found record. returning.'
            return record.associated_event
    except FacebookEventRecord.DoesNotExist:
        record = FacebookEventRecord(fb_id=fbevent_id)
        
    if fbevent_id in fbevent_cache:
        fbevent = fbevent_cache[event_id]
        print 'found event in cache'
    else:
        try:
            fbevent = fb_client.graph_api_objects(fbevent_id)
        except FacebookAPIError as e:
            print 'problem retreiving event %s from FB: %s' % (str(fbevent_id),str(e))
            return None

    event = Event(name=fbevent['name'])
    try:
        # TODO: look into dateutil package
        dtstart_est = est.localize(datetime.datetime.strptime(fbevent.get('start_time'),
                                                                "%Y-%m-%dT%H:%M:%S"))
        event.dtstart = utc.normalize(dtstart_est.astimezone(utc)).replace(tzinfo=None)
    except ValueError:
        print eid, 'bad start time', fbevent.get('start_time')
        return
    try:
        dtend_est = est.localize(datetime.datetime.strptime(fbevent.get('end_time'),
                                                            "%Y-%m-%dT%H:%M:%S"))
        event.dtend = utc.normalize(dtend_est.astimezone(utc)).replace(tzinfo=None)
    except ValueError:
        print eid, 'bad end time', fbevent.get('end_time')
        return
    
    # wrap this in something else
    import urllib
    event.image_url = urllib.urlopen('http://graph.facebook.com/%s/picture?type=normal'%fbevent_id).url

    fbowner = fbevent.get('owner',{})
    if fbowner.get('id'):
        owner = place_outsourcing.page_id_to_place(fbowner['id'],create_new=False)
    else:
        owner = None

    venue = fbevent.get('venue',{})
    place_name = fbevent.get('location','').strip()

    # figure out the event place
    place = None
    if venue.get('id'):
        # best case is that our venue is identified by a Facebook ID
        # TODO: we ignore place_name here. should this be a concern?
        print 'retriving place via venue ID'
        place = place_outsourcing.page_id_to_place(venue.get('id'))
    elif venue or place_name:
        print 'resolving place via APIs'
        # if we at least have a venue or location string, we can work with it
        location = place_outsourcing.fbloc_to_loc(venue)
    
        # if there's no address or geocoding, we'll need to talk to outside services
        if not location.address:
            # TODO: insert more factual logic? (i.e. saving uid, setting place to this uid, etc.)
            print 'attempting factual resolve'
            seed_loc = deepcopy(location)
            # give some hints on city/state from the owner if it exists
            fbowner = fbevent.get('owner',{})
            if fbowner.get('id'):
                owner_place = place_outsourcing.page_id_to_place(fbowner['id'],create_new=False)
                if owner_place:
                    if not seed_loc.town:
                        seed_loc.town = owner_place.location.town
                    if not seed_loc.state:
                        seed_loc.state = owner_place.location.state
                    # TODO: zip too? or a biut too much?
            resolved_place = place_outsourcing.resolve_place(Place(name=place_name,location=seed_loc))
            if resolved_place:
                print 'resolve success'
                location = resolved_place.location
                # TODO: should we just throw away the resolved name?
        # really want geolocation, go to Google Geocoding for it if we need it
        if location.longitude is None or location.latitude is None:
            print 'attempting geocode'
            resolved_location = place_outsourcing.resolve_location(location)
            if resolved_location:
                print 'geocoding success'
                location = resolved_location

        if location:
            # TODO: put this into the manager or a Location.save override
            location,_ = Location.objects.get_or_create(
                                    address=location.address,
                                    postcode=location.postcode,
                                    town=location.town,
                                    state=location.state,
                                    country=location.country,
                                    neighborhood=location.neighborhood,
                                    latitude=location.latitude,
                                    longitude=location.longitude)
        
        place,_ = Place.objects.get_or_create(
                                name=place_name,
                                location=location)
        print 'result',place
    # worst case: we assume the event is happening at the referer's location (if applicable)
    elif referer_fbid:
        print 'retriving place via referer id'
        place = place_outsourcing.page_id_to_place(referer_fbid)

    # finally set the place
    event.place = place

    # and save the event!
    event.save()

    # Complete the FB record we started building up above
    record.associated_event = event
    record.save()

    # now into the roles: owner and referer:
    fbowner = fbevent.get('owner',{})
    if fbowner.get('id'):
        owner = place_outsourcing.page_id_to_organization(fbowner['id'])
        if not owner:
            raise Exception('could not retreive owner information for event '+str(fbevent_id))
        print 'setting owner to',owner
        role = Role.objects.create(role_name='creator',
                                    organization=owner,
                                    event=event)

    # also store the referer if it is different from the owner
    if referer_fbid is not None and fbowner.get('id') != referer_fbid:
        ref = place_outsourcing.page_id_to_organization(referer_fbid)
        if not ref:
            raise Exception('could not retreive owner information for fb page '+str(owner['id']))
        print 'setting referer to',ref
        role = Role.objects.create(role_name='referer',
                                    organization=ref,
                                    event=event)

    print 'done!', event
    return event

def gather_event_info(page_id):
    '''
    Returns a list of event object information for all events connected
    to the given page.
    '''
    # make this a batch request to get detailed event info for each
    # id returned from the first events call
    batch_requests = [ BatchCommand('%s/events'%str(page_id),
                                    options={'limit':1000},
                                    name='get-events',
                                    omit_response_on_success=False),
                       BatchCommand('',
                                    options={'ids':'{result=get-events:$.data.*.id}'}),
                     ]
    full_response = fb_client.run_batch_request(batch_requests,process_response=False)
    first_response = json.loads(full_response[0]['body'])
    # if the first response has no data, there are no events. return
    if 'data' not in first_response or len(first_response['data']) == 0:
        # TODO: return exception if error happened here?
        return []
    else:
        # body of second request is JSON array of ids mapped to events
        id_event_map = json.loads(full_response[1]['body'])
        return id_event_map.values() 

class BatchErrContext:
    def __init__(self,ex,all_batch_commands,all_responses,bad_response1,bad_response2,page_id):
        self.exception = ex
        self.all_batch_commands = all_batch_commands
        self.all_responses = all_responses
        self.bad_response1 = bad_response1
        self.bad_response2 = bad_response2
        self.error_page_id = page_id

def gather_event_info_batch(page_ids):
    '''
    Returns a mapping of page_ids to a list of all events connected to
    the given page.
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
            time.sleep(.2)
            _run_batch(id_requests_map)
            id_requests_map = {}    # reset and start over
    
    # if there's still some requests not run, do it now
    if len(id_requests_map) > 0:
        time.sleep(.2)
        _run_batch(id_requests_map)

    #err_f.close()

    return results

def _get_all_places_from_cron_job():
    '''
    Runs a series of queries to return the same results that the old oip
    fb5_getLocal.execute_quadrants Java code searches over.
    '''
    search_coords = [ (40.44181,-80.01277),
                      (40.666667,-79.700556),
                      (40.666667,-80.308056),
                      (40.216944,-79.700556),
                      (40.216944,-80.308056),
                      (40.44181,-80.01277),
                    ]

    all_ids = set()
    for coords in search_coords:
        ids = [page['id'] for page in default_graph_client.gather_place_pages(coords,25000)]
        all_ids.update(ids)
    return list(all_ids)
