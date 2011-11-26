import urllib, re, json
from datetime import datetime
from copy import deepcopy

from places.models import Location, LocationLookupNotice

API_NOTICE_TYPES = ('PartialMatch','MultipleResults','NoStreetAddress',
                    'NonConcreteAddress','PreprocessingOccurred','LookupFailure')

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

    def run_text_query(self,address,bounds=None,region='US',sensor=False):
        '''
        Calls the Google Geocoding API with given text query and returns a 
        GGResponse

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
    
    def run_location_query(self,location,bounds=None,region=None,sensor=False):
        '''
        Calls the Google Geocoding API with a text query based on the fields
        in the given location. Note that region is not given 'US' as a default
        since many Location objects will have region expliclty provided.

        If bounds or region is given as a function argument, lat/longitude or 
        country, respectively, from the Location will be ignored.

        Rest of behavior is same as run_text_query
        '''
        LAT_BUFFER, LONG_BUFFER = 0.005, 0.005
        address_str = ''
        state = location.state
        if location.postcode:
            state += ' ' + location.postcode
        nbrhd = location.neighborhood.name if location.neighborhood else ''

        fields = [location.address, nbrhd, location.town, state]
        address_str = ', '.join( [field for field in [location.address, nbrhd, location.town, state] 
                                 if field != '' ])
        
        if bounds is None:
            if location.latitude is not None and location.longitude is not None:
                bounds = ( (location.latitude-LAT_BUFFER, location.longitude-LONG_BUFFER),
                           (location.latitude+LAT_BUFFER, location.longitude+LONG_BUFFER))

        if region is None:
            region = location.country

        return self.run_text_query(address_str,bounds=bounds,region=region,sensor=sensor)

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
        '''
        Returns the best result. Will be None if no results exist.
        '''
        if len(self.results) > 0:
            return self.results[0]
        else:
            return None

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

    def get_address_component(self,component_name,default=None,allow_multiple=False):
        '''
        Shortcut to returning the named address component. Returns the 
        "short_name" version of the component. If default argument given,
        this value will be returned if no components match the name.

        If allow_multiple is False, a single string will be returned and
        a KeyError will be thrown if the component occurs either zero or 
        multiple times.

        If allow_multiple is True, a list of strings will be returned that
        include all occurrances of the component type. 

        Note that default will NEVER be returned when allow_multiple is 
        True: in this case an empty list will be returned.
        '''
        matches = [comp for comp in self._result['address_components'] if component_name in comp['types']]
        if allow_multiple:
            return [comp['short_name'] for comp in matches]
        else:
            if len(matches) == 1:
                return matches[0]['short_name']
            elif len(matches) == 0:
                return default
            elif len(matches) > 1:
                raise KeyError("%s is not a unique component" % component_name)

    def contains_notice(self,notice_type):
        '''
        Returns true if the given notice type is present in the notices
        '''
        return notice_type in [n.notice_type for n in self.notices]

    ### methods to return normalized Location components

    # TODO: optmize a bit? doing a ton of repetitive linear searches inthe multiple get_address_components
    def get_address(self,default=None):
        '''
        Returns the normalized "address" component for a Location representation
        '''            
        named_address_types = list(GG_PREMISE_TYPES)
        named_address_types.remove('premise')   # we want to consider premises seperately from the rest of the named types
        named_components = [ comp for comp in [ self.get_address_component(t) for t in named_address_types ] 
                                if comp is not None ]
        named_component = named_components[0] if len(named_components) > 0 else None
        premise = self.get_address_component('premise',None)
        subpremise = self.get_address_component('subpremise',None)
        intersection = self.get_address_component('intersection',None)
        street_number = self.get_address_component('street_number',None)
        route = self.get_address_component('route',None)

        # normalizing scheme:
        # if a named component exists, printing it
        # if a premise exists, print it next. if subpremise exists, print it too now
        # if a route exists, print it
        # otherwise if a route exists, print it (proceeded by the street number)
        # finally, if the subpremise hasn't been printed yet, print it last
        address = ''
        if named_component is not None:
            address += named_component + ', '
        if premise is not None:
            address += premise + \
                        ((' #' + subpremise) if subpremise is not None else '') + \
                        ','
        if intersection is not None:
            address += intersection
        elif route is not None:
            if street_number is not None:
                address += street_number + ' '
            address += route
        
        if premise is None:
            if subpremise is not None:
                address += ' #' + subpremise

        return address.rstrip(', ')

    def get_postalcode(self,default=None):
        '''
        Returns the postal code component for a Location representation
        '''
        return self.get_address_component('postal_code',default)

    # TODO
    def get_neighborhood(self,default=None):
        '''
        Returns a string representation of the neighborhood for a Location 
        representation
        '''
        raise NotImplementedError

    def get_town(self,default=None):
        '''
        Returns the town component for a Location representation
        '''
        return self.get_address_component('locality',default)

    def get_state(self,default=None):
        '''
        Returns the state component for a Location representation
        '''
        return self.get_address_component('administrative_area_level_1',default)
        
    def get_country(self,default=None):
        '''
        Returns the country component for a Location representation
        '''
        return self.get_address_component('country',default)

    def get_geocoding(self,default=None):
        '''
        Returns the longitude and latitude components as a 2-tuple for a 
        Location representation.

        Returns (None,None) if geocoding result is not available.
        '''
        try:
            geocoding = self._result['geometry']['location']
        except KeyError:
            return None
        return (geocoding['lat'],geocoding['lng'])
    
    # TODO: add neighborhood
    def to_location(self):
        geocode = self.get_geocoding()
        return Location(
            address = self.get_address(),
            postcode = self.get_postalcode(),
            town = self.get_town(),
            state = self.get_state(),
            country = self.get_country(),
            latitude = geocode[0],
            longitude = geocode[1]
            )

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

class LocationValidator(object):
    SUPPORTED_APIS = ('GG',)
    def __init__(self,api):
        if api == 'GG':
            self.api_agent = GGAgent()
        else:
            raise Exception('Given api is not in the supported list.')

    def resolve_full(self,seed_location):
        '''
        Returns a Location with as many fields filled in as possible using 
        the input Location as a seed.
        '''
        
        result = self.api_agent.run_location_query(seed_location).best_result()
        if result is None:
            return None
        # TODO: decide how to process notices. probably not fail on non concrete for resolve?
        # TODO: also consider creating new notices here
        if result.contains_notice('NonConcreteAddress'):
            raise LocationValidationError('Non-concrete address generated from seed %s' % unicode(seed_location))
        return result.to_location()
    
    def normalize_address(self,seed):
        '''
        Returns a string that normalizes the given seed address.

        seed can be either:
        - a text address (with at least street info)
        - a Location object. If a Location is provided, the query will be 
            biased using the other available information.
            '''
        if isinstance(seed,Location):
            response = self.api_agent.run_location_query(seed)
        else:
            response = self.api_agent.run_text_query(seed)
        result = response.best_result()
        # TODO: decide how to process notices
        # TODO: also consider creating new notices here
        if result.contains_notice('NonConcreteAddress'):
            raise LocationValidationError('Non-concrete address generated from seed %s' % unicode(seed))
        return result.get_address()
        

class APIFailureError(Exception):
    pass

class LocationValidationError(Exception):
    pass

# probably move this into models or some other class
class AddressNormalizer(object):
    # undocumented location "types" that we've seen. kept track of because
    # it's possible some types could be useful in creating normalized 
    # addresses
    KNOWN_GOOGLE_LOCATION_TYPES = ['university']
