'''
Module containing code for maanging Facebook pages, including Organization
or Place insertion, updating, etc.
'''

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
        self._existing_pages = set()    # page_id

    def pull_page_info(page_ids,use_cache=True):
        '''
        Returns a list of page info dicts pulled from the live FB service.

        If use_cache is True, any available cached page information stored 
        in this manager will be used.
        '''
        return []

    def import_orgs(page_ids,use_cache=True):
        '''
        Inserts Organizations for a batch of page_ids from Facebook.

        Will skip over creating any Organizations already tracked by a 
        FacebookOrgRecord instance and return a result with a 
        ModelInstanceExists set as the error.

        If use_cache is True, any available cached page information stored 
        in this manager will be used.

        Returns a parallel list of PageImportReport objects.
        '''
        return []

    def import_places(page_ids,use_cache=True,import_owners=True):
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
        return []
