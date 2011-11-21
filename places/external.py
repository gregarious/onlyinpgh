import urllib, re, json
from datetime import datetime
from copy import deepcopy

from places.models import LocationLookupNotice

'''
Manages external API calls for place/location verification
'''
class GGAgent(object):
    '''
    Wrapper around Google Geocoding API call that handles some limited
    input preprocessing and generates notices for any API responses that
    have some red flags.
    '''
    GOOGLE_BASE_URL = "http://maps.googleapis.com/maps/api/geocode/json"
    def __init__(self):
        self.notice_stub = None

    def run_query(self,address,bounds=None,region='us',sensor=False):
        '''
        Calls the Google Geocoding API and return a GGResponse

        address should be a raw string (not urlencoded).
        bounds should be a pair of (lat,long) pairs for the upper left and 
            lower right corner of the bounding rect

        Will pass on errors of urllib.urlopen if the API's URL has trouble
        connecting.
        '''
        cleaned_address = self.preprocess_address(address)
        options = { 'address': cleaned_address,
                    'sensor': 'true' if sensor else 'false' }
        if bounds is not None:
            options['bounds'] = '%f,%f|%f,%f' % ( bounds[0][0], bounds[0][1], 
                                                  bounds[1][0], bounds[1][1] ) 
        if region is not None:
            options['region'] = region
        
        url = self.GOOGLE_BASE_URL + '?' + urllib.urlencode(options)

        fp = urllib.urlopen(url)
        response_json = fp.read()
        response_dict = json.loads(response_json)

        self.notice_stub = LocationLookupNotice(dtlookup=datetime.utcnow(),
                                                service='GoogleGeocode',
                                                raw_request=address,
                                                cleaned_request=cleaned_address,
                                                api_call=url,
                                                response_json=response_json)

        return GGResponse(response_dict,self.notice_stub)
    
    def preprocess_address(self,address):
        '''
        Special preprocessing based on known 'quirks' of API

        Currently does the following:
            1. Translates pound signs (#) to "Unit ". Despite returning 
                formatted addresses with the pound sign, the API doesn't like 
                requests that use it
            2. Removes parenthesized content
        '''
        cleaned = address.replace('#','Unit ')
        cleaned = re.sub(r'\([^)]*\)', '',cleaned)
        return cleaned

GG_PREMISE_TYPES = ('premise','establishment','point_of_interest','natural_feature','airport','park')
class GGResponse(object):
    def __init__(self,response,notice_stub=None):
        '''
        Process the raw response in Python dict format.

        notice_stub should be an incomplete LocationLookupNotice object that
        supplies all the information but the notice_type. This is to be used 
        for any notices that may need to be generated based on response content.
        '''
        # fail right away if bad status is returned
        if response['status'] in ['OVER_QUERY_LIMIT','REQUEST_DENIED','INVALID_REQUEST']:
            raise APIFailureError("API response status: '%s'" % response['status'])

        try:
            self._raw_results = response['results']
            self._notice_stub = notice_stub

            self.status = response['status']
            self.results = [self._package_result(r) for r in self._raw_results]
        except KeyError as e:
            raise APIFailureError("Unexpected Google Geocoding API response. No key '%s' in json." % e.message)

    def _package_result(self,result):
        self._postprocess_result(result)
        if self._notice_stub is not None:
            notices = self._process_notices(result)
        else:
            notices = None
        return GGResult(result,notices)

    def _postprocess_result(self,result):
        # if type is intersection, the full intersection name won't be in the address_components. remedy this.
        if 'intersection' in result['types']:
            try:
                route = [comp['short_name'] for comp in result['address_components'] if 'route' in comp['types']][0]
            except IndexError:
                raise APIFailureError("Unexpected Google Geocoding API Response. No 'route' for 'intersection' result")
            pattern = r'(%s.+?)\,' % route
            match = re.search(pattern,result['formatted_address'])
            if not match:
                raise APIFailureError("Unexpected Google Geocoding API Response. 'route' not contained in 'formatted_address'")
            
            # add the full intersection name to the result's address components 
            result['address_components'].insert(0,
                {'types':['intersection'],'short_name':match.group(1),'long_name':match.group(1)})
    
    def _process_notices(self,result):
        # TODO: might want to refactor this notice_stub system. Storing these stubs, passing them around and the 
        #       duplication of all data but an enum in each notice just seems a bit off.
        notices = []
        # MultipleResults: when call returned more than one result
        if len(self._raw_results) > 1:
            self._append_notice(notices,'MultipleResults')

        # PartialMatch: when the partial_match flag is set in the result
        if result.get('partial_match',False):
            self._append_notice(notices,'PartialMatch')

        # gather all component types to see how specific the result is
        all_component_types = []
        for comp in result['address_components']:
            all_component_types.extend(comp['types'])
        
        # if no street address or intersection is given
        if not ('intersection' in all_component_types or
                ('route' in all_component_types and 
                 'street_number' in all_component_types)):
            # could be one of two notices:
            #   NonConcreteAddress: when the address is unmappable
            #   NoStreetAddress: when no street address is given, but there is a named landmark
            if len(set(GG_PREMISE_TYPES).intersection(all_component_types)) == 0:
                self._append_notice(notices,'NonConcreteAddress')
            else:
                self._append_notice(notices,'NoStreetAddress')

        # PreprocessingOccurred: when the cleanred request doesn't match the original one
        if self._notice_stub.raw_request != self._notice_stub.cleaned_request:
            self._append_notice(notices,'PreprocessingOccurred')
        return notices
        
    def _append_notice(self,notice_list,notice_type):
        notice = deepcopy(self._notice_stub)
        notice.notice_type = notice_type
        notice_list.append(notice)

    def best_result(self):
        return self.results[0]

class GGResult(object):
    '''
    A single result entry from a Google Geocoding response. Has dict-like
    address to the result for getitem, iter, and contains methods.
    '''
    def __init__(self,result_dict,notices=None):
        '''
        notices is a list of APILookupNotice objects.
        '''
        self._result = result_dict
        self._notices = notices

    @property
    def notices(self):
        if self._notices is None:
            raise APIFailureError('GGResult was not constructed with notices!')
        return self._notices
    
    def __getitem__(self,key):
        return self._result.__getitem__(key)

    def __iter__(self):
        return self._result.__iter__()

    def __contains__(self):
        return self._result.__contains__(key)

    def get_address_component(self,component_name,allow_multiple=False):
        '''
        Shortcut to returning the named address component. Returns the 
        "short_name" version of the component.

        If allow_multiple is False, a single string will be returned and
        a KeyError will be thrown if the component occurs either zero or 
        multiple times.

        If allow_multiple is True, a list of strings will be returned that
        include all occurrances of the component type.
        '''
        matches = [comp for comp in self._result['address_components'] if component_name in comp['types']]
        if allow_multiple:
            return [comp['short_name'] for comp in matches]
        else:
            if len(matches) == 1:
                return matches[0]['short_name']
            elif len(matches) == 0:
                raise KeyError(component_name)
            elif len(matches) > 1:
                raise KeyError("%s is not a unique component" % component_name)

    def contains_notice(self,notice_type):
        '''
        Returns true if the given notice type is present in the notices
        '''
        return notice_type in [n.notice_type for n in self.notices]

# maybe useful for refactoring
#class APIResultInfo(object):
#    def __init__(self,dt,request,cleaned_request,api_call_text,response_json):
#        self.dt = dt
#        self.raw_request = request_text
#        self.cleaned_request = cleaned_request
#        self.api_call = api_call_text
#        self.response_json = response_json
#        self.notice_types = []  # elements should be among LocationLookupNotice.NOTICE_TYPES
#    
#    def add_notice_type(self,nt):
#        self.notice_types.append(nt)
#
#    def contains_notices(self)

    # def save_to_model(service,location=None):
    #     '''
    #     Save the given 
    #     '''
    #     if len(notice_types) == 0:
    #         raise Exception('No notices to save')
        



class APIFailureError(Exception):
    pass

# probably move this into models or some other class
class AddressNormalizer(object):
    # undocumented location "types" that we've seen. kept track of because
    # it's possible some types could be useful in creating normalized 
    # addresses
    KNOWN_GOOGLE_LOCATION_TYPES = ['university']
