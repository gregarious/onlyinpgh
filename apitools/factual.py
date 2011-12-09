# create Resolver class that has ability to create hints for fields (e.g. feed 
#   reader would use it with city fixed in Pgh)

from onlyinpgh.apitools import APIError

class FactualAPIError(APIError):
    def __init__(self,request,error_type,message,*args,**kwargs):
        self.request = request
        self.error_type = error_type
        self.message = message
        super(FactualAPIError,self).__init__('factual',*args,**kwargs)    

class FactualClient(object):
    def __init__(self,oauth_key,oauth_secret):
        self.key = oauth_key
        self.secret = oauth_secret
    
    def resolve(self,name=None,address=None,city=None,state=None,postcode=None,
                phone=None,latitude=None,longitude=None):
        # form request
        request = None
        # get raw response via API call 
        response = ResolveResponse(raw_response)
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

        self.version = None
        self.status = None
        self.responses = None   # list of resolve_result arrays
        self.error_type = None
        self.message = None

        # TODO: insert response parsing
        # hack the resolved status to false if more two different addresses
        # have 1 responses
    
    def successful(self):
        '''Returns True if response status was "ok"'''
        return self.status == 'ok'

    def get_resolved_result(self):
        '''
        Returns a dict containing place components as well as 
        resolve-specific "similarity" and "resolved" fields.
        '''
        return {}

    def get_all_results(self):
        '''
        Returns a list of dicts containing place components as well as 
        resolve-specific "similarity" and "resolved" fields. List is 
        ordered same as response JSON.
        '''
        return []

OIP_OAUTH_KEY = 'sJqNeJAzOeBwmIpdubcyguqAxG8OVqQ65Pu7lUxj'
OIP_OAUTH_SECRET = 'QQUO9RjZOETZVjRRV8uYrmaaSMs2ulNDb7mALus8'

oip_client = FactualClient(OIP_OAUTH_KEY,OIP_OAUTH_SECRET)