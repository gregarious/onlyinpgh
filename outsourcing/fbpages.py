'''
Module containing code for maanging Facebook pages, including Organization
or Place insertion, updating, etc.
'''

from django.db import transaction

from onlyinpgh.outsourcing.apitools import facebook, google, factual
from onlyinpgh.identity.models import Organization
from onlyinpgh.outsourcing.models import FacebookOrgRecord

import logging
dbglog = logging.getLogger('onlyinpgh.debugging')

def get_full_place_pages(pids):
    '''
    Returns a list of full page information dicts, one per page id.

    Bad requests will return caught exception objects.
    '''
    page_details = []
    cmds = []
    def _add_batch(batch):
        responses = facebook.oip_client.run_batch_request(batch)
        for resp,batch_req in zip(responses,batch):
            try:
                resp = facebook.oip_client.postprocess_response(batch_req.to_GET_format(),resp)
            except facebook.FacebookAPIError as e:
                resp = e
            page_details.append(resp)

    for pid in pids:
        cmds.append(facebook.BatchCommand(pid,{'metadata':1}))
        if len(cmds) == 50:
            _add_batch(cmds)
            cmds = []
    if len(cmds) > 0:
        _add_batch(cmds)

    return page_details 

@transaction.commit_on_success
def store_fbpage_organization(page_info):
    '''
    Takes a dict of properties retreived from a Facebook Graph API call for
    a page and stores an Organization from the information. The following 
    fields in the dict are used:
    - id        (required)
    - type      (required with value 'page' or a TypeError will be thrown)
    - name      (required)
    - website
    - picture

    If a FacebookOrgRecord already exists for the given Facebook id, the 
    already linked organization is returned. An INFO message is logged to 
    note the attempt to store an existing page as an Organization.
    '''
    pid = page_info['id']

    try:
        organization = FacebookOrgRecord.objects.get(fb_id=pid).organization
        dbglog.info('Existing fb page Organization found for fbid %s' % str(pid))
        return organization
    except FacebookOrgRecord.DoesNotExist:
        pass

    if page_info.get('type') != 'page':
        raise TypeError("Cannot store object without 'page' type as a Place.")

    pname = page_info['name'].strip()

    try:
        # url field can be pretty free-formed and list multiple urls. 
        # we take the first one (identified by whitespace parsing)
        url = page_info.get('website','').split()[0].strip()[:400]
    except IndexError:
        # otherwise, go with the fb link (and manually create it if even that fails)
        url = page_info.get('link','http://www.facebook.com/%s'%pid)
    organization, created = Organization.objects.get_or_create(name=pname[:200],
                                                                avatar=page_info.get('picture','')[:400],
                                                                url=url)

    if not created:
        dbglog.notice('An organization matching fbid %s already existed with '\
                        'no FacebookOrgRecord. The record was created.' % str(pid))
    
    record = FacebookOrgRecord.objects.create(fb_id=pid,organization=organization)
    dbglog.info(u'Stored new Organization for fbid %s: "%s"' % (pid,unicode(organization)))

    if len(pname) == 0:
        logging.warning('Facebook page with no name was stored as Organization')

    return organization

class PageImportReport(object):
    # notices can be expected to be among the following:
    #   - TypeError (when page is not a valid page for the model type being created)
    #   - FacebookAPIError (for successful responses with unexpected content)
    #   - IOError (if problem getting response from server)
    #   - PageImportReport.RelatedObjectCreationError (e.g. if Org couldn't be created inside Place creation)
    #   - PageImportReport.ModelInstanceExists (if FBPageManager attempts to create an object already being managed)
    def __init__(self,page_id,model_instance,notices=[]):
        self.page_id = page_id
        self.model_instance = model_instance
        self.notices = notices

    class RelatedObjectCreationError(Exception):
        def __init__(self,related_object,error):
            '''
            Related object is any string, error is Exception that occurred
            while object creation was being attempted.
            '''
            self.related_object = related_object
            self.error = error
            super(PageImportReport.RelatedObjectCreationError,self).__init__()

        def __str__(self):
            return 'RelatedObjectCreationError: %s failed with error: "%s"' % \
                    (str(self.related_object),str(self.error))

    class ModelInstanceExists(Exception):
        def __init__(self,fbid,model_type):
            self.model_type = model_type
            self.fbid = fbid
            super(PageImportReport.ModelInstanceExists,self).__init__()
        
        def __str__(self):
            return 'ModelInstanceExists: %s for Facebook page id %s' % \
                    (str(self.model_type),str(self.fbid))

class FBPageManager(object):
    '''
    Class to manage the building and storage of Place and Organization
    model instances from Facebook pages.
    '''
    def __init__(self,logger=None):
        self.logger = logger
        # each page ids requested will ultimately be put in one (and only one) of these buckets:
        self._cached_page_infos = {}    # page_id:{page_info}
        self._unavailble_pages = {}     # page_id:error

    def pull_page_info(self,page_ids,use_cache=True):
        '''
        Returns a list of page info dicts pulled from the live FB service.

        If use_cache is True, any available cached page information stored 
        in this manager will be used.
        '''
        # if we can use the cache, pull any cached ids from the API request
        if use_cache:
            ids_to_pull = list(set(page_ids).difference(self._cached_page_infos.keys()))
        else:
            ids_to_pull = page_ids
        
        try:
            page_infos = get_full_place_pages(ids_to_pull)
        except IOError as e:
            # spread the IOError to all requests
            page_infos = [e]*len(ids_to_pull)

        # update the cached items
        for pid,info in zip(ids_to_pull,page_infos):
            # each "info" is either a successful page info response, or 
            #  an Exception. put them into the correct bnuckets
            if isinstance(info,Exception):
                self._unavailble_pages[pid] = info
            else:
                self._cached_page_infos[pid] = info

        # return the responses in the same order as the requests
        return [self._cached_page_infos.get(pid,self._unavailble_pages.get(pid))
                    for pid in page_ids]

    def _store_org(self,info):
        '''
        Does actual storage of a new page-bacekd organization. Does the 
        packaging into PageImportReports.
        '''
        pid = info['id']
        # first off -- if org is already stored, we're done -- no overwriting as of now
        try:
            FacebookOrgRecord.objects.get(fb_id=pid)
            return PageImportReport(pid,None,
                        notices=[PageImportReport.ModelInstanceExists(pid,'Organization')])
        except FacebookOrgRecord.DoesNotExist:
            pass

        # try to store, and catch TypeErrors from info not being a 'page'
        try:
            org = store_fbpage_organization(info)
            return PageImportReport(pid,org)
        except TypeError as e:
            return PageImportReport(pid,None,notices=[e])

    def import_orgs(self,page_ids,use_cache=True):
        '''
        Inserts Organizations for a batch of page_ids from Facebook.

        Will skip over creating any Organizations already tracked by a 
        FacebookOrgRecord instance and return a result with a 
        ModelInstanceExists set as the error.

        If use_cache is True, any available cached page information stored 
        in this manager will be used.

        Returns a parallel list of PageImportReport objects.
        '''
        # TODO: could do something here to filter out page ids that we 
        #       already have info for before we pull them
        page_infos = self.pull_page_info(page_ids,use_cache)
        
        return [self._store_org(info) if not isinstance(info,Exception)
                                        else PageImportReport(pid,None,[info])
                                        for pid,info in zip(page_ids,page_infos)]

    def import_places(self,page_ids,use_cache=True,import_owners=True):
        '''
        Inserts Places for a batch of page_ids from Facebook.

        Will skip over creating any Places already tracked by a 
        FacebookOrgRecord instance and return a result with a
        ModelInstanceExists set as the error.

        If use_cache is True, any available cached page information stored 
        in this manager will be used.

        If import_owners is True, an Organization owning the Place that 
        does not already exist will be imported as well.

        Returns a parallel list of PageImportReport objects.
        '''
        # TODO: filter out pages already linked to places
        return []
