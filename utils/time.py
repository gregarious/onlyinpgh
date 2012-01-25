from pytz import timezone, utc

# cliff's notes on converting a UTC dt:
# >>> from pytz import timezone
# >>> utc = timezone('utc'); est = timezone('US/Eastern')
# >>> utc_dt = utc.localize(dt)                         % change the tz-agnostic datetime into a utc datetime
# >>> est_dt = est.normalize(utc_dt.astimezone(est))    % convert into the EST timezone
# Note that just setting tzinfo to localize and using datetime.astimezone to convert isn't enough. the pytz 
#   normalize/localize methods are needed to ensure Daylight savings special cases are handled

def utctolocal(dt,local_tz_name,return_naive=False):
    '''
    Converts the given datetime to the time zone given by local_tz_name.

    If return_naive is True, the returned datetime will have it's
    tzinfo field cleared. Otherwise, it's set to a UTC tzinfo.

    Will fail if input dt.tzinfo is set to a non-UTC timezone.
    '''
    tz_local = timezone(local_tz_name)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=utc)   # change the tz-agnostic datetime into a utc datetime
    elif dt.tzinfo != utc:
        raise ValueError('Given datetime has non-UTC tzinfo: %s'%str(dt.tzinfo))

    dt = tz_local.normalize(dt.astimezone(tz_local))    # convert into the local timezone
    
    # return either a tz naive or aware version of the new dt
    return dt if not return_naive else dt.replace(tzinfo=None)

def localtoutc(dt,local_tz_name=None,return_naive=False):
    '''
    Converts the given datetime to UTC. If local_tz_name is given, a tzinfo-
    naive dt will be assumed to have the given time zone (this is often more 
    convenient that just setting the dt's tzinfo manually due to the need
    to use pytz functionality).

    If return_naive is True, the returned datetime will have it's
    tzinfo field cleared. Otherwise, it's set to local_tz.

    Will fail if input dt.tzinfo is already set to a timezone different than
    the one prescribed by a given local_tz_name argument.
    '''
    if local_tz_name:
        tz_local = timezone(local_tz_name)
        if not dt.tzinfo:
            dt = tz_local.localize(dt)   # change the tz-agnostic datetime into a local datetime     and dt.tzinfo != tz_local:
        elif dt.tzinfo != tz_local:
            raise ValueError('Given datetime tzinfo (%s) conflicts with local_tz_name argument (%s)' % \
                                (str(dt.tzinfo),str(local_tz_name)))
    elif not dt.tzinfo:
        # no local_tz_name of dt.tzinfo. we don't know what the given datetime's timezone is.
        raise ValueError('No local tzinfo available for given datetime.')
 
    dt = dt.astimezone(utc)
    # return either a tz naive or aware version of the new dt
    return dt if not return_naive else dt.replace(tzinfo=None)
