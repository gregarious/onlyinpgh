import urllib2
from urlparse import urlparse, parse_qsl

from onlyinpgh.apitools import oauth

class APIError(Exception):
    def __init__(self,api_name,*args,**kwargs):
        super(APIError,self).__init__(*args,**kwargs)

def build_oauth_request(url,key,secret):
    '''
    Returns an oauth signed urllib2.Request object
    '''
    params    = parse_qsl(urlparse(url).query)
    consumer  = oauth.OAuthConsumer(key=key, secret=secret)
    request   = oauth.OAuthRequest.from_consumer_and_token(consumer, http_method='GET', http_url=url, parameters=params)

    request.sign_request(oauth.OAuthSignatureMethod_HMAC_SHA1(), consumer, None)

    return urllib2.Request(url, None, request.to_header())
