from onlyinpgh.apitools.facebook import BatchCommand
from onlyinpgh.apitools.facebook import oip_client as fb_client
import json

def gather_place_pages(center,radius,query=None,limit=4000):
    '''
    Returns a list of Facebook place page 'objects' represneting all places 
    found in the given area. Object fields can be found at 
    https://developers.facebook.com/docs/reference/api/page/

    center should be a tuple of (latitude,logitude) values, and radius is 
    in meters (i think?)

    If query is omitted, a "blank query" will be run by running the same 
    center and radius query 26 separate times, once per letter of the 
    alphabet as the actual query argument.
    '''
    # no query given, run one for each letter of the alphabet
    if query is None:
        ids_seen = set()    # cache the ids in the list for a quick duplicate check
        all_pages = []
        # cycle thru each letter
        for letter in [chr(o) for o in range(ord('a'),ord('z')+1)]:
            for page in gather_place_pages(center,radius,query=letter,limit=limit):
                if page['id'] not in ids_seen:
                    ids_seen.add(page['id'])
                    all_pages.append(page)
        return all_pages

    return fb_client.graph_api_query('search',q=query,
                                                type='place',
                                                center='%f,%f' % center,
                                                distance=radius,
                                                limit=limit)

def gather_event_info(page_id):
    '''
    Returns a list of event object information for all events connected
    to the given page.
    '''
    # make this a batch request to get detailed event info for each
    # id returned from the first events call
    batch_request = [ BatchCommand('%s/events'%str(page_id),
                                    options={'limit':1000},
                                    name='get-events'),
                      BatchCommand('',
                                    options={'ids':'{result=get-events:$.data.*.id}'}),
                    ]
    full_response = fb_client.run_batch_request(batch_request,process_response=False)

    event_responses = json.loads(full_response[1]['body'])
    return event_responses.values() # full responses are maps from id to info

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
