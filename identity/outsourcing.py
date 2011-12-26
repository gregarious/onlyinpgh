from onlyinpgh.apitools import facebook
from onlyinpgh.identity.models import Organization, FacebookPageRecord

import logging
dbglog = logging.getLogger('onlyinpgh.debugging')

def store_fbpage_organization(page_info):
    '''
    Takes a dict of properties retreived from a Facebook Graph API call for
    a page and stores an Organization from the information. This dict can
    have the following keys:
    - id
    - type (value must be 'page' or a TypeError will be thrown)
    - name
    - website (optional)
    - picture (optional)

    If a FacebookPageRecord already exists for the given Facebook id, the already 
    linked organization is returned.
    '''
    pid = page_info['id']

    if page_info.get('type') != 'page':
        raise TypeError("Cannot store fbpage with a 'type' value that is not 'page'.")

    try:
        organization = FacebookPageRecord.objects.get(fb_id=pid).organization
        dbglog.info('Existing fb page organization found for fbid %s' % str(pid))
        return organization
    except FacebookPageRecord.DoesNotExist:
        pass

    pname = page_info['name'].strip()

    try:
        # url field can be pretty free-formed and list multiple urls. 
        # we take the first one (identified by whitespace parsing)
        url = page_info.get('website','').split()[0].strip()[:400]
    except IndexError:
        # otherwise, go with the fb link (and manually create it if even that fails)
        url = page_info.get('link','http://www.facebook.com/%s'%pid)
    organization = Organization.objects.get_or_create(name=pname,
                                                        avatar=page_info.get('picture',''),
                                                        url=url)
    organization.save()
    
    record = FacebookPageRecord.objects.create(fb_id=pid,organization=organization)
    dbglog.info(u'Stored new Organization for fbid %s: "%s"' % (pid,unicode(organization)))

    if len(pname) == 0:
        logging.warning('Facebook page with no name was stored as Organization')

    return organization

def create_org_from_fbpage(page_id):
    page_info = facebook.oip_client.graph_api_page_request(page_id)
    store_fbpage_organization(page_info)