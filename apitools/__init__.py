class APIError(Exception):
    def __init__(self,api_name,*args,**kwargs):
        super(APIError,self).__init__(*args,**kwargs)
