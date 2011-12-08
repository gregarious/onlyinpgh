from onlyinpgh.apitools.facebook import BatchCommand
from onlyinpgh.apitools.facebook import oip_client as fb_client

from copy import copy
import json, time


def gather_place_pages(center,radius,query=None,limit=4000,batch_requests=True):
    '''
    Returns a list of Facebook place page 'objects' represneting all places 
    found in the given area. Object fields can be found at 
    https://developers.facebook.com/docs/reference/api/page/

    center should be a tuple of (latitude,logitude) values, and radius is 
    in meters (i think?)

    If query is omitted, a "blank query" will be run by running the same 
    center and radius query 26 separate times, once per letter of the 
    alphabet as the actual query argument. 

    If batch_request is True (default), these requests will be batched, 
    otherwise they'll be run once at a time. Commands with a large number
    of results may fail if batched.
    '''
    # no query given, run one for each letter of the alphabet
    
    search_opts = dict(type='place',
                        center='%f,%f' % center,
                        distance=radius,
                        limit=limit)
    if query is None:
        batch_commands, pages_unfilitered = [], []
        letters = [chr(o) for o in range(ord('a'),ord('z')+1)]

        if batch_requests:
            for letter in letters:
                opts = copy(search_opts)
                opts['q']=letter
                batch_commands.append(BatchCommand('search',options=opts))
            for response in fb_client.run_batch_request(batch_commands):
                pages_unfilitered.extend(response['data'])
        else:
            for letter in letters:
                pages_unfilitered.extend(fb_client.graph_api_query('search',q=letter,**search_opts))
                  
        # need to go through the 26 separate page sets to filter out dups
        ids_seen = set()    # cache the ids in the list for a quick duplicate check
        pages = []
        for page in pages_unfilitered:
            if page['id'] not in ids_seen:
                ids_seen.add(page['id'])
                pages.append(page)
        return pages
    else:
        return fb_client.graph_api_query('search',q=query,**search_opts)

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
