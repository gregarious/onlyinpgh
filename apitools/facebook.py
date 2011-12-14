import urllib, urllib2, json
from onlyinpgh.apitools import APIError

class FacebookAPIError(APIError):
    # TODO: decide on error contents. complicated because there's a variety of responses this API handles
    def __init__(self,request,*args,**kwargs):
        self.request = request
        super(FacebookAPIError,self).__init__('facebook-graph',*args,**kwargs)    

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

class BatchCommand(object):
    '''
    Stores a single GET command to be used in a batch operation.
    e.g. BatchCommand('cocacola/events', {limit: 10}) will create a command 
            that returns details of 10 events owned by Coca Cola.
    
    See https://developers.facebook.com/docs/reference/api/batch/ for
    details about using the "name" parameter for commands with dependencies
    with other commands.
    '''

    def __init__(self,url,options={},name=None,omit_response_on_success=True):
        self.url = url
        self.options = options
        self.name = name
        # only useful if name is specified
        self.omit_response_on_success = omit_response_on_success    
    
    def __unicode__(self):
        return unicode(dict(url=self.url,options=self.options,name=self.name))

    def to_command_dict(self):
        command = { 'method':       'GET',
                    'relative_url': self.url }
        if self.options:
            command['relative_url'] += '?' + urllib.urlencode(self.options)
        if self.name:
            command['name'] = self.name
            command['omit_response_on_success'] = self.omit_response_on_success
        return command


class GraphAPIClient(object):
    def __init__(self,access_token=None):
        self.access_token = access_token

    def graph_api_objects(self,ids):
        '''
        Returns details about objects with known Facebook ids. Input
        is a list of ids (numbers or strings OK), output is a parallel
        list of response dicts.

        A single string/value can be input without a list for convenience's 
        sake. In this case, the single result will be returned in isolation 
        (not in a list).
        '''
        return_list = True
        # duck typing fun to handle single id case
        if isinstance(ids,basestring):
            ids = [ids]
            return_list = False
        try:
            ids = [str(id) for id in ids]
        except TypeError:   # if the input was a number
            ids = [str(ids)]
            return_list = False

        get_opts = { 'ids': ','.join(ids) }
        if self.access_token:
            get_opts['access_token'] = self.access_token
        
        request_url = 'https://graph.facebook.com/?' + urllib.urlencode(get_opts)

        response = json.load(urllib.urlopen(request_url))
        if not response or 'error' in response:
            raise Exception('Graph API returned error. Content:\n%s' % str(response))    
        
        # return sorted list based on the input id ordering
        responses = [response[id] for id in ids]
        if return_list:
            return responses
        elif len(responses) > 1:
            raise Exception('Internal error: More than one response returned to single object query.')
        else:
            return responses[0]

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
                err = response['error']
                raise FacebookAPIError(
                            request=request_url,
                            message='%s: %s' % (str(err['type']),str(err['message']))
                        )
            if 'data' not in response:
                raise FacebookAPIError(
                            request=request_url,
                            message='%s' % str(response))
            
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

    def run_batch_request(self,batch_commands,process_response=True):
        '''
        Runs a batch of GET calls. Argument should be a list of BatchCommand
        objects. All commands are run relative to https://graph.facebook.com/

        If process_response is True (default), a list of response dicts
        parsed out from the "body" elements of the full response will be
        returned. Otherwise, the bare full response (with status codes and 
        headers) will be directly returned.
        
        See https://developers.facebook.com/docs/reference/api/batch/
        for more details on the format of this responses.
        '''
        command_dicts = [cmd.to_command_dict() for cmd in batch_commands]
        data = {'batch': json.dumps(command_dicts)}
        if self.access_token:
            data['access_token'] = self.access_token
        
        req = urllib2.Request(url='https://graph.facebook.com/',data=urllib.urlencode(data))
        response = json.load(urllib2.urlopen(req))

        if process_response:
            return [json.loads(entry['body']) if entry else None
                        for entry in response]
        else:
            return response

# onlyinpgh.com app credentials
OIP_APP_ID = '203898346321665'
OIP_APP_SECRET = '897ca9d744d43da15d40d3f793f112e3'
# if this stops working, try calling get_basic_access_token directly
OIP_ACCESS_TOKEN = '203898346321665|e_aVTLcJCsV3c9tiQJn0tZjWcZg'

# a default GraphAPIClient that uses OIP's credentials
oip_client = GraphAPIClient(OIP_ACCESS_TOKEN)