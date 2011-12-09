import json, re, urllib, os
from onlyinpgh.apitools import APIError

class GoogleGeocodingAPIError(APIError):
    def __init__(self,request,response,*args,**kwargs):
        self.request = request
        self.response = response
        super(GoogleGeocodingAPIError,self).__init__('google-geocoding',*args,**kwargs)    

class GoogleGeocodingClient(object):
    '''
    Wrapper around Google Geocoding API call that handles some limited
    input preprocessing and generates notices for any API responses that
    have some red flags.
    '''
    GOOGLE_BASE_URL = "http://maps.googleapis.com/maps/api/geocode/json"
    @classmethod
    def run_geocode_request(cls,query,bounds=None,region='US',sensor=False):
        '''
        Calls the Google Geocoding API with given text query and returns a 
        GoogleGeocodingResponse.

        query should be a raw string (not urlencoded).
        bounds should be a pair of (lat,long) pairs for the upper left and 
            lower right corner of the bounding rect

        Will pass on errors of urllib.urlopen if the API's URL has trouble
        connecting.
        '''
        cleaned_address = cls._preprocess_address(query)
        options = { 'address': cleaned_address,
                    'sensor': 'true' if sensor else 'false' }
        if bounds is not None:
            options['bounds'] = '%f,%f|%f,%f' % ( bounds[0][0], bounds[0][1], 
                                                  bounds[1][0], bounds[1][1] ) 
        if region is not None:
            options['region'] = region
        
        request_url = cls.GOOGLE_BASE_URL + '?' + urllib.urlencode(options)
        fp = urllib.urlopen(request_url)
        raw_response = fp.read()
        return cls._package_response(raw_response,request_url)
    
    @classmethod
    def _package_response(cls,raw_response,request=None):
        response = GoogleGeocodingResponse(raw_response)
        if response.status in ['OVER_QUERY_LIMIT','REQUEST_DENIED','INVALID_REQUEST']:
            raise GoogleGeocodingAPIError(request,raw_response)
        return response

    @classmethod
    def _preprocess_address(cls,address):
        '''
        Special preprocessing for address text based on known 'quirks' of API

        Currently does the following:
            1. Translates pound signs (#) to "Unit ". Despite returning 
                formatted addresses with the pound sign, the API doesn't like 
                requests that use it
            2. Removes parenthesized content
        '''
        cleaned = address.replace('#','Unit ')
        cleaned = re.sub(r'\([^)]*\)', '',cleaned)
        return cleaned

class GoogleGeocodingResponse(object):
    '''
    Wrapper around response from Google Geocoding API. Contains two primary
    fields: status and results. See 
    http://code.google.com/apis/maps/documentation/geocoding/#GeocodingResponses
    for details. 

    Also refer to doc for _postprocess_result, which can modify the result 
    from what is listed in Google documentation.

    Results list will be empty for all responses except those with 'OK' 
    status.
    '''
    def __init__(self,response,request='unavailable'):
        '''response can be string or file-like object'''
        try:
            # see if it's a file-like object
            self._full_response = json.load(response)
        except AttributeError:
            # assume it's a string
            self._full_response = json.loads(response)

        self.status = self._full_response['status']
        self.results = [self._postprocess_result(res) for res in self._full_response['results']]

    def _postprocess_result(self,result):
        '''
        Do any post-response massaging on a given result.

        Currently goes the following:
        - Adds 'intersection' address_component if result represents an intersection
        '''
        # if type is intersection, the full intersection name won't be in the address_components. remedy this.
        if 'intersection' in result['types']:
            try:
                route = [comp['short_name'] for comp in result['address_components'] if 'route' in comp['types']][0]
            except IndexError:
                # TODO: more specific error
                raise Exception("Unexpected Google Geocoding API Response. No 'route' for 'intersection' result")
            pattern = r'(%s.+?)\,' % route
            match = re.search(pattern,result['formatted_address'])
            if not match:
                # TODO: more specific error
                raise Exception("Unexpected Google Geocoding API Response. 'route' not contained in 'formatted_address'")
            
            # add the full intersection name to the result's address components 
            result['address_components'].insert(0,
                {'types':['intersection'],'short_name':match.group(1),'long_name':match.group(1)})
        return result

    def best_result(self,wrapped=False):
        '''
        Returns best result. If no results exist, None is returned.

        If wrapped is True, result will be returned wrapped in a 
        GoogleGeocodingResult object.
        '''
        if len(self.results) > 0:
            if wrapped:
                return GoogleGeocodingResult(self.results[0])
            return self.results[0]
        else:
            return None

    def wrapped_results(self):
        '''
        Return the results list with each one wrapped in a 
        GoogleGeocodingResult.
        '''
        return [GoogleGeocodingResponse.wrap_result(r) for r in self._result]

    @classmethod
    def wrap_result(cls,result):
        return GoogleGeocodingResult(result)
    
PREMISE_TYPES = ('premise','establishment','point_of_interest','natural_feature','airport','park')
class GoogleGeocodingResult(object):
    '''
    Wrapper around a single result from a Google Geocoding response
    that makes it simpler to access particular address components 
    directly.

    Fields can be accessed directly with dict-like access, named address
    components can be accessed with get_address_component.
    '''
    def __init__(self,result):
        '''result is a dict of a single set of response result data'''
        self._result = result

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

    def get_street_address(self,default=None):
        '''
        Returns the normalized "address" component for a Location representation
        '''
        named_address_types = list(PREMISE_TYPES)
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
        Returns the postal code component
        '''
        return self.get_address_component('postal_code',default)

    def get_neighborhood(self,default=None):
        '''
        Returns the neighborhood component. 

        Note, these neighborhoods are not necessarily those defined for the
        places.models.Neighborhood model.
        '''
        return self.get_address_component('postal_code',default)

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
    