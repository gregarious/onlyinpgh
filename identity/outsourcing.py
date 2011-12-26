from onlyinpgh.apitools import facebook

from onlyinpgh.identity.models import Organization, FacebookPageRecord


import logging
dbglog = logging.getLogger('onlyinpgh.debugging')

# TODO: revisit page cache thing
def page_id_to_organization(page_id,create_new=True,page_cache={}):
    '''
    Takes a fb page ID and tries to resolve an Organization object 
    from it. First queries the FacebookPageRecord table. If that fails, 
    and create_new is True, it will try to create a new one and return 
    that.

    If page information has been loaded at a prior time for a group of 
    pages, the page_cache argument can be used (dict of ids to page 
    details).

    Returns None if no Organization could be retreived.
    '''
    try:
        organization = FacebookPageRecord.objects.get(fb_id=page_id).organization
        dbglog.info('found existing organization for fbid %s'%page_id)
    except FacebookPageRecord.DoesNotExist:
        organization = None
    
    # we return if we either found a record, or didn't but can't create
    if organization or not create_new:
        return organization

    dbglog.info('gathering data for creating org with fbid %s' % page_id)
    if page_id in page_cache:
        page = page_cache[page_id]
        dbglog.debug('retreiving page info from cache')
    else:
        try:
            dbglog.debug('retreiving page info from facebook')
            page = facebook.oip_client.graph_api_objects(page_id)

        except facebook.FacebookAPIError as e:
            dbglog.error('Facebook error occured!')
            dbglog.error(str(e))
            return None

    pname = page['name'].strip()

    # TODO: temp because of idiotic page http://graph.facebook.com/104712989579167
    try:
        url = page.get('website','').split()[0].strip()
    except IndexError:
        url = page.get('link','http://www.facebook.com/%s'%page_id)
    organization = Organization(name=pname,
                        avatar=page.get('picture',''),
                        url=url)
    organization.save()
    # TODO: wtf page 115400921824318?
    # TODO: ensure page isn't just a user
    try:
        ostr = unicode(organization)
    except UnicodeDecodeError:
        ostr = '<UNICODE ERROR>'
    dbglog.info(u'created new organization for fbid %s: "%s"' % (page_id,ostr))

    try:
        record = FacebookPageRecord.objects.get(fb_id=page_id)
    except FacebookPageRecord.DoesNotExist:
        record = FacebookPageRecord(fb_id=page_id)

    record.organization = organization
    record.save()

    return organization
