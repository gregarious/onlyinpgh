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

def delayed_retry_on_ioerror(apicall,delay_seconds,retry_limit=1,logger=None):
    '''
    Function designed to automatically reattempt a function call on the
    event that it returns an IOError. Each reattempt is preceded by a
    sleep count. 

    This is a convenient way to avoid the common pattern of causing a 
    delayed-retry when an API service denies access momentarily because
    of throttling concerns.
    '''
    retry_count = 0
    while True:
        try:
            return apicall()
        except IOError as e:
            # we're out of retries -- just raise the error
            if retry_count >= retry_limit:
                raise
            retry_count += 1
            if logger:
                logger.warning('IOError "%s": Will attempt retry %d (of %d max) in %d secs...' %\
                    (str(e),
                    retry_count,
                    retry_limit,
                    delay_seconds))
            
