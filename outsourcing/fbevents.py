class EventImportReport(object):
    # notices can be expected to be among the following:
    #   - TypeError (when page is not a valid page for the model type being created)
    #   - FacebookAPIError (for successful responses with unexpected content)
    #   - IOError (if problem getting response from server)
    #   - EventImportReport.RelatedObjectCreationError (e.g. if Org couldn't be created inside Place creation)
    #   - EventImportReport.ModelInstanceExists (if FBPageManager attempts to create an object already being managed)
    def __init__(self,fbevent_id,model_instance,notices=[]):
        self.fbevent_id = fbevent_id
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
            super(EventImportReport.RelatedObjectCreationError,self).__init__()

        def __str__(self):
            return 'RelatedObjectCreationError: %s failed with error: "%s"' % \
                    (str(self.related_object),str(self.error))

    class EventInstanceExists(Exception):
        def __init__(self,fbid):
            self.fbid = fbid
            super(PageImportReport.EventInstanceExists,self).__init__()
        
        def __str__(self):
            return 'EventInstanceExists: Facebook page id %s' % str(self.fbid)

class FBEventManager(object):
    '''
    Class to manage the building and storage of Event model instances from 
    Facebook events.
    '''
    def __init__(self,logger=None):
        self.logger = logger
        # each page ids requested will ultimately be put in one (and only one) of these buckets:
        self._cached_event_infos = {}    # fbevent_id:{event_info}
        self._unavailble_events = {}     # fbevent_id:error
        self._existing_events = set()    # fbevent_id

    def pull_event_info(fbevent_ids,use_cache=True):
        '''
        Returns a list of fb event info dicts pulled from the live FB 
        service.

        If use_cache is True, any available cached event information 
        stored in this manager will be used.
        '''
        return []

    def import_events(fbevent_ids,use_cache=True,import_related=True):
        '''
        Inserts Events for a batch of fbevent_ids from Facebook.

        Will skip over creating any Events already tracked by a 
        FacebookEventRecord instance and return a result with a 
        EventInstanceExists set as the error.

        If use_cache is True, any available cached event information 
        stored in this manager will be used.

        If import_related is True, any related pages to this event will
        be imported as well. For example, owner pages will be imported 
        as Facebook page-linked Organizations. Same with pages linked to 
        event locations. 

        Note that a Place object for each event will be created/retrieved 
        regardless -- the import_related setting only controls whether a 
        FB id-backed event location will be linked to its parent page.

        Returns a parallel list of EventImportReport objects.
        '''
        return []

    def import_events_from_pages(page_ids,use_cache=True,import_related=True):
        '''
        Inserts Places for a batch of page_ids from Facebook. Returns a 
        dict of lists of EventImportReport objects.

        See import_events for notes about options.
        '''
        return {}