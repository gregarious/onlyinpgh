'''
Module containing code to manage "outsourcing" tasks related to identity 
models. i.e. Organization pulling from Facebook.
'''
from onlyinpgh.outsourcing.apitools import facebook
from onlyinpgh.identity.models import Organization
from onlyinpgh.outsourcing.models import FacebookOrgRecord

import logging
dbglog = logging.getLogger('onlyinpgh.debugging')\

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

    If a FacebookOrgRecord already exists for the given Facebook id, the 
    already linked organization is returned. An INFO message is logged to 
    note the attempt to store an existing page.
    '''
    pid = page_info['id']

    if page_info.get('type') != 'page':
        raise TypeError("Cannot store fbpage with a 'type' value that is not 'page'.")

    try:
        organization = FacebookOrgRecord.objects.get(page_fbid=pid).organization
        dbglog.info('Existing fb page organization found for fbid %s' % str(pid))
        return organization
    except FacebookOrgRecord.DoesNotExist:
        pass

    pname = page_info['name'].strip()

    try:
        # url field can be pretty free-formed and list multiple urls. 
        # we take the first one (identified by whitespace parsing)
        url = page_info.get('website','').split()[0].strip()[:400]
    except IndexError:
        # otherwise, go with the fb link (and manually create it if even that fails)
        url = page_info.get('link','http://www.facebook.com/%s'%pid)
    organization, created = Organization.objects.get_or_create(name=pname,
                                                                avatar=page_info.get('picture',''),
                                                                url=url)

    if not created:
        dbglog.notice('An organization matching fbid %s already existed with '\
                        'no FacebookOrgRecord. The record was created.' % str(pid))
    
    record = FacebookOrgRecord.objects.create(page_fbid=pid,organization=organization)
    dbglog.info(u'Stored new Organization for fbid %s: "%s"' % (pid,unicode(organization)))

    if len(pname) == 0:
        logging.warning('Facebook page with no name was stored as Organization')

    return organization

def create_org_from_fbpage(page_id):
    page_info = facebook.oip_client.graph_api_page_request(page_id)
    store_fbpage_organization(page_info)