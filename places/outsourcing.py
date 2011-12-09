'''
Module containing utilities that use external APIs to perform 
places-related tasks.
'''

from onlyinpgh.apitools.google import GoogleGeocodingClient
from onlyinpgh.apitools.factual import FactualClient

def resolve_place(partial_place=None,partial_location=None):
    '''
    Resolves a partial Place or Location object into a complete Place 
    using the Factual Resolve API. Returns None if resolution was not 
    possible.

    Exactly one of the arguments must be provided.
    '''
    # run a straightforward factual query on Place/Location.
    raise NotImplementedError

def resolve_location(partial_location):
    '''
    Resolves a partial Location object into a complete one using the Google
    Geocoding API. Useful for fleshing out non-named locations not in Factual's
    Places database.

    Also useful for normalizing street addresses contained in Location objects.

    Returns None if resolution was not possible.
    '''
    raise NotImplementedError

# can be a little more creative with address_text. Try simple
    # query with name, maybe try address, splitting by comma, extracting
    # zip, etc.

def text_to_place(address_text,seed_location=None):
    '''
    Attempts to resolve a raw text string into a Place using the Factual
    Resolve API. 

    If Location object is provided as seed_location Location, the completed
    fields from it are used as hints to help resolving. Note that if any of
    these "hints" are erroneous, resolution may fail since the Resolve API
    is fairly strict.

    Returns None if resolution was not possible. Can raise APIError if 
    critical error occurs.
    '''
    raise NotImplementedError

def text_to_location(address_text,seed_location=None):
    '''
    Attempts to resolve a raw text string into a Location using the Google
    Geocoding API.

    If Location object is provided as seed_location Location, the completed
    fields from it are used as hints to help resolving. These hints are more
    forgiving than those used in the Resolve API.

    Returns None if resolution was not possible.
    '''
    raise NotImplementedError

def normalize_street_address(address_text):
    '''
    Given a free-formed address in a string, returns the normalized street
    address portion of a result obtained by Google Geocoding API.

    Including additional address information (e.g. city, zip code) is useful
    for the API query, but will the information will not be included in
    the result.

    Returns None if normalization was not possible.
    '''
    raise NotImplementedError    

# TODO: consider geocoding notice handling here