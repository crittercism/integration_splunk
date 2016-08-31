#!/usr/bin/python
import datetime
import json
import sys
import requests
import time

try:
    import splunk.entity as entity
except ImportError:
    import splunk_mock.entity as entity

# The splunk name for the app. Needed for the auth storage
myapp = 'crittercism_integration'
access_token = ''
debug = False
DUMP_DIAGS = 1
interval = 10  # minutes between runs of this script as performed by Splunk
MAX_RETRY = 10

TODAY = datetime.datetime.now() # calculate this for a common time for all summary data
DATETIME_OF_RUN = TODAY.strftime('%Y-%m-%d %H:%M:%S %Z')

# a quick command to format quasi json output nicely
pretty=(lambda a:lambda v,t="\t",n="\n",i=0:a(a,v,t,n,i))(lambda f,v,t,n,i:"{%s%s%s}"%(",".join(["%s%s%s: %s"%(n,t*(i+1),repr(k),f(f,v[k],t,n,i+1))for k in v]),n,(t*i)) if type(v)in[dict] else (type(v)in[list]and"[%s%s%s]"or"(%s%s%s)")%(",".join(["%s%s%s"%(n,t*(i+1),f(f,k,t,n,i+1))for k in v]),n,(t*i)) if type(v)in[list,tuple] else repr(v))

PARAMS = 'params'
APPID = 'appId'
SORT = 'sort'
LATENCY = 'latency'
VOLUME = 'volume'
ERRORS = 'errors'
DATA = 'data'
LIMIT = 'limit'
GRAPH = 'graph'
DURATION = 'duration'
GEOMODE = 'geoMode'
FILTERS = 'filters'
COUNTRY = 'country'
US = 'US'
U = 'u'
S = 's'
D = 'd'
ENDPOINTS = 'endpoints'
FAILED = 'failed'
CHANGE_PCT = 'changePct'
VALUE = 'value'
SERIES = 'series'
NAME = 'name'
GROUPS = 'groups'
FAILURE_RATE = 'failureRate'
FAIL_RATE = 'failRate'
UNIT = 'unit'
TYPE = 'type'
STARTED_TRANSACTIONS = 'startedTransactions'
MEAN_FOREGROUND_TIME = 'meanForegroundTime'
FAILED_TRANSACTIONS = 'failedTransactions'
SUCCEEDED_TRANSACTIONS = 'succeededTransactions'
FAILED_MONEY_VALUE = 'failedMoneyValue'
COUNT = 'count'
RATE = 'rate'
MONEY_VALUE = 'moneyValue'
MEAN_DURATION = 'meanDuration'

BASEURL = "https://developers.crittercism.com/v1.0/"

def apicall_with_response_code(uri, attribs=None):
    # perform an API call
    if (debug): print u'access token is {}'.format(access_token)
    url = BASEURL + uri

    if (attribs): url += "?"+attribs

    if (debug): print u'reqstring is {}'.format(url)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': "Bearer {}".format(access_token),
        'CR-source': 'integration_splunk'
    }

    try:
        response = requests.get(url, headers=headers)
        return (response.status_code, response.json())
    except requests.exceptions.Timeout as e:
        print 'Connection timeout. Apteligent API returned an error code:', e
        sys.exit(0)
    except requests.exceptions.ConnectionError as e:
        print 'Connection error. Apteligent API returned an error code:', e
        sys.exit(0)
    except requests.exceptions.HTTPError as e:
        print 'HTTP error. Apteligent API returned an error code:', e
        sys.exit(0)
    except requests.exceptions.RequestException as e:
        print 'Apteligent API retuned an error code:', e
        sys.exit(0)

def apicall(uri, attribs=None):
    http_code, data = apicall_with_response_code(uri, attribs)
    return data

def apipost_with_response_code(uri, postdata='', keyget=None):
    # perform an API POST
    if (debug): print u'access token is {}'.format(access_token)
    url = BASEURL + uri

    if (debug):
        print u'reqstring is {}'.format(url)
        print u'postdata is {}'.format(postdata)

    pdata = json.dumps(postdata)

    if keyget:
        headers = None
    else:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': "Bearer {}".format(access_token),
            'CR-source': 'integration_splunk'
        }

    try:
        response = requests.post(url, headers=headers, data=pdata)
        if debug:
            print 'response is {}'.format(response.text)
        return (response.status_code, response.json())

    except requests.exceptions.RequestException as e:
        print u'{} MessageType="ApteligentError" Apteligent API retuned an error code: {} for the call to {}.  Maybe an ENTERPRISE feature?'.format(DATETIME_OF_RUN, e, url)
        return "ERROR"

def apipost(uri, attribs=None):
    http_code, data = apipost_with_response_code(uri, attribs)
    return data

def scopetime():
    # return an ISO8601 timestring based on NOW - Interval
    newtime=(datetime.datetime.utcnow() - datetime.timedelta(minutes=interval))

    return (newtime.isoformat())


def getAppSummary():
# read app summary information.  Print out in Splunk KV format.  Return a dict with appId and appName.

    # list of the attributes we'll hand to Apteligent, also the list we will create as Splunk Keys
    summattrs = "appName,appType,crashPercent,dau,latency,latestAppStoreReleaseDate,latestVersionString,linkToAppStore,iconURL,mau,rating,role,appVersions"
    atstring = "attributes=%s"%summattrs
    gdata = apicall("apps", atstring)

    AppDict = {}
    for appId in gdata.keys():
        printstring = u'{} MessageType="AppSummary" appId={} '.format(DATETIME_OF_RUN, appId)
        slist = summattrs.split(",")
        for atname in slist:
            printstring += u'{}="{}"'.format(atname,gdata[appId][atname])
            if atname == "appName" : AppDict[appId]= {'name': gdata[appId][atname], 'versions': gdata[appId]['appVersions']}
        print printstring

    return AppDict


def getCrashSummary(appId, appName):
# given an appID and an appName, produce a Splunk KV summary of the crashes for a given timeframe
    mystime = scopetime()
    crashdata = None
    crashattrs = "hash,lastOccurred,sessionCount,uniqueSessionCount,reason,status,displayReason,name"

    http_code = None
    retry = 0
    while http_code != 200:
        http_code, crashdata = apicall_with_response_code("app/%s/crash/summaries" % appId, "lastOccurredStart=%s" % mystime)
        retry += 1
        if retry > MAX_RETRY:
            break

    CrashDict = {}
    if http_code != 200:
        print u'{} MessageType="CrashSummary" appId={} appName="{}" Could not get crash summaries for {}. Code: {} after retry {}'.format(DATETIME_OF_RUN, appId, appName, mystime, http_code, retry)
    elif crashdata:
        for x, y in enumerate(crashdata):
            printstring = u'{} MessageType="CrashSummary" appId={} appName="{}" '.format(DATETIME_OF_RUN, appId, appName)
            slist = crashattrs.split(",")
            for atname in slist:
                printstring += u'{}="{}" '.format(atname, crashdata[x][atname])
                if atname == "hash" : CrashDict[crashdata[x][atname]]= appName
            print printstring
    else:
        print u'{} MessageType="CrashSummary" appId={} appName="{}" No crashes found for {}.'.format(DATETIME_OF_RUN, appId, appName, mystime)
    return CrashDict


def getBreadcrumbs(crumbs, hash, appName) :
    for crumb in crumbs:
        version = crumb.get('appVersion')
        os = crumb.get('os')
        device = crumb.get('device')
        printstring = u'{} MessageType="CrashDetailBreadcrumbs" hash={} \n'.format(DATETIME_OF_RUN, hash)
        parsed = json.dumps(crumb['parsedBreadcrumbs'])
        parsed = '}|{'.join(parsed.split('}, {'))
        parsed = parsed.replace('{', '')
        parsed = parsed.replace('}', '')
        parsed = parsed.replace('"', "'")
        printstring += u'trace="{}" os="{}" appVersion="{}" device="{}"'.format(parsed, os, version, device)
        print printstring


def getStacktrace(stacktrace,hash) :
    print u'{} MessageType="CrashDetailStacktrace"  hash={} '.format(DATETIME_OF_RUN, hash),pretty(stacktrace)


def diag_geo(data,hash):
    if (debug) : print "into diag_geo"
    for country in data.keys():
        for city in data[country].keys():
            if city == '--NAME--':
                continue
            (lat,lon,crashes) = (str(data[country][city][0]),
                                str(data[country][city][1]),
                                str(data[country][city][2])  )
            print u'{} MessageType="CrashDiagsGeo" hash={} country="{}" city="{}" lat={} lon={} crashes="{}"'.format(DATETIME_OF_RUN, hash, country, city, lat, lon, crashes)


def diag_discrete(data, hash):
    datastring= ""
    for dstat in data.keys():
        for (var,val) in data[dstat]:
            datastring += " \"%s:%s\"=\"%s\"" % (dstat,str(var).replace(" ","_"),str(val))

    print u'{} MessageType="CrashDiagsDiscrete"  hash={} {} '.format(DATETIME_OF_RUN, hash, datastring)


def diag_affected_users(data,hash) :
    for uhash in data.keys():
        datastring= ""
        for vhash in data[uhash]:
            datastring += " %s=\"%s\"" % (str(vhash).replace(" ","_"),str(data[uhash][vhash]))

        print u'{} MessageType="CrashDiagsAffectedUser"  hash={}  userhash={} {} '.format(DATETIME_OF_RUN, hash, uhash, datastring)


def diag_affected_versions(data,hash):
    datastring = ""
    for x,vpair in data:
        datastring += " \"%s\"=%s" % (str(x).replace(" ","_"),str(vpair))

    print u'{} MessageType="CrashDiagsAffectedVersions"  hash={} {} '.format(DATETIME_OF_RUN, hash, datastring)


def diag_cont_bar(data, hash):
# The continuous_bar_diagnostic_data data comes back as two arrays per datapoint
# we Zip them back together to make them KV for Splunk

    for dstat in data.keys():
        x=0
        valstr = ""
        tmp={}
        for vstat in data[dstat]:
            tmp[x]=data[dstat][vstat]
            x+=1
        zipped = zip(tmp[1],tmp[0])
        for var,val in zipped:
            valstr += " \"%s\"=%s" %(val,var)

        print u'{} MessageType="CrashDiagsContBar"  hash={} datatype={} {} '.format(DATETIME_OF_RUN, hash, dstat, valstr)


def diag_cont(data, hash):
# Grab all of the continuous data from Apteligent and format into a splunk event
    datastring= ""
    for uhash in data.keys():

        for vhash in data[uhash]:
            datastring += " %s_%s=\"%s\"" % (uhash,str(vhash).replace(" ","_"),str(data[uhash][vhash]))

    print u'{} MessageType="CrashDiagsContinuous"  hash={} {} '.format(DATETIME_OF_RUN, hash, datastring)


#############
def getDiagnostics(diags,hash) :
# Dump and prettyprint the diags -- might want to expand on this...
    if (DUMP_DIAGS ==0) :
        print u'{} MessageType="CrashDetailDiagnostics" DISABLED PER CONFIG FILE '.format(DATETIME_OF_RUN, hash)
        return

    for key in diags.keys() :
        if (key == 'geo_data'):
            diag_geo(diags[key], hash)

        elif (key=='discrete_diagnostic_data'):
            diag_discrete(diags[key], hash)

        elif (key=='affected_users'):
            diag_affected_users(diags[key], hash)


        elif (key=='affected_versions'):
            diag_affected_versions(diags[key], hash)

        elif (key=='continuous_bar_diagnostic_data'):
            diag_cont_bar(diags[key], hash)

        elif (key=='continuous_diagnostic_data'):
            diag_cont(diags[key], hash)
        elif (key=='num_geo_points'):
            continue
        elif (key=='discrete_bar_diagnostic_data'):
            continue
        else:
            print u'--UNPROCESSED----{} - {}'.format(key,diags[key])


def getDOBV(stacktrace, hash) :
# handle the DailyOccurrencesByVersion coming back from a crashdetail
    print u'{} MessageType="CrashDetailDailyOccurrencesByVersion"  hash={} '.format(DATETIME_OF_RUN, hash), pretty(stacktrace)


def getUSCBV(stacktrace,hash) :
# handle the UniqueSessionCountsByVersion coming back from a crashdetail
    print u'{} MessageType="CrashDetailUniqueSessionCountsByVersion"  hash={} '.format(DATETIME_OF_RUN, hash), pretty(stacktrace)


def getSCBV(stacktrace, hash) :
# handle the SessionCountsByVersion coming back from a crashdetail
    print u'{} MessageType="CrashDetailSessionCountsByVersion"  hash={} '.format(DATETIME_OF_RUN, hash), pretty(stacktrace)


def getSymStacktrace(stacktrace,hash) :
# handle the lSymbolizedStacktrace coming back from a crashdetail
    print u'{} MessageType="CrashDetailSymbolizedStacktrace"  hash={} '.format(DATETIME_OF_RUN, hash), pretty(stacktrace)


def getCrashDetail(hash, appName):
# given a crashhash, get all of the detail about that crash

    crashdetail = apicall("crash/%s" % hash, "diagnostics=True")
    printstring = u'{} MessageType="CrashDetail"  appName="{}" '.format(DATETIME_OF_RUN, appName)
    for dkey in crashdetail.keys():
        if dkey == "breadcrumbTraces" :
            getBreadcrumbs(crashdetail[dkey], hash, appName)
        elif dkey == "stacktrace" :
            getStacktrace(crashdetail[dkey], hash)
        elif dkey == "diagnostics" :
            getDiagnostics(crashdetail[dkey],hash)
        elif dkey == "dailyOccurrencesByVersion" :
            getDOBV(crashdetail[dkey], hash)
        elif dkey == "uniqueSessionCountsByVersion" :
            getUSCBV(crashdetail[dkey],hash)
        elif dkey == "sessionCountsByVersion" :
            getSCBV(crashdetail[dkey],hash)
        elif dkey == "symbolizedStacktrace" :
            getSymStacktrace(crashdetail[dkey],hash)
        else:
            printstring += u'{}="{}" '.format(dkey, crashdetail[dkey])

    print printstring


def getErrorSummary(appId,appName) :
# Grab the elements we need from errorMonitoring endpoint
# errorSummary is returned as a post...

# Get the current apploads
#    params = {"params":{"appId":appId,"graph":"appLoads","duration":43200}, "filter":{"carrier":""}}
    params = {"params":{"appId":appId,"graph":"appLoads","duration":43200}}
    appload_sum=apipost("errorMonitoring/graph", params)
#    print(pretty(appload_sum))
    dlist = appload_sum['data']['series'][0]['points']
    print u'{} MessageType=HourlyAppLoads AppLoads={} appId="{}" appName="{}"'.format(DATETIME_OF_RUN, dlist[len(dlist) - 1], appId, appName)
    #print jtest['data']


def getCrashesByOS(appId,appName):
    """Get the number of crashes for a given app sorted by OS."""

    params={"params":{
	    "graph": "crashes",
		"duration": 1440,
		"groupBy": "os",
        "appId": appId
        }}

    crashesos = apipost("errorMonitoring/pie",params)
    # is user does not have pro access for a given application, this fails.
    if (crashesos == "ERROR") : return (None,None)

    mystring = u''
    try:
        for series in crashesos['data']['slices']:
            mystring += u'("{}",{}),'.format(series['label'], series['value'])

        print u'{} MessageType=DailyCrashesByOS appName="{}" appId="{}" DATA {}'.format(DATETIME_OF_RUN, appName, appId, mystring)
        return

    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_crashes_by_os')
        return (None, None)


"""--------------------------------------------------------------"""
def getGenericPerfMgmt(appId, appName,graph,groupby,messagetype):
    """Generic data return for performanceManagement/pie end point."""

    params={"params":{
        "groupBy": groupby,
        "graph": graph,
        "duration": 1440,
        "appId": appId
        }}

    server_errors = apipost("performanceManagement/pie",params)

#    print "%s DEBUG Into getGenericPerfMgmt appId = %s  appName = %s graph= %s groupby = %s messagetype = %s" %(DATETIME_OF_RUN, appId, appName,graph,groupby,messagetype)

    mystring = u''
    try:
        slices = server_errors['data']['slices']
        if slices:
            for series in server_errors['data']['slices']:
                mystring += u'("{}",{}),'.format(series['label'], series['value'])

            print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(DATETIME_OF_RUN, messagetype, appName, appId, mystring)
        else:
            print u'{} MessageType="ApteligentError" Error: API did not return {} data for {}. Returned {}'.format(DATETIME_OF_RUN, messagetype, appId, server_errors['data'])
    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: API returned malformed data in {} of {}. Data: {}'.format(DATETIME_OF_RUN, str(e), messagetype, server_errors)
        return (None, None)


def getAPMEndpoints(app_id, app_name, sort, message_type):
    """Get APM Endpoint data."""

    params = {
        PARAMS: {
            APPID: app_id,
            SORT: sort,
            LIMIT: 10,
            DURATION: 240,
            GEOMODE: True
        }
    }

    response = apipost("apm/endpoints", params)

    try:
        messages = u','.join([u'("{}{}",{})'.format(ep[D], ep[U], ep[S]) for ep in
                              response[DATA][ENDPOINTS]])
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), message_type))
        return None, None


def getAPMServices(app_id, app_name, sort, message_type):
    """Get APM services data"""

    params = {
        PARAMS: {
            APPID: app_id,
            SORT: sort,
            LIMIT: 10,
            DURATION: 240,
            GEOMODE: True
        }
    }

    response = apipost("apm/services", params)

    try:
        messages = u','.join([u'("{}",{})'.format(service['name'], service['sort']) for service in
                              response['data']['services']])
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), message_type))
        return None, None


def getAPMGeo(app_id, app_name, graph, message_type):
    """Get APM geographical data"""

    params = {
        PARAMS: {
            APPID: app_id,
            GRAPH: graph,
            LIMIT: 10,
            DURATION: 240,
        }
    }

    response = apipost("apm/geo", params)

    try:
        messages = u','.join([u'("{}",{})'.format(location, data) for location, data in
                      response['data']['series'][0]['geo'].iteritems()])
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), message_type))
        return None, None


def getGenericErrorMon(appId, appName,graph,groupby,messagetype):
    """Generic data return for errorMonitoring/pie end point."""

    params={"params":{
        "groupBy": groupby,
        "graph": graph,
        "duration": 1440,
        "appId": appId
        }}

    server_errors = apipost("errorMonitoring/pie",params)

    # print "{} DEBUG Into getGenericErrorMon appId = {}  appName = {} graph= {} groupby = {} messagetype = {} DATA {}".format(DATETIME_OF_RUN, appId, appName,graph,groupby,messagetype, server_errors)

    mystring = u''
    try:
        slices = server_errors['data']['slices']
        if slices:
            for series in slices:
                mystring += u'("{}",{}),'.format(series['label'], series['value'])

            print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(DATETIME_OF_RUN, messagetype, appName, appId, mystring)
        else:
            print u'{} MessageType="ApteligentError" Error: API did not return {} data for {}. Returned {}'.format(DATETIME_OF_RUN, messagetype, appId, server_errors['data'])

    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: API returned malformed data in {} of {}. Data: {}'.format(DATETIME_OF_RUN, str(e), messagetype, server_errors)
        return (None, None)


"""--------------------------------------------------------------"""

def getUserflowsSummary(app_id, app_name, message_type):
    """Calls the transactions summary endpoint for an app

    :param app_id: (string) App ID used to request data from the API
    :param app_name: (string) Human-readable app name
    :param message_type: (string) Type of message (for sorting in Splunk)
    :return: None
    """
    uri = 'transactions/{}/summary/'.format(app_id)

    response = apicall(uri)

    try:
        messages = u','.join([u'("{}",{},{})'.format(metric, data[VALUE], data[CHANGE_PCT]) for metric, data in
                              response[SERIES].iteritems()])
        print u'{} MessageType={} appName="{}" appId="{}" DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), message_type))
        return None, None

def getUserflowsRanked(app_id, app_name, category, message_type):
    """Calls the transactions ranked endpoint to get the top failed transactions

    :param app_id: (string) App ID used to request data from the API
    :param app_name: (string) Human-readable app name
    :param category: (string) Kind of transaction to return (e.g. failed, succeeded)
    :param message_type: (string) Type of message (for sorting in Splunk), equivalent to category
    :return: None
    """

    uri = 'transactions/{}/ranked/{}/'.format(app_id, category)

    response = apicall(uri)

    try:
        messages = u','.join([u'("{}",{},{})'.format(group[NAME], group[FAILURE_RATE], group[UNIT][TYPE]) for group in
                              response[GROUPS]])
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), message_type))


def getUserflowsDetails(app_id, app_name):
    """Call the userflows details/change endpoint for an app

    :param app_id: (string) App ID used to request data from the API
    :param app_name: (string) Human-readable app name
    :return: None
    """
    uri = 'transactions/{}/details/change/P1M?pageNum=1&pageSize=10&sortBy=name&sortOrder=ascending'.format(app_id)

    response = apicall(uri)

    getUserflowsChangeDetails(app_id, app_name, response)

    for group in response[GROUPS]:
        getUserflowsGroups(app_id, app_name, group[NAME])


def getUserflowsChangeDetails(app_id, app_name, userflow_dict):
    """Process the userflows details/change data for Splunk

    :param app_id: (string) App ID used to request data from the API
    :param app_name: (string) Human-readable app name
    :return: None
    """

    try:
        for group in userflow_dict[GROUPS]:
            messages = u''
            messages += (u'(Name="{}",volume={},foregroundTime={}s,'
                         u'failed={},failRate={}%,successful={},'
                         u'revenueAtRisk=${})'.format(
                              group[NAME],
                              group[SERIES][STARTED_TRANSACTIONS][VALUE],
                              group[SERIES][MEAN_FOREGROUND_TIME][VALUE],
                              group[SERIES][FAILED_TRANSACTIONS][VALUE],
                              group[SERIES][FAIL_RATE][VALUE],
                              group[SERIES][SUCCEEDED_TRANSACTIONS][VALUE],
                              group[SERIES][FAILED_MONEY_VALUE][VALUE]))
            print u'{} MessageType={} appName="{}" appId="{}" DATA {}'.format(
                DATETIME_OF_RUN, 'UserflowsChangeDetails', app_name, app_id, messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), 'UserflowsChangeDetails'))

def getUserflowsGroups(app_id, app_name, group):
    """Call the transactions group endpoint for a group

    :param app_id: (string) App ID used to request data from the API
    :param app_name: (string) Human-readable app name
    :param group: (string) The name of a transactions group (e.g. Login)
    :return: None
    """

    uri = '/transactions/{}/group/{}'.format(app_id, group)

    response = apicall(uri)

    try:
        for transaction in response[SERIES].keys():
            messages = u''
            messages += u'(Metric="{}",count={},rate={}%,moneyValue=${},meanDuration={})'.format(
                transaction,
                response[SERIES][transaction][COUNT][VALUE],
                response[SERIES][transaction][RATE][VALUE],
                response[SERIES][transaction][MONEY_VALUE][VALUE],
                response[SERIES][transaction][MEAN_DURATION][VALUE])
            print u'{} MessageType={} appId="{}" appName="{}" Userflow="{}" DATA {}'.format(
                DATETIME_OF_RUN,
                'UserflowGroup',
                app_id,
                app_name,
                group,
                messages)

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), "TransactionsGroup"))


def getDailyAppLoads(appId,appName):
    """Get the number of daily app loads for a given app."""

    params={"params":{
        "graph": "appLoads",
        "duration": 1440,
        "appId": appId,
        }}

    apploadsD = apipost("errorMonitoring/graph", params)

    try:
        print u'{} MessageType=DailyAppLoads appName="{}" appId="{}" dailyAppLoads={}'.format(DATETIME_OF_RUN, appName, appId, apploadsD['data']['series'][0]['points'][0])
    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_daily_app_loads')
        return None


def getDailyCrashes(appId,appName):
    """Get the number of daily app crashes for a given app."""
    """good candidate for 'backfill' data if needed"""

    crashdata = apicall("app/%s/crash/counts" % appId)

    try:
        print u'{} MessageType=DailyCrashes appName="{}" appId="{}" dailyCrashes={}'.format(DATETIME_OF_RUN, appName, appId, crashdata[len(crashdata) - 1]['value'])
    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_daily_crashes')
        return None

    return


def getTrends(appId,appName):
    """Calls the trends endpoint for an app

    :param appId: (string) App ID used to request data from the API
    :param appName: (string) Human-readable app name
    :return: None
    """

    trends_data = apicall(u'{}/trends'.format(appId))

    getTopValues(appId,appName,trends_data)
    getTimeseriesTrends(appId,appName,trends_data)


def getTopValues(appId,appName,trendsData):
    """Pulls todayTopValues data out of the trends dictionary for specific trends, and prints to Splunk.
    :param appId: (string) App ID
    :param appName: (string) Human-readable app name
    :param trendsData: (dict) A dictionary of trends data
    :return: None
    """

    trend_names = ['appLoadsByVersion',
                   'crashesByVersion',
                   'appLoadsByOs',
                   'crashesByOs']

    for trend in trend_names:
        messages = u''
        for version, value in trendsData[u'series'][trend][u'todayTopValues'].iteritems():
            messages += u'("{}",{}),'.format(version, value)
        try:
            print u'{} MessageType={} appName="{}" appId="{}" DATA {}'.format(DATETIME_OF_RUN, trend, appName, appId, messages)
        except KeyError as e:
            print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'TopValues')
            continue

    return


def getTimeseriesTrends(appId,appName,trendsData):
    """Pulls time series data out of the trends dictionary for crashes by version, and prints to Splunk.
    :param appId: (string) App ID
    :param appName: (string) Human-readable app name
    :param trendsData: (dict) A dictionary of trends data
    :return: None
    """

    for version in trendsData['series']['crashesByVersion']['categories'].keys():
        messages = u''
        for bucket in trendsData['series']['crashesByVersion']['categories'][version]['buckets']:
            messages += u'({},{}),'.format(bucket['start'][:10], bucket['value'])
        try:
            print u'{} MessageType={} appName="{}" appId="{}" appVersion="{}" DATA {}'.format(DATETIME_OF_RUN, "TimeseriesTrends",
                                                                                              appName, appId, version, messages)
        except KeyError as e:
            print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'TimeseriesTrends')
    return

def getCrashCounts(appId,appName):
    """Get the number of daily app crashes for a given app."""
    """good candidate for 'backfill' data if needed"""

    crashdata = apicall("app/%s/crash/counts" % appId)

    mystring = u''

    try:
        for series in crashdata:
            mystring += u'({},{}),'.format(series['date'], series['value'])

        print u'{} MessageType=CrashCounts appName="{}" appId="{}" DATA {}'.format(DATETIME_OF_RUN, appName, appId, mystring)

    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_crash_counts')
        return None

    return


def getCredentials(sessionKey):
# access the credentials in /servicesNS/nobody/<MyApp>/admin/passwords

    if (debug) : print u'{} MessageType="ApteligentDebug"  Into getCredentials'.format(DATETIME_OF_RUN)

    auth = None
    entities = None
    retry = 1

    while auth is None and retry < MAX_RETRY:
        if (debug) : print u'Attempt to get credentials {}'.format(retry)
        try:
            # list all credentials
            entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                        owner='nobody', sessionKey=sessionKey)
        except Exception, e:
            print (u'{} MessageType="ApteligentDebug" '
                   u'Could not get {} credentials from splunk. '
                   u'Error: {}'.format(DATETIME_OF_RUN, myapp, str(e)))

        # return first set of credentials
        if (debug) : print "Entities is ", entities
        if entities:
            auth = entities.items()[0][1].get('clear_password')
        else:
            time.sleep(10)

        retry += 1

    if not auth:
        print (u'{} MessageType="ApteligentDebug" '
               u'No credentials have been found for app {} . '
               u'Maybe a setup issue?'.format(DATETIME_OF_RUN, myapp))

    return auth

###########
#

def main():
    #read session key sent from splunkd
    sessionKey = sys.stdin.readline().strip()
    if (debug) : print u'{} MessageType="ApteligentDebug" sessionKey is {}'.format(DATETIME_OF_RUN, sessionKey)

    if len(sessionKey) == 0:
        print u'{} MessageType="ApteligentError" Did not receive a session key from splunk. '.format(DATETIME_OF_RUN)
        exit(2)

    # now get crittercism oauth token
    global access_token
    access_token = getCredentials(sessionKey)

    if (debug) : print u'{} MessageType="ApteligentDebug" OAuth token is {}'.format(DATETIME_OF_RUN, access_token)

# Get application summary information.
    apps = getAppSummary()
    for key in apps.keys():
        crashes = getCrashSummary(key, apps[key]['name'])
        if crashes:
            for ckey in crashes.keys():
                getCrashDetail(ckey, apps[key]['name'])

        getTrends(key,apps[key]['name'])

        getDailyAppLoads(key,apps[key]['name'])
        getDailyCrashes(key,apps[key]['name'])
        getCrashCounts(key,apps[key]['name'])

        getGenericPerfMgmt(key,apps[key]['name'],'volume','device','DailyVolumeByDevice')
        getGenericPerfMgmt(key,apps[key]['name'],'errors','service','DailyServiceErrorRates')
        getGenericPerfMgmt(key,apps[key]['name'],'volume','os','DailyVolumeByOS')
        getGenericPerfMgmt(key,apps[key]['name'],'volume','appVersion','VolumeByAppVersion')

        getGenericErrorMon(key,apps[key]['name'],'crashes','device','CrashesByDevice')
        getGenericErrorMon(key,apps[key]['name'],'crashPercent','device','CrashPerByDevice')
        getGenericErrorMon(key,apps[key]['name'],'appLoads','os','ApploadsByOs')
        getGenericErrorMon(key,apps[key]['name'],'crashes','os','DailyCrashesByOs')
        getGenericErrorMon(key,apps[key]['name'],'crashPercent','os','CrashPerByOs')
        getGenericErrorMon(key,apps[key]['name'],'crashPercent','appVersion','CrashPerByAppVersion')
        getGenericErrorMon(key,apps[key]['name'],'crashes','appVersion','CrashByAppVersion')
        getGenericErrorMon(key,apps[key]['name'],'appLoads','appVersion','LoadsByAppVersion')
        getGenericErrorMon(key,apps[key]['name'],'dau','appVersion','DauByAppVersion')
        getGenericErrorMon(key,apps[key]['name'],'appLoads','device','ApploadsByDevice')

        getAPMEndpoints(key, apps[key]['name'], LATENCY, 'ApmEndpointsLatency')
        getAPMEndpoints(key, apps[key]['name'], VOLUME, 'ApmEndpointsVolume')
        getAPMEndpoints(key, apps[key]['name'], ERRORS, 'ApmEndpointsErrors')
        getAPMEndpoints(key, apps[key]['name'], DATA, 'ApmEndpointsData')

        getAPMServices(key, apps[key]['name'], LATENCY, 'ApmServicesLatency')
        getAPMServices(key, apps[key]['name'], VOLUME, 'ApmServicesVolume')
        getAPMServices(key, apps[key]['name'], ERRORS, 'ApmServicesErrors')
        getAPMServices(key, apps[key]['name'], DATA, 'ApmServicesData')

        getAPMGeo(key, apps[key]['name'], LATENCY, 'ApmGeoLatency')
        getAPMGeo(key, apps[key]['name'], VOLUME, 'ApmGeoVolume')
        getAPMGeo(key, apps[key]['name'], ERRORS, 'ApmGeoErrors')
        getAPMGeo(key, apps[key]['name'], DATA, 'ApmGeoData')

        getUserflowsSummary(key, apps[key]['name'], "UserflowsSummary")
        getUserflowsRanked(key, apps[key]['name'], FAILED, "UserflowsRankedFailed")
        getUserflowsDetails(key, apps[key]['name'])

if __name__=='__main__':
    main()
