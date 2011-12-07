import urllib, json

def get_basic_access_token(client_id,client_secret):
    '''
    Quick utility function to generate a basic access token given an app id
    and secret values. Shouldn't need 
    '''
    query = { 'client_id':      client_id,
              'client_secret':  client_secret,
              'grant_type':     'client_credentials'}

    url = 'https://graph.facebook.com/oauth/access_token?' + urllib.urlencode(query)
    response = urllib.urlopen(url).read()
    
    try:
        key,val = response.split('=')
        if key == 'access_token':
            return val        
    except ValueError:  # be silent for now, it will be reported below
        pass

    # if we made it this far, we didn't return with a value response
    raise Exception("Unexpected response from server: '%s'" % response)

class GraphAPIClient(object):
    def __init__(self,access_token=None):
        self.access_token = access_token

    def graph_api_object(self,obj_id):
        '''
        Returns a single object from the graph API.
        '''
        request_url = 'https://graph.facebook.com/' + str(obj_id)
        if self.access_token:
            request_url += '?' + urllib.urlencode({'access_token':self.access_token})

        response = json.load(urllib.urlopen(request_url))
        if not response or 'error' in response:
            raise Exception('Graph API returned error. Content:\n%s' % str(response))    
        return response

    def graph_api_query(self,suburl,max_pages=10,**kw_options):
        '''
        Thin wrapper around Graph API query that returns pages of 'data' arrays. 
        kw_options can take any option that the graph query could take. 

        e.g. - graph_api_query('cocacola/events') 
                for all events connected to Coca-Cola
             - graph_api_query('search',q=coffee,
                                        type=place,
                                        center=37.76,-122.427,
                                        distance=1000)
                for all pages with coffee in the name 1km from (37.76,-122.427)
            See https://developers.facebook.com/docs/reference/api/ for more.

        Paging will be automatically followed up to max_pages requests. This
        limit can be disabled by setting it to None or a non-positive number.
        A runaway query could run for a VERY long time, hence the need to 
        explicitly disabling the max pages.
        '''
        if max_pages < 1:
            max_pages = None

        get_args = {}
        if self.access_token:
            get_args = {'access_token':self.access_token}
        if kw_options:
            get_args.update(kw_options)
        
        request_url = 'https://graph.facebook.com/' + suburl
        if get_args:
            request_url += '?' + urllib.urlencode(get_args)

        all_data = []
        pages_read = 0
        # inside loop because results might be paged
        while request_url:
            response = json.load(urllib.urlopen(request_url))
            if 'error' in response:
                raise Exception('Graph API returned error. Content:\n%s' % str(response))

            if 'data' not in response:
                raise Exception('Graph API returned unexpected response. Content:\n%s' % str(response))
            
            all_data.extend(response['data'])

            # if there's more pages to the results, fb gives a handy url to go to next page
            if 'paging' in response and 'next' in response['paging']:
                request_url = response['paging']['next']
                pages_read += 1
            else:
                request_url = ''

            if max_pages is not None and pages_read >= max_pages:
                break

        return all_data

    def gather_place_pages(self,center,radius,query=None,limit=4000):
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
                for page in self.gather_place_pages(center,radius,query=letter,limit=limit):
                    if page['id'] not in ids_seen:
                        ids_seen.add(page['id'])
                        all_pages.append(page)
            return all_pages

        return self.graph_api_query('search',q=query,
                                                type='place',
                                                center='%f,%f' % center,
                                                distance=radius,
                                                limit=limit)

    def gather_event_info(self,page_id):
        '''
        Returns a list of event object information for all events connected
        to the given page.
        '''
        event_stubs = self.graph_api_query('%s/events'%str(page_id),limit=1000,max_pages=None)
        # this took almost 4 minutes with 400 events. do 50 at a time with batch requests 
        # via urllib2.Request
        # https://developers.facebook.com/docs/reference/api/batch/
        # http://docs.python.org/library/urllib2.html#urllib2.Request
        return [self.graph_api_object(event['id']) for event in event_stubs]


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

# onlyinpgh.com app credentials
OIP_APP_ID = '203898346321665'
OIP_APP_SECRET = '897ca9d744d43da15d40d3f793f112e3'
# if this stops working, try calling get_basic_access_token directly
OIP_ACCESS_TOKEN = '203898346321665|e_aVTLcJCsV3c9tiQJn0tZjWcZg'

# a default GraphAPIClient that uses OIP's credentials
oip_client = GraphAPIClient(OIP_ACCESS_TOKEN)