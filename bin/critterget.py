#!/usr/bin/python
import datetime
import json
import os
import sys
import requests
import time

try:
    import splunk.entity as entity
except ImportError:
    import splunk_mock.entity as entity

# The splunk name for the app. Needed for the auth storage
myapp = 'crittercism_integration'

DUMP_DIAGS = 1
interval = 10  # minutes between runs of this script as performed by Splunk
MAX_RETRY = 10

debug = os.environ.get('CR_SPLUNK_DEBUG')

TODAY = datetime.datetime.now() # calculate a common time for all summary data
DATETIME_OF_RUN = TODAY.strftime('%Y-%m-%d %H:%M:%S %Z')

# a quick command to format quasi json output nicely
pretty=(lambda a:lambda v,t="\t",n="\n",i=0:a(a,v,t,n,i))(lambda f,v,t,n,i:"{%s%s%s}"%(",".join(["%s%s%s: %s"%(n,t*(i+1),repr(k),f(f,v[k],t,n,i+1))for k in v]),n,(t*i)) if type(v)in[dict] else (type(v)in[list]and"[%s%s%s]"or"(%s%s%s)")%(",".join(["%s%s%s"%(n,t*(i+1),f(f,k,t,n,i+1))for k in v]),n,(t*i)) if type(v)in[list,tuple] else repr(v))

APPID = 'appId'
APPLOADS = 'appLoads'
APPNAME = 'appName'
APPS = 'apps'
APPVERSION = 'appVersion'
APPVERSIONS = 'appVersions'
ATTRIBUTES = 'attributes'
CATEGORIES = 'categories'
CHANGE_PCT = 'changePct'
COUNT = 'count'
COUNTRY = 'country'
CRASHES = 'crashes'
CRASHESBYVERSION = 'crashesByVersion'
CRASHPERCENT = 'crashPercent'
D = 'd'
DATA = 'data'
DATE = 'date'
DAU = 'dau'
DEVICE = 'device'
DURATION = 'duration'
ENDPOINTS = 'endpoints'
ERRORS = 'errors'
GEO = 'geo'
GEOMODE = 'geoMode'
GRAPH = 'graph'
GROUPBY = 'groupBy'
GROUPS = 'groups'
FAILED = 'failed'
FAILED_MONEY_VALUE = 'failedMoneyValue'
FAILED_TRANSACTIONS = 'failedTransactions'
FAIL_RATE = 'failRate'
FAILURE_RATE = 'failureRate'
FILTERS = 'filters'
LABEL = 'label'
LATENCY = 'latency'
LIMIT = 'limit'
MEAN_DURATION = 'meanDuration'
MEAN_FOREGROUND_TIME = 'meanForegroundTime'
MONEY_VALUE = 'moneyValue'
NAME = 'name'
OS = 'os'
PARAMS = 'params'
PARSEDBREADCRUMBS = 'parsedBreadcrumbs'
RATE = 'rate'
S = 's'
SERIES = 'series'
SERVICE = 'service'
SERVICES = 'services'
SLICES = 'slices'
SORT = 'sort'
START = 'start'
STARTED_TRANSACTIONS = 'startedTransactions'
SUCCEEDED_TRANSACTIONS = 'succeededTransactions'
TYPE = 'type'
U = 'u'
UNIT = 'unit'
US = 'US'
VALUE = 'value'
VERSIONS = 'versions'
VOLUME = 'volume'

SUMMARY_ATTRIBUTES = [
    'appName',
    'appType',
    'appVersions',
    'crashPercent',
    'dau',
    'iconURL',
    'latency',
    'latestAppStoreReleaseDate',
    'latestVersionString',
    'linkToAppStore',
    'mau',
    'rating',
    'role'
]

CRASH_ATTRIBUTES = [
    'displayReason',
    'hash',
    'lastOccurred',
    'name',
    'reason',
    'sessionCount',
    'status',
    'uniqueSessionCount'
]

BASEURL = "https://developers.crittercism.com/v2/"


def apicall_with_response_code(uri, attribs=None):
    # perform an API call
    url = BASEURL + uri

    if debug:
        print u'reqstring is {}'.format(url)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': "Bearer {}".format(access_token),
        'CR-source': 'integration_splunk'
    }

    try:
        response = requests.get(url, headers=headers, params=attribs)
        return response.status_code, response.json()
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


def apipost_with_response_code(uri, postdata=''):
    # perform an API POST
    if (debug): print u'access token is {}'.format(access_token)
    url = BASEURL + uri

    if (debug):
        print u'reqstring is {}'.format(url)
        print u'postdata is {}'.format(postdata)

    pdata = json.dumps(postdata)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': "Bearer {}".format(access_token),
        'CR-source': 'integration_splunk'
    }

    try:
        response = requests.post(url, headers=headers, data=pdata)
        if debug:
            print 'response is {}'.format(response.text)
        return response.status_code, response.json()

    except requests.exceptions.RequestException as e:
        print (u'{} MessageType="ApteligentError" Apteligent API retuned an '
              u'error code: {} for the call to {}.  '
              u'Maybe an ENTERPRISE feature?').format(DATETIME_OF_RUN, e, url)
        return "ERROR"


def apipost(uri, attribs=None):
    http_code, data = apipost_with_response_code(uri, attribs)
    return data


def scopetime():
    # return an ISO8601 timestring based on NOW - Interval
    newtime=(datetime.datetime.utcnow() - datetime.timedelta(minutes=interval))

    return newtime.isoformat()


def getAppSummary():
    # read app summary information.
    # Print out in Splunk KV format.
    # Return a dict with appId and appName.

    params = {ATTRIBUTES: ','.join(SUMMARY_ATTRIBUTES)}
    summary_data = apicall(APPS, params)

    AppDict = {}
    for appId in summary_data[DATA].keys():
        printstring = u'{} MessageType="AppSummary" appId={} '.format(
            DATETIME_OF_RUN, appId
        )

        for attribute_name in SUMMARY_ATTRIBUTES:
            printstring += u'{}="{}"'.format(
                attribute_name,
                summary_data[DATA][appId][attribute_name]
            )
            if attribute_name == APPNAME:
                AppDict[appId] = {
                    NAME: summary_data[DATA][appId][attribute_name],
                    VERSIONS: summary_data[DATA][appId][APPVERSIONS]
                }
        print printstring

    return AppDict


def getCrashSummary(appId, appName):
    # given an appID and an appName, produce a Splunk KV summary of the
    # crashes for a given timeframe

    mystime = scopetime()
    crashdata = None

    http_code = None
    retry = 0
    while http_code != 200:
        http_code, crashdata = apicall_with_response_code(
            "app/crash/summaries/{}".format(
                appId,
                {'lastOccurredStart': mystime}
            )
        )
        retry += 1
        if retry > MAX_RETRY:
            break

    CrashDict = {}
    if http_code != 200:
        print (u'{} MessageType="CrashSummary" appId={} appName="{}" '
              u'Could not get crash summaries for {}. '
              u'Code: {} after retry {}').format(DATETIME_OF_RUN,
                                                appId, appName,
                                                mystime,
                                                http_code,
                                                retry)
    elif crashdata:
        for i, y in enumerate(crashdata[DATA]):
            printstring = (u'{} MessageType="CrashSummary" '
                          u'appId={} appName="{}" ').format(
                DATETIME_OF_RUN, appId, appName
            )
            for attribute_name in CRASH_ATTRIBUTES:
                printstring += u'{}="{}" '.format(
                    attribute_name,
                    crashdata[DATA][i][attribute_name]
                )
                if attribute_name == "hash":
                    CrashDict[crashdata[DATA][i][attribute_name]] = appName
            print printstring
    else:
        print (u'{} MessageType="CrashSummary" appId={} appName="{}" '
              u'No crashes found for {}.').format(DATETIME_OF_RUN,
                                                 appId,
                                                 appName,
                                                 mystime)
    return CrashDict


def getBreadcrumbs(crumbs, crash_hash, appName):
    for crumb in crumbs:
        version = crumb.get(APPVERSIONS)
        os = crumb.get(OS)
        device = crumb.get(DEVICE)
        parsed = json.dumps(crumb[PARSEDBREADCRUMBS])
        parsed = '}|{'.join(parsed.split('}, {'))
        parsed = parsed.replace('{', '')
        parsed = parsed.replace('}', '')
        parsed = parsed.replace('"', "'")
        printstring = (u'{} MessageType="CrashDetailBreadcrumbs" '
                      u'hash={} \ntrace="{}" '
                      u'os="{}" appVersion="{}" device="{}"').format(
                      DATETIME_OF_RUN, crash_hash, parsed, os, version, device)
        print printstring


def getStacktrace(stacktrace, crash_hash):
    print u'{} MessageType="CrashDetailStacktrace"  hash={} '.format(
        DATETIME_OF_RUN,
        crash_hash
    ), pretty(stacktrace)


def diag_geo(data, crash_hash):

    for country in data.keys():
        for city in data[country].keys():
            if city == '--NAME--':
                continue
            (lat,lon,crashes) = (str(data[country][city][0]),
                                str(data[country][city][1]),
                                str(data[country][city][2]))
            print (u'{} MessageType="CrashDiagsGeo" hash={} country="{}" '
                  u'city="{}" lat={} lon={} crashes="{}"').format(DATETIME_OF_RUN,
                                                                 crash_hash,
                                                                 country,
                                                                 city,
                                                                 lat,
                                                                 lon,
                                                                 crashes)


def diag_discrete(data, crash_hash):
    datastring= ""
    for dstat in data.keys():
        for (var,val) in data[dstat]:
            datastring += " \"%s:%s\"=\"%s\"" % (dstat, str(var).replace(" ","_"),str(val))

    print u'{} MessageType="CrashDiagsDiscrete"  hash={} {} '.format(DATETIME_OF_RUN, crash_hash, datastring)


def diag_affected_users(data, crash_hash):
    for uhash in data.keys():
        datastring= ""
        for vhash in data[uhash]:
            datastring += " %s=\"%s\"" % (str(vhash).replace(" ","_"),str(data[uhash][vhash]))

        print u'{} MessageType="CrashDiagsAffectedUser"  hash={}  userhash={} {} '.format(DATETIME_OF_RUN, crash_hash, uhash, datastring)


def diag_affected_versions(data, crash_hash):
    datastring = ""
    for x,vpair in data:
        datastring += " \"%s\"=%s" % (str(x).replace(" ","_"),str(vpair))

    print u'{} MessageType="CrashDiagsAffectedVersions"  hash={} {} '.format(DATETIME_OF_RUN, crash_hash, datastring)


def diag_cont_bar(data, crash_hash):
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

        print u'{} MessageType="CrashDiagsContBar"  hash={} datatype={} {} '.format(DATETIME_OF_RUN, crash_hash, dstat, valstr)


def diag_cont(data, crash_hash):
# Grab all of the continuous data from Apteligent and format into a splunk event
    datastring= ""
    for uhash in data.keys():

        for vhash in data[uhash]:
            datastring += " %s_%s=\"%s\"" % (uhash,str(vhash).replace(" ","_"),str(data[uhash][vhash]))

    print u'{} MessageType="CrashDiagsContinuous"  hash={} {} '.format(DATETIME_OF_RUN, crash_hash, datastring)


#############
def getDiagnostics(diags, crash_hash):
# Dump and prettyprint the diags -- might want to expand on this...
    if not DUMP_DIAGS:
        print u'{} MessageType="CrashDetailDiagnostics" ' \
              u'DISABLED PER CONFIG FILE '.format(DATETIME_OF_RUN, crash_hash)
        return

    for key in diags.keys():
        if key == 'geo_data':
            diag_geo(diags[key], crash_hash)

        elif key == 'discrete_diagnostic_data':
            diag_discrete(diags[key], crash_hash)

        elif key == 'affected_users':
            diag_affected_users(diags[key], crash_hash)

        elif key == 'affected_versions':
            diag_affected_versions(diags[key], crash_hash)

        elif key == 'continuous_bar_diagnostic_data':
            diag_cont_bar(diags[key], crash_hash)

        elif key == 'continuous_diagnostic_data':
            diag_cont(diags[key], crash_hash)

        elif key == 'num_geo_points':
            continue

        elif key == 'discrete_bar_diagnostic_data':
            continue

        else:
            print u'--UNPROCESSED----{} - {}'.format(key, diags[key])


def getDOBV(stacktrace, crash_hash):
# handle the DailyOccurrencesByVersion coming back from a crashdetail
    print u'{} MessageType="CrashDetailDailyOccurrencesByVersion"  hash={} '.format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getUSCBV(stacktrace, crash_hash):
# handle the UniqueSessionCountsByVersion coming back from a crashdetail
    print u'{} MessageType="CrashDetailUniqueSessionCountsByVersion"  hash={} '.format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getSCBV(stacktrace, crash_hash):
# handle the SessionCountsByVersion coming back from a crashdetail
    print u'{} MessageType="CrashDetailSessionCountsByVersion"  hash={} '.format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getSymStacktrace(stacktrace, crash_hash):
# handle the lSymbolizedStacktrace coming back from a crashdetail
    print u'{} MessageType="CrashDetailSymbolizedStacktrace"  hash={} '.format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getCrashDetail(crash_hash, app_id, app_name):
# given a crashhash, get all of the detail about that crash

    crashes = apicall(
        "crash/{}/{}".format(app_id, crash_hash),
        {'diagnostics': True}
    )

    crash_detail = crashes[DATA]
    print_string = u'{} MessageType="CrashDetail"  appName="{}" '.format(
        DATETIME_OF_RUN,
        app_name
    )
    for dkey in crash_detail.keys():
        if dkey == "breadcrumbTraces":
            getBreadcrumbs(crash_detail[dkey], crash_hash, app_name)
        elif dkey == "stacktrace":
            getStacktrace(crash_detail[dkey], crash_hash)
        elif dkey == "diagnostics":
            getDiagnostics(crash_detail[dkey], crash_hash)
        elif dkey == "dailyOccurrencesByVersion":
            getDOBV(crash_detail[dkey], crash_hash)
        elif dkey == "uniqueSessionCountsByVersion":
            getUSCBV(crash_detail[dkey], crash_hash)
        elif dkey == "sessionCountsByVersion":
            getSCBV(crash_detail[dkey], crash_hash)
        elif dkey == "symbolizedStacktrace":
            getSymStacktrace(crash_detail[dkey], crash_hash)
        else:
            print_string += u'{}="{}" '.format(dkey, crash_detail[dkey])
    print print_string


def getErrorSummary(appId,appName) :
# Grab the elements we need from errorMonitoring endpoint
# errorSummary is returned as a post...

# Get the current app loads
    params = {
        APPID: appId,
        GRAPH: APPLOADS,
        DURATION: 43200
    }

    app_load_sum = apicall("errorMonitoring/graph", params)

    dlist = app_load_sum[DATA][SERIES][0]['points']
    print u'{} MessageType=HourlyAppLoads AppLoads={} appId="{}" appName="{}"'.format(DATETIME_OF_RUN, dlist[len(dlist) - 1], appId, appName)


def getCrashesByOS(appId, appName):
    """Get the number of crashes for a given app sorted by OS."""

    params = {
            GRAPH: CRASHES,
            DURATION: 1440,
            GROUPBY: OS,
            APPID: appId
            }

    crashesos = apicall("errorMonitoring/pie", params)
    # is user does not have pro access for a given application, this fails.
    if crashesos == "ERROR":
        return None, None

    print_string = u''
    try:
        for series in crashesos[DATA][SLICES]:
            print_string += u'("{}",{}),'.format(series[LABEL], series[VALUE])

        print u'{} MessageType=DailyCrashesByOS appName="{}" appId="{}" DATA {}'.format(DATETIME_OF_RUN, appName, appId, print_string)
        return

    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_crashes_by_os')
        return None, None


"""--------------------------------------------------------------"""
def getGenericPerfMgmt(appId, appName, graph, groupby, messagetype):
    """Generic data return for performanceManagement/pie end point."""

    params = {
        GROUPBY: groupby,
        GRAPH: graph,
        DURATION: 1440,
        APPID: appId
        }

    server_errors = apicall("performanceManagement/pie", params)

#    print "%s DEBUG Into getGenericPerfMgmt appId = %s  appName = %s graph= %s groupby = %s messagetype = %s" %(DATETIME_OF_RUN, appId, appName,graph,groupby,messagetype)

    print_string = u''
    try:
        slices = server_errors[DATA][SLICES]
        if slices:
            for series in server_errors[DATA][SLICES]:
                print_string += u'("{}",{}),'.format(series[LABEL], series[VALUE])

            print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(DATETIME_OF_RUN, messagetype, appName, appId, print_string)
        else:
            print u'{} MessageType="ApteligentError" Error: API did not return {} data for {}. Returned {}'.format(DATETIME_OF_RUN, messagetype, appId, server_errors['data'])
    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: API returned malformed data in {} of {}. Data: {}'.format(DATETIME_OF_RUN, str(e), messagetype, server_errors)
        return (None, None)


def getAPMEndpoints(app_id, app_name, sort, message_type):
    """Get APM Endpoint data."""

    params = {
                APPID: app_id,
                SORT: sort,
                LIMIT: 10,
                DURATION: 240,
                GEOMODE: True
            }

    response = apicall("performanceManagement/endpoints", params)

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
            APPID: app_id,
            SORT: sort,
            LIMIT: 10,
            DURATION: 240,
            GEOMODE: True
        }

    response = apicall("performanceManagement/services", params)

    try:
        messages = u','.join([u'("{}",{})'.format(service[NAME], service[SORT]) for service in
                              response[DATA][SERVICES]])
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), message_type))
        return None, None


def getAPMGeo(app_id, app_name, graph, message_type):
    """Get APM geographical data"""

    params = {
            APPID: app_id,
            GRAPH: graph,
            LIMIT: 10,
            DURATION: 240,
        }

    response = apicall("performanceManagement/geo", params)

    try:
        messages = u','.join([u'("{}",{})'.format(location, data) for location, data in
                      response[DATA][SERIES][0][GEO].iteritems()])
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, str(e), message_type))
        return None, None


def getGenericErrorMon(appId, appName,graph,groupby,messagetype):
    """Generic data return for errorMonitoring/pie end point."""

    params = {
        GROUPBY: groupby,
        GRAPH: graph,
        DURATION: 1440,
        APPID: appId
        }

    server_errors = apicall("errorMonitoring/pie",params)

    # print "{} DEBUG Into getGenericErrorMon appId = {}  appName = {} graph= {} groupby = {} messagetype = {} DATA {}".format(DATETIME_OF_RUN, appId, appName,graph,groupby,messagetype, server_errors)

    mystring = u''
    try:
        slices = server_errors[DATA][SLICES]
        if slices:
            for series in slices:
                mystring += u'("{}",{}),'.format(series[LABEL], series[VALUE])

            print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(DATETIME_OF_RUN, messagetype, appName, appId, mystring)
        else:
            print u'{} MessageType="ApteligentError" Error: API did not return {} data for {}. Returned {}'.format(DATETIME_OF_RUN, messagetype, appId, server_errors[DATA])

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
    userflow_data = response[DATA]
    print "USERFLOWS SUMMARY DATA", userflow_data

    try:
        messages = u','.join([u'("{}",{},{})'.format(metric, data[VALUE], data[CHANGE_PCT]) for metric, data in
                              userflow_data.iteritems()])
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
    userflow_data = response[DATA]

    try:
        messages = u','.join([u'("{}",{},{})'.format(group[NAME], group[FAILURE_RATE], group[UNIT][TYPE]) for group in
                              userflow_data])
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
    uri = 'transactions/{}/details/change/P1M'.format(app_id)
    params = {'pageNum': 1,
             'pageSize': 10,
             'sortBy': 'name',
             'sortOrder': 'ascending'}

    response = apicall(uri, params)
    userflow_data = response[DATA]

    getUserflowsChangeDetails(app_id, app_name, userflow_data)

    for group in userflow_data:
        getUserflowsGroups(app_id, app_name, group[NAME])


def getUserflowsChangeDetails(app_id, app_name, userflow_dict):
    """Process the userflows details/change data for Splunk

    :param app_id: (string) App ID used to request data from the API
    :param app_name: (string) Human-readable app name
    :return: None
    """

    try:
        for group in userflow_dict:
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
    userflow_data = response[DATA]

    try:
        for transaction in userflow_data[SERIES].keys():
            messages = u''
            messages += u'(Metric="{}",count={},rate={}%,moneyValue=${},meanDuration={})'.format(
                transaction,
                userflow_data[SERIES][transaction][COUNT][VALUE],
                userflow_data[SERIES][transaction][RATE][VALUE],
                userflow_data[SERIES][transaction][MONEY_VALUE][VALUE],
                userflow_data[SERIES][transaction][MEAN_DURATION][VALUE])
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


def getDailyAppLoads(appId, appName):
    """Get the number of daily app loads for a given app."""

    params = {
        GRAPH: APPLOADS,
        DURATION: 1440,
        APPID: appId,
        }

    apploadsD = apicall("errorMonitoring/graph", params)

    try:
        print u'{} MessageType=DailyAppLoads appName="{}" appId="{}" dailyAppLoads={}'.format(DATETIME_OF_RUN, appName, appId, apploadsD[DATA][SERIES][0]['points'][0])
    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_daily_app_loads')
        return None


def getDailyCrashes(appId, appName):
    """Get the number of daily app crashes for a given app."""
    """good candidate for 'backfill' data if needed"""

    crashdata = apicall("app/%s/crash/counts" % appId)[DATA]

    try:
        print u'{} MessageType=DailyCrashes appName="{}" appId="{}" dailyCrashes={}'.format(DATETIME_OF_RUN, appName, appId, crashdata[len(crashdata) - 1][VALUE])
    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_daily_crashes')
        return None

    return


def getTrends(appId, appName):
    """Calls the trends endpoint for an app

    :param appId: (string) App ID used to request data from the API
    :param appName: (string) Human-readable app name
    :return: None
    """
    print u'MessageType="ApteligentDebug" getTrends for {}'.format(appId)

    trends = apicall(u'trends/{}'.format(appId))
    trends_data = trends[DATA]

    getTopValues(appId, appName, trends_data)
    getTimeseriesTrends(appId, appName, trends_data)


def getTopValues(appId, appName, trendsData):
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
        for version, value in trendsData[SERIES][trend]['todayTopValues'].iteritems():
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

    for version in trendsData[SERIES][CRASHESBYVERSION][CATEGORIES].keys():
        messages = u''
        for bucket in trendsData[SERIES][CRASHESBYVERSION][CATEGORIES][version]['buckets']:
            messages += u'({},{}),'.format(bucket[START][:10], bucket[VALUE])
        try:
            print u'{} MessageType={} appName="{}" appId="{}" appVersion="{}" DATA {}'.format(DATETIME_OF_RUN, "TimeseriesTrends",
                                                                                              appName, appId, version, messages)
        except KeyError as e:
            print u'{} MessageType="ApteligentError" Error: Could not access {} in {}.'.format(DATETIME_OF_RUN, str(e), 'TimeseriesTrends')
    return

def getCrashCounts(appId, appName):
    """Get the number of daily app crashes for a given app."""
    """good candidate for 'backfill' data if needed"""

    crash_data = apicall("app/crash/counts/{}".format(appId))

    print_string = u''

    try:
        for series in crash_data[DATA]:
            print_string += u'({},{}),'.format(series[DATE], series[VALUE])

        print u'{} MessageType=CrashCounts appName="{}" appId="{}" DATA ' \
              u'{}'.format(DATETIME_OF_RUN, appName, appId, print_string)

    except KeyError as e:
        print u'{} MessageType="ApteligentError" Error: Could not access ' \
              u'{} in {}.'.format(DATETIME_OF_RUN, str(e), 'get_crash_counts')
        return None

    return


def getCredentials(sessionKey):
# access the credentials in /servicesNS/nobody/<MyApp>/admin/passwords

    if debug:
        print u'{} MessageType="ApteligentDebug"  Into getCredentials'.format(
            DATETIME_OF_RUN
        )

    auth = None
    entities = None
    retry = 1

    while auth is None and retry < MAX_RETRY:
        if debug:
            print u'Attempt to get credentials {}'.format(retry)
        try:
            # list all credentials
            entities = entity.getEntities(
                ['admin', 'passwords'],
                namespace=myapp,
                owner='nobody',
                sessionKey=sessionKey)
        except Exception, e:
            print (u'{} MessageType="ApteligentDebug" '
                   u'Could not get {} credentials from splunk. '
                   u'Error: {}'.format(DATETIME_OF_RUN, myapp, str(e)))

        # return first set of credentials
        if debug:
            print "Entities is ", entities
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


def parse_arguments_for_debugging():
    """
    Capture command line arguments in order to run the script
    outside of Splunk.
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--token')
    args = parser.parse_args()
    if args.debug:
        return args.token, args.debug
    else:
        return None, None

###########


def main(access_token=None, debug=None):
    #read session key sent from splunkd
    if debug:
        sessionKey = "bogus_session_key_for_debugging"
    else:
        sessionKey = sys.stdin.readline().strip()

    if debug:
        print u'{} MessageType="ApteligentDebug" sessionKey is {}'.format(
            DATETIME_OF_RUN,
            sessionKey
        )

    if len(sessionKey) == 0:
        print u'{} MessageType="ApteligentError" ' \
              u'Did not receive a session key from splunk. '.format(
               DATETIME_OF_RUN
               )
        exit(2)

    # now get crittercism oauth token
    if not access_token:
        access_token = getCredentials(sessionKey)

    if debug:
        print u'{} MessageType="ApteligentDebug" OAuth token is {}'.format(
            DATETIME_OF_RUN,
            access_token
        )

# Get application summary information.
    apps = getAppSummary()
    for key in apps.keys():
        crashes = getCrashSummary(key, apps[key][NAME])
        if crashes:
            for ckey in crashes.keys():
                getCrashDetail(ckey, key, apps[key][NAME])

        getTrends(key, apps[key][NAME])

        getDailyAppLoads(key, apps[key][NAME])
        getDailyCrashes(key, apps[key][NAME])
        getCrashCounts(key, apps[key][NAME])

        getGenericPerfMgmt(key, apps[key][NAME], VOLUME, DEVICE, 'DailyVolumeByDevice')
        getGenericPerfMgmt(key, apps[key][NAME], ERRORS, SERVICE, 'DailyServiceErrorRates')
        getGenericPerfMgmt(key, apps[key][NAME], VOLUME, OS, 'DailyVolumeByOS')
        getGenericPerfMgmt(key, apps[key][NAME], VOLUME, APPVERSION, 'VolumeByAppVersion')

        getGenericErrorMon(key, apps[key][NAME], CRASHES, DEVICE, 'CrashesByDevice')
        getGenericErrorMon(key, apps[key][NAME], CRASHPERCENT, DEVICE, 'CrashPerByDevice')
        getGenericErrorMon(key, apps[key][NAME], APPLOADS, OS, 'ApploadsByOs')
        getGenericErrorMon(key, apps[key][NAME], CRASHES, OS, 'DailyCrashesByOs')
        getGenericErrorMon(key, apps[key][NAME], CRASHPERCENT, OS, 'CrashPerByOs')
        getGenericErrorMon(key, apps[key][NAME], CRASHPERCENT, APPVERSION, 'CrashPerByAppVersion')
        getGenericErrorMon(key, apps[key][NAME], CRASHES, APPVERSION, 'CrashByAppVersion')
        getGenericErrorMon(key, apps[key][NAME], APPLOADS, APPVERSION, 'LoadsByAppVersion')
        getGenericErrorMon(key, apps[key][NAME], DAU, APPVERSION, 'DauByAppVersion')
        getGenericErrorMon(key, apps[key][NAME], APPLOADS, DEVICE, 'ApploadsByDevice')

        getAPMEndpoints(key, apps[key][NAME], LATENCY, 'ApmEndpointsLatency')
        getAPMEndpoints(key, apps[key][NAME], VOLUME, 'ApmEndpointsVolume')
        getAPMEndpoints(key, apps[key][NAME], ERRORS, 'ApmEndpointsErrors')
        getAPMEndpoints(key, apps[key][NAME], DATA, 'ApmEndpointsData')

        getAPMServices(key, apps[key][NAME], LATENCY, 'ApmServicesLatency')
        getAPMServices(key, apps[key][NAME], VOLUME, 'ApmServicesVolume')
        getAPMServices(key, apps[key][NAME], ERRORS, 'ApmServicesErrors')
        getAPMServices(key, apps[key][NAME], DATA, 'ApmServicesData')

        getAPMGeo(key, apps[key][NAME], LATENCY, 'ApmGeoLatency')
        getAPMGeo(key, apps[key][NAME], VOLUME, 'ApmGeoVolume')
        getAPMGeo(key, apps[key][NAME], ERRORS, 'ApmGeoErrors')
        getAPMGeo(key, apps[key][NAME], DATA, 'ApmGeoData')

        getUserflowsSummary(key, apps[key][NAME], 'UserflowsSummary')
        getUserflowsRanked(key, apps[key][NAME], FAILED, 'UserflowsRankedFailed')
        getUserflowsDetails(key, apps[key][NAME])

if __name__=='__main__':
    access_token, debug = parse_arguments_for_debugging()
    main(access_token, debug)
