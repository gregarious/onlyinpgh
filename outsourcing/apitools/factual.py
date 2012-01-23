# create Resolver class that has ability to create hints for fields (e.g. feed 
#   reader would use it with city fixed in Pgh)

from onlyinpgh.outsourcing.apitools import APIError
from onlyinpgh.outsourcing.apitools import build_oauth_request, delayed_retry_on_ioerror

import urllib, urllib2, json, time
import logging

outsourcing_log = logging.getLogger('onlyinpgh.outsourcing')

class FactualAPIError(APIError):
    def __init__(self,request,error_type,message,*args,**kwargs):
        self.request = request
        self.error_type = error_type
        self.message = message
        super(FactualAPIError,self).__init__('factual',*args,**kwargs)    

class FactualClient(object):
    RESOLVE_URL = "http://api.v3.factual.com/places/resolve"
    def __init__(self,oauth_key,oauth_secret):
        self.key = oauth_key
        self.secret = oauth_secret
    
    def resolve(self,name=None,address=None,town=None,state=None,postcode=None,
                latitude=None,longitude=None):
        '''
        Runs a Factual Resolve API call with the given search options and 
        returns a ResolveResponse object. Will raise a FactualAPIError if
        response returns a non-OK status.
        '''
        query_opts = dict(
            name = name,
            address = address,
            locality = town,
            region = state,
            postcode = postcode,
            latitude = latitude,
            longitude = longitude,
        )

        # make a JSON version with all None valued-parameters stripped out
        json_query = json.dumps( {key:val for key,val in query_opts.items() if val is not None} )

        full_url = FactualClient.RESOLVE_URL + '?' + urllib.urlencode({'values':json_query})
        request = build_oauth_request(full_url,self.key,self.secret)

        response = delayed_retry_on_ioerror(lambda:ResolveResponse(urllib2.urlopen(request)),
                                            5,5,outsourcing_log)

        if response.status != 'ok':
            raise FactualAPIError(request,response.error_type,response.message)
        return response

class ResolveResponse(object):
    '''
    Object representation of a response received from the Resolve API

    See http://developer.factual.com/display/docs/Places+API+-+Resolve 
    for details.
    '''
    def __init__(self,response):
        '''response can be string or file-like object'''
        try:
            # see if it's a file-like object
            response_text = response.read()
        except AttributeError:
            # assume it's a string
            response_text = response

        self.version, self.status, self.error_type, self.message = None, None, None, None
        try:
            response = json.loads(response_text)
            self.version = response['version']
            self.status = response['status']
            self.error_type = response.get('error_type',None)
            self.message = response.get('message',None)
            data = response['response']['data']
        except ValueError:      # result for 02053b6a-a96b-42b4-99dd-8e865d029e2e had some bad json?
            self.results = None
        except KeyError:
            self.results = None
        else:
            # Not sure if it's a beta glitch or what, but Resolve will sometimes return
            # multiple results with similarity of 1 and yet mark the first result's
            # "resolved" status is True. This seems counter to the philosophy of the
            # Resolve API, so we're hacking the resolved status to False for now.
            if len([1 for result in data if result['similarity']==1]) > 1:
                data[0]['resolved'] = False
            self.results = data

    def get_resolved_result(self):
        '''
        Returns the one and only "resolved" result, if it exists. Return 
        False if it doesnt. Return value is a dict containing place 
        components as well as resolve-specific "similarity" and "resolved"
        fields.
        '''
        if len(self.results) == 0 or not self.results[0]['resolved']:
            return None
        return self.results[0]

OIP_OAUTH_KEY = 'sJqNeJAzOeBwmIpdubcyguqAxG8OVqQ65Pu7lUxj'
OIP_OAUTH_SECRET = 'QQUO9RjZOETZVjRRV8uYrmaaSMs2ulNDb7mALus8'