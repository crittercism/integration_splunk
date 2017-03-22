#!/usr/bin/python
import datetime
import json
import os
import sys
import time
import requests

try:
    import splunk.entity as entity
except ImportError:
    import splunk_mock.entity as entity

# The splunk name for the app. Needed for the auth storage
myapp = 'crittercism_integration'

DUMP_DIAGS = 1
INTERVAL = 10  # minutes between runs of this script as performed by Splunk
MAX_RETRY = 10
ACCESS_TOKEN = ''
DEBUG = os.environ.get('CR_SPLUNK_DEBUG')

TODAY = datetime.datetime.utcnow()  # calculate a common time for all summary data
DATETIME_OF_RUN = TODAY.strftime('%Y-%m-%d %H:%M:%S +0000')

# a quick command to format quasi json output nicely
#TODO (sf) figure out what this does and then find a better way
pretty = (lambda a: lambda v, t="\t", n="\n", i=0: a(a, v, t, n, i))(lambda f, v, t, n, i: "{%s%s%s}" % (",".join(["%s%s%s: %s" % (n, t * (i + 1), repr(k), f(f, v[k], t, n, i + 1)) for k in v]), n, (t * i)) if type(v) in [dict] else (type(v) in [list] and "[%s%s%s]" or "(%s%s%s)") % (",".join(["%s%s%s" % (n, t *(i + 1), f(f, k, t, n, i + 1)) for k in v]), n, (t * i)) if type(v) in [list, tuple] else repr(v))

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
CRASH = 'crash'
CRASHES = 'crashes'
CRASHESBYVERSION = 'crashesByVersion'
CRASHPERCENT = 'crashPercent'
DATA = 'data'
DATE = 'date'
DAU = 'dau'
DEVICE = 'device'
DISPATCH = 'dispatch'
DOMAIN = 'domain'
DURATION = 'duration'
ENDPOINTS = 'endpoints'
ENTRY = 'entry'
ERRORS = 'errors'
EXCEPTION = 'exception'
GEO = 'geo'
GEOMODE = 'geoMode'
GET = 'GET'
GRAPH = 'graph'
GROUPBY = 'groupBy'
GROUPS = 'groups'
FAILED = 'failed'
FAILED_MONEY_VALUE = 'failedMoneyValue'
FAILED_TRANSACTIONS = 'failedTransactions'
FAIL_RATE = 'failRate'
FAILURE_RATE = 'failureRate'
FILTERS = 'filters'
HASH = 'hash'
JSON = 'json'
LABEL = 'label'
LAST_APPS_CALL = 'last_apps_call'
LAST_CRASH_DETAILS_CALL = 'last_crash_details_call'
LAST_TRENDS_CALL = 'last_trends_call'
LATENCY = 'latency'
LIMIT = 'limit'
LINKS = 'links'
MEAN_DURATION = 'meanDuration'
MEAN_FOREGROUND_TIME = 'meanForegroundTime'
MONEY_VALUE = 'moneyValue'
NAME = 'name'
OS = 'os'
OUTPUT_MODE = 'output_mode'
PARAMS = 'params'
PARSEDBREADCRUMBS = 'parsedBreadcrumbs'
POST = 'POST'
RATE = 'rate'
RESULTS = 'results'
SERIES = 'series'
SERVICE = 'service'
SERVICES = 'services'
SID = 'sid'
SLICES = 'slices'
SORT = 'sort'
START = 'start'
STARTED_TRANSACTIONS = 'startedTransactions'
SUCCEEDED_TRANSACTIONS = 'succeededTransactions'
TYPE = 'type'
UNIT = 'unit'
URI = 'uri'
US = 'US'
VALUE = 'value'
VERSIONS = 'versions'
VOLUME = 'volume'
UNDERSCORE_TIME = '_time'

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

ERROR_ATTRIBUTES = [
    'displayReason',
    'hash',
    'lastOccurred',
    'name',
    'reason',
    'sessionCount',
    'status',
    'uniqueSessionCount'
]

BASEURL = 'https://developers.crittercism.com/v2/'

ALL_CALLS = []


def apicall_with_response_code(uri, attribs=None):
    """Call the Apteligent API

    Args:
        uri: string
        attribs: dict

    Returns:
        status_code string and json object of data from the endpoint
    """
    ALL_CALLS.append(uri)

    url = BASEURL + uri

    if DEBUG:
        print u'reqstring is {}'.format(url)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': "Bearer {}".format(ACCESS_TOKEN),
        'CR-source': 'integration_splunk'
    }

    try:
        response = requests.get(url, headers=headers, params=attribs)
    except requests.exceptions.Timeout as error:
        print 'Connection timeout. Apteligent API returned an error code:', error
        sys.exit(0)
    except requests.exceptions.ConnectionError as error:
        print 'Connection error. Apteligent API returned an error code:', error
        sys.exit(0)
    except requests.exceptions.HTTPError as error:
        print 'HTTP error. Apteligent API returned an error code:', error
        sys.exit(0)
    except requests.exceptions.RequestException as error:
        print 'Apteligent API retuned an error code:', error
        sys.exit(0)

    if response.status_code == 200:
        return response.status_code, response.json()
    else:
        return response.status_code, None


def splunk_api_call(uri, method, session_key):
    """Connect to the local Splunk API

    Args:
        uri: string, Splunk API endpoint
        method: string, either GET or POST
        session_key: string, auth token for Splunk
    Returns:
        A dict of data from the response object
    """
    url = 'https://localhost:8089{}'.format(uri)
    headers = {'Authorization': 'Splunk {}'.format(session_key)}
    params = {OUTPUT_MODE: JSON}
    splunk_response = None

    try:
        splunk_response = requests.request(method, url,
                                           params=params,
                                           headers=headers,
                                           verify=False)
    except requests.exceptions.Timeout as error:
        print 'Connection timeout. Splunk API returned an error code:', error
    except requests.exceptions.ConnectionError as error:
        print 'Connection error. Splunk API returned an error code:', error
    except requests.exceptions.HTTPError as error:
        print 'HTTP error. Splunk API returned an error code:', error
    except requests.exceptions.RequestException as error:
        print 'Splunk API returned an error code:', error

    return splunk_response.json()


def run_splunk_search(search_name, session_key):
    """Dispatches a saved search via Splunk's API and returns the results.

    Args:
        search_name: string, the name of the saved search
        session_key: string, auth token for Splunk

    Returns:
        None or a dictionary of search results
    """
    saved_searches_uri = ('/servicesNS/admin/'
                          'crittercism_integration/saved/searches')
    search_jobs_uri = '/services/search/jobs/{}/results'
    dispatch_url = None

    all_saved_searches = splunk_api_call(saved_searches_uri, GET, session_key)

    for entry in all_saved_searches[ENTRY]:
        if entry[NAME] == search_name:
            dispatch_url = entry[LINKS][DISPATCH]

    if dispatch_url:
        r = splunk_api_call(dispatch_url, POST, session_key)
        sid = r[SID]
        time.sleep(1)  # This lets Splunk finish running the search
    else:
        print (u'{} MessageType="ApteligentError" Error: '
               u'No saved searches returned by Splunk'.format(DATETIME_OF_RUN))
        return

    if sid:
        search_url = search_jobs_uri.format(sid)
        search_results = splunk_api_call(search_url, GET, session_key)
    else:
        print (u'{} MessageType="ApteligentError" Error: '
               u'Could not dispatch search'.format(DATETIME_OF_RUN))
        return

    return search_results


def get_last_run_times(session_key):
    """Retrieve the last time the connector ran from Splunk's API

    Args:
        session_key: string, auth token for Splunk

    Returns:
        datetime object, time of last run, or None
    """

    searches = {LAST_APPS_CALL: datetime.timedelta(days=0),
                LAST_TRENDS_CALL: datetime.timedelta(days=0),
                LAST_CRASH_DETAILS_CALL: datetime.timedelta(days=0)}

    for search in searches.keys():
        search_results = run_splunk_search(search, session_key)

        if not search_results or not search_results.get(RESULTS):
            print (u'{} MessageType="ApteligentError" Error: '
                   u'Could not get last run time for {}'.format(
                       DATETIME_OF_RUN,
                       search)
                   )
        else:
            last_run_string = search_results[RESULTS][0][UNDERSCORE_TIME]

            try:
                last_run_time = datetime.datetime.strptime(
                    last_run_string,
                    '%Y-%m-%dT%H:%M:%S.%f+00:00'
                )
                searches[search] = last_run_time
            except Exception as e:
                print (u'{} MessageType="ApteligentError" Error: '
                       u'Time formatting error: {} formatting {}'.format(
                        DATETIME_OF_RUN,
                        e,
                        last_run_string)
                       )
    return searches


def call_manager(session_key):
    """Make calls based on the time of the last run

    Based on the last time the connector ran, figure out which calls should
    be made to the Apteligent API

    TODO: This function is a stub that will be hooked to factories for
    Apteligent API calls, once those are built.

    Args:
        session_key: string, auth token for Splunk
    """
    last_runs = get_last_run_times(session_key)

    if not last_runs.get(LAST_APPS_CALL):
        calls_to_run = ['basic calls', 'hour calls', 'daily calls']
        print (u'{} MessageType="ApteligentTimestamp" LastRunTimes="{}" '
               u'Running {}'.format(
                   DATETIME_OF_RUN,
                   last_runs,
                   calls_to_run)
              )
        return
    else:
        calls_to_run = ['basic calls']

    if last_runs.get(LAST_TRENDS_CALL):
        time_since_trends = TODAY - last_runs[LAST_TRENDS_CALL]
        if time_since_trends > datetime.timedelta(hours=1):
            calls_to_run.append('hour calls')

    if last_runs.get(LAST_CRASH_DETAILS_CALL):
        time_since_crash_details = TODAY - last_runs[LAST_CRASH_DETAILS_CALL]
        if time_since_crash_details > datetime.timedelta(days=1):
            calls_to_run.append('daily calls')

    print (u'{} MessageType="ApteligentTimestamp" LastRunTime="{}" '
           u'Running {}'.format(
               DATETIME_OF_RUN,
               last_runs,
               calls_to_run)
          )


def apicall(uri, attribs=None):
    """For API calls that do not need to know their http response code

    Args:
        uri: string
        attribs: dict

    Returns:
        json object of data from the endpoint
    """
    _, data = apicall_with_response_code(uri, attribs)
    return data


def scopetime():
    """Return an ISO8601 timestring based on NOW - Interval

    Returns:
        string, time in ISO format
    """
    newtime = (
        datetime.datetime.utcnow() -
        datetime.timedelta(
            minutes=INTERVAL))

    return newtime.isoformat()


def getAppSummary():
    """Transmit app summary data
    Read app summary information. Print out in Splunk KV format.
    Return a dict with appId and appName.

    Returns:
        dict
    """


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


def get_error_summary(app_id, app_name, error_type):
    """Transmit crash or exception summary data

    Args:
        app_id: string for API call
        app_name: string for Splunk
        error_type: string, either 'crash' or 'exception'

    Returns:
        dict of error hashes mapped to app IDs
    """

    start_time = scopetime()
    error_data = None

    if error_type == 'crash':
        summary_uri = 'app/crash/summaries/{}'.format(app_id)
        error_type_message = 'CrashSummary'
    elif error_type == 'exception':
        summary_uri = 'app/exception/summaries/{}'.format(app_id)
        error_type_message = 'ExceptionSummary'
    else:
        print (u'{} MessageType="ApteligentError" Cannot get error summaries.'
               u'No error type provided.').format(DATETIME_OF_RUN)
        return

    http_code = None
    retry = 0
    while http_code != 200:
        http_code, error_data = apicall_with_response_code(
            summary_uri,
            {'lastOccurredStart': start_time}
        )
        retry += 1
        if retry > MAX_RETRY:
            break

    all_errors = {}
    if http_code == 200 and error_data:
        for error in error_data[DATA]:
            printstring = (u'{} MessageType="{}" '
                           u'appId={} appName="{}" ').format(
                               DATETIME_OF_RUN, error_type_message, app_id, app_name
                           )
            for attribute_name in ERROR_ATTRIBUTES:
                printstring += u'{}="{}" '.format(
                    attribute_name,
                    error[attribute_name]
                )
                if attribute_name == HASH:
                    all_errors[error[attribute_name]] = app_name
            print printstring
    elif http_code != 200:
        print (u'{} MessageType="{}" appId={} appName="{}" '
               u'Could not get error summaries for {}. '
               u'Code: {} after retry {}').format(DATETIME_OF_RUN,
                                                  error_type_message,
                                                  app_id,
                                                  app_name,
                                                  start_time,
                                                  http_code,
                                                  retry)
    elif not error_data:
        print (u'{} MessageType="{}" appId={} appName="{}" '
               u'No crashes found for {}.').format(DATETIME_OF_RUN,
                                                   error_type_message,
                                                   app_id,
                                                   app_name,
                                                   start_time)
    return all_errors


def get_breadcrumbs(crumbs, crash_hash, appName):
    for crumb in crumbs:
        version = crumb.get(APPVERSION)
        device_os = crumb.get(OS)
        device = crumb.get(DEVICE)
        parsed = json.dumps(crumb[PARSEDBREADCRUMBS])
        parsed = '}|{'.join(parsed.split('}, {'))
        parsed = parsed.replace('{', '')
        parsed = parsed.replace('}', '')
        parsed = parsed.replace('"', "'")
        printstring = (u'{} MessageType="CrashDetailBreadcrumbs" '
                       u'hash={} \ntrace="{}" '
                       u'os="{}" appVersion="{}" device="{}"').format(
                           DATETIME_OF_RUN,
                           crash_hash,
                           parsed,
                           device_os,
                           version,
                           device
                       )
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
            (lat, lon, crashes) = (data[country][city][0],
                                   data[country][city][1],
                                   data[country][city][2])
            print (u'{} MessageType="CrashDiagsGeo" hash={} country="{}" '
                   u'city="{}" lat={} lon={} crashes="{}"').format(DATETIME_OF_RUN,
                                                                   crash_hash,
                                                                   country,
                                                                   city,
                                                                   lat,
                                                                   lon,
                                                                   crashes)


def diag_discrete(data, crash_hash):
    datastring = ""
    for dstat in data.keys():
        for (var, val) in data[dstat]:
            datastring += u' "{}:{}"="{}"'.format(dstat,
                                                  var.replace(" ", "_"),
                                                  val)

    print (u'{} MessageType="CrashDiagsDiscrete"  hash={} {} ').format(
        DATETIME_OF_RUN,
        crash_hash,
        datastring
    )


def diag_affected_users(data, crash_hash):
    for uhash in data.keys():
        datastring = u''
        for vhash in data[uhash]:
            datastring += u' {}="{}"'.format(vhash.replace(" ", "_"),
                                             data[uhash][vhash])

        print (u'{} MessageType="CrashDiagsAffectedUser"  hash={}  '
               u'userhash={} {} ').format(DATETIME_OF_RUN,
                                          crash_hash,
                                          uhash,
                                          datastring)


def diag_affected_versions(data, crash_hash):
    datastring = u''
    for x, vpair in data:
        datastring += ' "{}"={}'.format(x.replace(" ", "_"),
                                        vpair)

    print (u'{} MessageType="CrashDiagsAffectedVersions"  '
           u'hash={} {} ').format(DATETIME_OF_RUN, crash_hash, datastring)


def diag_cont_bar(data, crash_hash):
    # The continuous_bar_diagnostic_data data comes back as two arrays per datapoint
    # we Zip them back together to make them KV for Splunk

    for dstat in data.keys():
        x = 0
        valstr = u''
        tmp = {}
        for vstat in data[dstat]:
            tmp[x] = data[dstat][vstat]
            x += 1
        zipped = zip(tmp[1], tmp[0])
        for var, val in zipped:
            valstr += u' "{}"={}'.format(val, var)

        print (u'{} MessageType="CrashDiagsContBar"  hash={} '
               u'datatype={} {} ').format(DATETIME_OF_RUN,
                                          crash_hash,
                                          dstat,
                                          valstr)


def diag_cont(data, crash_hash):
    # Grab all of the continuous data from Apteligent and format into a splunk
    # event
    datastring = u''
    for uhash in data.keys():

        for vhash in data[uhash]:
            datastring += u' {}_{}="{}"'.format(uhash,
                                                vhash.replace(" ", "_"),
                                                data[uhash][vhash])

    print (u'{} MessageType="CrashDiagsContinuous"  '
           u'hash={} {} ').format(DATETIME_OF_RUN, crash_hash, datastring)


#############
def getDiagnostics(diags, crash_hash):
    # Dump and prettyprint the diags -- might want to expand on this...
    if not DUMP_DIAGS:
        print (u'{} MessageType="CrashDetailDiagnostics" '
               u'DISABLED PER CONFIG FILE ').format(DATETIME_OF_RUN)
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
    print (u'{} MessageType="CrashDetailDailyOccurrencesByVersion"  '
           u'hash={} ').format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getUSCBV(stacktrace, crash_hash):
    # handle the UniqueSessionCountsByVersion coming back from a crashdetail
    print (u'{} MessageType="CrashDetailUniqueSessionCountsByVersion"  '
           u'hash={} ').format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getSCBV(stacktrace, crash_hash):
    # handle the SessionCountsByVersion coming back from a crashdetail
    print (u'{} MessageType="CrashDetailSessionCountsByVersion"  '
           u'hash={} ').format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getSymStacktrace(stacktrace, crash_hash):
    # handle the lSymbolizedStacktrace coming back from a crashdetail
    print (u'{} MessageType="CrashDetailSymbolizedStacktrace"  '
           u'hash={} ').format(DATETIME_OF_RUN, crash_hash), pretty(stacktrace)


def getCrashDetail(crash_hash, app_id, app_name):
    # given a crashhash, get all of the detail about that crash

    crashes = apicall(
        "crash/{}/{}".format(app_id, crash_hash),
        {'diagnostics': True}
    )

    if crashes:
        crash_detail = crashes[DATA]
    else:
        print (u'{} MessageType=ApteligentError No details found for crash {}'
               u'in app {} ({})').format(DATETIME_OF_RUN,
                                         crash_hash,
                                         app_name,
                                         app_id)
        return
    print_string = u'{} MessageType="CrashDetail"  appName="{}" '.format(
        DATETIME_OF_RUN,
        app_name
    )
    for dkey in crash_detail.keys():
        if dkey == "breadcrumbTraces":
            get_breadcrumbs(crash_detail[dkey], crash_hash, app_name)
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


def getErrorSummary(appId, appName):
    """Grab the elements we need from errorMonitoring endpoints

    Args:
        appId:
        appName:

    Returns:
        None
    """
    params = {
        APPID: appId,
        GRAPH: APPLOADS,
        DURATION: 43200
    }

    app_load_sum = apicall("errorMonitoring/graph", params)

    dlist = app_load_sum[DATA][SERIES][0]['points']
    print (u'{} MessageType=HourlyAppLoads AppLoads={} appId="{}" '
           u'appName="{}"').format(DATETIME_OF_RUN,
                                   dlist[len(dlist) - 1],
                                   appId,
                                   appName)


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

        print (u'{} MessageType=DailyCrashesByOS appName="{}" appId="{}" '
               u'DATA {}').format(DATETIME_OF_RUN,
                                  appName,
                                  appId,
                                  print_string)
        return

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: '
               u'Could not access {} in {}.').format(DATETIME_OF_RUN,
                                                     e,
                                                     'get_crashes_by_os')
        return None, None


# --------------------------------------------------------------


def getGenericPerfMgmt(appId, appName, graph, groupby, messagetype):
    """Generic data return for performanceManagement/pie end point."""

    params = {
        GROUPBY: groupby,
        GRAPH: graph,
        DURATION: 1440,
        APPID: appId
    }

    server_errors = apicall("performanceManagement/pie", params)

    print_string = u''
    try:
        slices = server_errors[DATA][SLICES]
        if slices:
            for series in server_errors[DATA][SLICES]:
                print_string += u'("{}",{}),'.format(
                    series[LABEL], series[VALUE])

            print (u'{} MessageType={} appName="{}" appId="{}"  '
                   u'DATA {}').format(DATETIME_OF_RUN,
                                      messagetype,
                                      appName,
                                      appId,
                                      print_string)
        else:
            print (u'{} MessageType="ApteligentError" Error: '
                   u'API did not return {} data for {}. Returned {}').format(
                       DATETIME_OF_RUN,
                       messagetype,
                       appId,
                       server_errors['data']
                   )
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: '
               u'API returned malformed data in {} of {}. Data: {}').format(
                   DATETIME_OF_RUN,
                   e,
                   messagetype,
                   server_errors
               )
        return None, None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: API did not return '
               u'data in {} of {}.').format(
                   DATETIME_OF_RUN,
                   e,
                   messagetype
               )
        return None, None



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
        messages = u','.join([u'("{}{}",{})'.format(ep[DOMAIN], ep[URI], ep[SORT]) for ep in
                              response[DATA][ENDPOINTS]])
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, e, message_type))
        return None, None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: No data returned for '
               u'{} in {}.'.format(DATETIME_OF_RUN, e, message_type))
        return None, None



def getAPMServices(app_id, app_name, sort, message_type):
    """Get APM services data

    Args:
        app_id: string
        app_name: string
        sort: string, sort metric for the API
        message_type: string, message type to print

    Returns:
        None
    """

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
               u'in {}.'.format(DATETIME_OF_RUN, e, message_type))
        return None, None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: {} '
               u'no data returned for {}.'.format(DATETIME_OF_RUN,
                                                  e,
                                                  message_type))
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
               u'in {}.'.format(DATETIME_OF_RUN, e, message_type))
        return None, None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: {} '
               u'no data returned for {}.'.format(DATETIME_OF_RUN,
                                                  e,
                                                  message_type))
        return None, None



def getGenericErrorMon(appId, appName, graph, groupby, messagetype):
    """Generic data return for errorMonitoring/pie end point."""

    params = {
        GROUPBY: groupby,
        GRAPH: graph,
        DURATION: 1440,
        APPID: appId
    }

    server_errors = apicall("errorMonitoring/pie", params)

    mystring = u''
    try:
        slices = server_errors[DATA][SLICES]
        if slices:
            for series in slices:
                mystring += u'("{}",{}),'.format(series[LABEL], series[VALUE])

            print (u'{} MessageType={} appName="{}" appId="{}"  '
                   u'DATA {}').format(DATETIME_OF_RUN,
                                      messagetype,
                                      appName,
                                      appId,
                                      mystring)
        else:
            print (u'{} MessageType="ApteligentError" Error: '
                   u'API did not return {} data for {}. Returned {}').format(
                       DATETIME_OF_RUN,
                       messagetype,
                       appId,
                       server_errors[DATA]
                   )

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: '
               u'API returned malformed data in {} of {}. Data: {}').format(
                   DATETIME_OF_RUN,
                   e,
                   messagetype,
                   server_errors
               )
        return None, None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: '
               u'API did not return data in {} of {}.').format(
                   DATETIME_OF_RUN,
                   e,
                   messagetype
               )
        return None, None



# -------------------------------------------------------------


def getUserflowsSummary(app_id, app_name, message_type):
    """Calls the transactions summary endpoint for an app

    Args
        app_id: (string) App ID used to request data from the API
        app_name: (string) Human-readable app name
        message_type: (string) Type of message (for sorting in Splunk)

    Returns:
        None
    """
    uri = 'transactions/{}/summary/'.format(app_id)

    response = apicall(uri)

    try:
        userflow_data = response[DATA]
        messages = u','.join(
            [u'("{}",{},{})'.format(
                metric,
                data[VALUE],
                data[CHANGE_PCT]) for metric, data in userflow_data.iteritems()]
        )
        print u'{} MessageType={} appName="{}" appId="{}" DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, e, message_type))
        return None, None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: API returned no {} data'
               u' for {} ({}).'.format(DATETIME_OF_RUN,
                                       message_type,
                                       app_id,
                                       app_name))
        return None, None


def getUserflowsRanked(app_id, app_name, category, message_type):
    """Calls the transactions ranked endpoint to get the top failed transactions

    Args:
        app_id: (string) App ID used to request data from the API
        app_name: (string) Human-readable app name
        category: (string) Kind of transaction to return (e.g. failed, succeeded)
        message_type: (string) Type of message (for sorting in Splunk), equivalent to category

    Return:
        None
    """

    uri = 'transactions/{}/ranked/{}/'.format(app_id, category)

    response = apicall(uri)

    try:
        userflow_data = response[DATA]
        messages = u','.join(
            [u'("{}",{},{})'.format(
                group[NAME],
                group[FAILURE_RATE],
                group[UNIT][TYPE]
            ) for group in userflow_data]
        )
        print u'{} MessageType={} appName="{}" appId="{}"  DATA {}'.format(
            DATETIME_OF_RUN, message_type, app_name, app_id, messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, e, message_type))
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: {} '
               u'no data returned for {}.'.format(DATETIME_OF_RUN,
                                                  e,
                                                  message_type))


def getUserflowsDetails(app_id, app_name):
    """Call the userflows details/change endpoint for an app

    Args:
        app_id: (string) App ID used to request data from the API
        app_name: (string) Human-readable app name

    Return:
        None
    """
    uri = 'transactions/{}/details/change/P1M'.format(app_id)
    params = {'pageNum': 1,
              'pageSize': 10,
              'sortBy': NAME,
              'sortOrder': 'ascending'}

    response = apicall(uri, params)

    try:
        userflow_data = response[DATA]

        getUserflowsChangeDetails(app_id, app_name, userflow_data)

        for group in userflow_data:
            getUserflowsGroups(app_id, app_name, group[NAME])
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN,
                                e,
                                'UserflowsDetails'))
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: {} '
               u'no data returned for {}.'.format(DATETIME_OF_RUN,
                                                  e,
                                                  'UserflowsDetails'))


def getUserflowsChangeDetails(app_id, app_name, userflow_dict):
    """Process the userflows details/change data for Splunk

    Args:
        app_id: (string) App ID used to request data from the API
        app_name: (string) Human-readable app name
    Return:
        None
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
            print (u'{} MessageType={} appName="{}" appId="{}" '
                   u'DATA {}').format(DATETIME_OF_RUN,
                                      'UserflowsChangeDetails',
                                      app_name,
                                      app_id,
                                      messages)
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN,
                                e,
                                'UserflowsChangeDetails'))


def getUserflowsGroups(app_id, app_name, group):
    """Call the transactions group endpoint for a group

    Args:
        app_id: (string) App ID used to request data from the API
        app_name: (string) Human-readable app name
        group: (string) The name of a transactions group (e.g. Login)

    Returns: None
    """

    uri = 'transactions/{}/group/{}'.format(app_id, group)

    response = apicall(uri)
    userflow_data = response[DATA]

    try:
        for transaction in userflow_data[SERIES].keys():
            messages = u''
            messages += (u'(Metric="{}",count={},rate={}%,moneyValue=${},'
                         u'meanDuration={})').format(
                             transaction,
                             userflow_data[SERIES][transaction][COUNT][VALUE],
                             userflow_data[SERIES][transaction][RATE][VALUE],
                             userflow_data[SERIES][transaction][MONEY_VALUE][VALUE],
                             userflow_data[SERIES][transaction][MEAN_DURATION][VALUE]
                         )
            print (u'{} MessageType={} appId="{}" appName="{}" Userflow="{}" '
                   u'DATA {}').format(
                       DATETIME_OF_RUN,
                       'UserflowGroup',
                       app_id,
                       app_name,
                       group,
                       messages
                   )

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access {} '
               u'in {}.'.format(DATETIME_OF_RUN, e, "TransactionsGroup"))


def getDailyAppLoads(app_id, app_name):
    """Get the number of daily app loads for a given app."""

    params = {
        GRAPH: APPLOADS,
        DURATION: 1440,
        APPID: app_id,
    }

    apploadsD = apicall("errorMonitoring/graph", params)

    try:
        print (u'{} MessageType=DailyAppLoads appName="{}" appId="{}" '
               u'dailyAppLoads={}').format(
                   DATETIME_OF_RUN,
                   app_name,
                   app_id,
                   apploadsD[DATA][SERIES][0]['points'][0]
               )
    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: '
               u'Could not access {} in {}.').format(DATETIME_OF_RUN,
                                                     e,
                                                     'get_daily_app_loads')
        return None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: '
               u'{}. No daily app loads for {}').format(DATETIME_OF_RUN,
                                                        e,
                                                        app_id)


def getDailyCrashes(appId, appName):
    """Get the number of daily app crashes for a given app.
    good candidate for 'backfill' data if needed"""

    daily_crashes = apicall("app/%s/crash/counts" % appId)

    if daily_crashes:
        crashdata = daily_crashes.get(DATA)
    else:
        return

    if crashdata:
        try:
            print (u'{} MessageType=DailyCrashes appName="{}" appId="{}" '
                   u'dailyCrashes={}').format(DATETIME_OF_RUN,
                                              appName,
                                              appId,
                                              crashdata[len(crashdata) - 1][VALUE])
        except KeyError as e:
            print (u'{} MessageType="ApteligentError" Error: '
                   u'Could not access {} in {}.').format(DATETIME_OF_RUN,
                                                         e,
                                                         'get_daily_crashes')
            return None

        return


def getTrends(app_id, app_name):
    """Calls the trends endpoint for an app

    Args:
        app_id: (string) App ID used to request data from the API
        app_name: (string) Human-readable app name

    Return:
        None
    """
    print u'{} MessageType="getTrends" for {}'.format(
        DATETIME_OF_RUN,
        app_id
    )

    trends = apicall(u'trends/{}'.format(app_id))

    if trends:
        trends_data = trends[DATA]
    else:
        print (u'{} MessageType=ApteligentError No trends data found for '
               u'app {} ({})').format(DATETIME_OF_RUN,
                                      app_name,
                                      app_id)
        return

    getTopValues(app_id, app_name, trends_data)
    getTimeseriesTrends(app_id, app_name, trends_data)


def getTopValues(appId, appName, trendsData):
    """Pulls todayTopValues data out of the trends dictionary
    for specific trends, and prints to Splunk.

    Args:
        appId: (string) App ID
        appName: (string) Human-readable app name
        trendsData: (dict) A dictionary of trends data
    Returns:
        None
    """

    trend_names = ['appLoadsByVersion',
                   'crashesByVersion',
                   'appLoadsByOs',
                   'crashesByOs']

    for trend in trend_names:
        messages = u''
        for version, value in trendsData[SERIES][
                trend]['todayTopValues'].iteritems():
            messages += u'("{}",{}),'.format(version, value)
        try:
            print (u'{} MessageType={} appName="{}" appId="{}" '
                   u'DATA {}').format(DATETIME_OF_RUN,
                                      trend,
                                      appName,
                                      appId,
                                      messages)
        except KeyError as e:
            print (u'{} MessageType="ApteligentError" Error: '
                   u'Could not access {} in {}.').format(DATETIME_OF_RUN,
                                                         e,
                                                         'TopValues')
            continue

    return


def getTimeseriesTrends(appId, appName, trendsData):
    """Pulls time series data out of the trends dictionary for
    crashes by version, and prints to Splunk.

    Args:
        appId: (string) App ID
        appName: (string) Human-readable app name
        trendsData: (dict) A dictionary of trends data

    Returns:
        None
    """

    for version in trendsData[SERIES][CRASHESBYVERSION][CATEGORIES].keys():
        messages = u''
        for bucket in trendsData[SERIES][CRASHESBYVERSION][
                CATEGORIES][version]['buckets']:
            messages += u'({},{}),'.format(bucket[START][:10], bucket[VALUE])
        try:
            print (u'{} MessageType={} appName="{}" appId="{}" appVersion="{}" '
                   u'DATA {}').format(DATETIME_OF_RUN,
                                      "TimeseriesTrends",
                                      appName,
                                      appId,
                                      version,
                                      messages)
        except KeyError as e:
            print (u'{} MessageType="ApteligentError" Error: '
                   u'Could not access {} in {}.').format(DATETIME_OF_RUN,
                                                         e,
                                                         'TimeseriesTrends')
    return


def get_error_counts(app_id, app_name, error_type):
    """Get the number of daily crashes or handled exceptions for a given app.

    Args:
        app_id: string for API call
        app_name: string for Splunk
        error_type: string, either 'crash' or 'exception'

    Returns:
        None
    """
    if error_type == 'crash':
        error_data = apicall("app/crash/counts/{}".format(app_id))
        error_type_message = 'CrashCounts'
    elif error_type == 'exception':
        error_data = apicall("app/exception/counts/{}".format(app_id))
        error_type_message = 'ExceptionCounts'
    else:
        print (u'{} MessageType="ApteligentError" Cannot get error counts.'
               u'No error type provided.').format(DATETIME_OF_RUN)
        return

    print_string = u''

    try:
        for series in error_data[DATA]:
            print_string += u'({},{}),'.format(series[DATE], series[VALUE])

        print (u'{} MessageType={} appName="{}" appId="{}" DATA {}').format(
            DATETIME_OF_RUN,
            error_type_message,
            app_name,
            app_id,
            print_string
        )

    except KeyError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not access '
               u'{} in {}.').format(DATETIME_OF_RUN,
                                    e,
                                    'get_error_counts')
        return None
    except TypeError as e:
        print (u'{} MessageType="ApteligentError" Error: Could not get '
               u'error counts for {} ({})').format(DATETIME_OF_RUN,
                                                   app_id,
                                                   app_name)
        return None



def get_error_details(app_id, app_name, error_type):
    """Get paginated exception summary data and pass it to Splunk

    Args:
        app_id: string
        app_name: string
        error_type: string, either 'crash' or 'exception'

    Return:
        None
    """

    if error_type == 'crash':
        error_uri = u'crash/paginatedtable/{}'.format(app_id)
        error_type_message = 'CrashDetail'
    elif error_type == 'exception':
        error_uri = u'exception/paginatedtable/{}'.format(app_id)
        error_type_message = 'ExceptionDetail'
    else:
        print (u'{} MessageType="ApteligentError" Cannot get error details.'
               u'No error type provided.').format(DATETIME_OF_RUN)
        return

    pages = get_all_pages(error_uri)

    for page in pages:
        for error in page[DATA][ERRORS]:
            print_string = (u'{} MessageType="{}" appId={} appName="{}" '
                            u'exceptionHash="{}"').format(
                                DATETIME_OF_RUN,
                                error_type_message,
                                app_id,
                                app_name,
                                error[HASH]
                            )
            for key, value in error.iteritems():
                if key == 'class_name':
                    continue
                if key == HASH:
                    continue
                elif value:
                    print_string += u'{}="{}"'.format(key, value)
            print print_string


def get_all_pages(base_url):
    """
    For paginated data, get all pages
    use the pagination data returned by the API to get all pages
    :param base_url: string, basic url of the endpoint
    :param param_to_get: string, a specific parameter inside the 'data'
        object returned by the API, e.g. 'errors'
    :yields: the next page of data
    """
    pagenum = 'pageNum'
    attribs = {pagenum: 1}
    page = apicall(base_url, attribs=attribs)
    pagination = 'pagination'

    total_pages = page[DATA].get(pagination).get('totalPages')

    while attribs[pagenum] <= total_pages:
        yield apicall(base_url, attribs=attribs)
        attribs[pagenum] += 1


def getCredentials(sessionKey):
    """
    access the credentials in /servicesNS/nobody/<MyApp>/admin/passwords

    :param sessionKey: string, unique key from Splunk
    :return:
    """

    if DEBUG:
        print u'{} MessageType="ApteligentDebug"  Into getCredentials'.format(
            DATETIME_OF_RUN
        )

    auth = None
    entities = None
    retry = 1

    while auth is None and retry < MAX_RETRY:
        if DEBUG:
            print u'Attempt to get credentials {}'.format(retry)
        try:
            # list all credentials
            entities = entity.getEntities(
                ['admin', 'passwords'],
                namespace=myapp,
                owner='nobody',
                sessionKey=sessionKey
            )
        except Exception as e:
            print (u'{} MessageType="ApteligentDebug" '
                   u'Could not get {} credentials from splunk. '
                   u'Error: {}'.format(DATETIME_OF_RUN, myapp, e))

        # return first set of credentials
        if DEBUG:
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


###########


def main():
    if DEBUG:
        sessionKey = "bogus_session_key_for_debugging"
    else:
        sessionKey = sys.stdin.readline().strip()

    if DEBUG:
        print u'{} MessageType="ApteligentDebug" sessionKey is {}'.format(
            DATETIME_OF_RUN,
            sessionKey
        )

    if len(sessionKey) == 0:
        print (u'{} MessageType="ApteligentError" '
               u'Did not receive a session key from splunk. ').format(
                   DATETIME_OF_RUN
               )
        exit(2)

    # now get crittercism oauth token
    global ACCESS_TOKEN
    ACCESS_TOKEN = getCredentials(sessionKey)

    if DEBUG:
        print u'{} MessageType="ApteligentDebug" OAuth token is {}'.format(
            DATETIME_OF_RUN,
            ACCESS_TOKEN
        )

    call_manager(sessionKey)

# Get application summary information.
    all_apps = getAppSummary()

    for app in all_apps.keys():
        crashes = get_error_summary(app, all_apps[app][NAME], CRASH)
        if crashes:
            for ckey in crashes.keys():
                getCrashDetail(ckey, app, all_apps[app][NAME])

        getTrends(app, all_apps[app][NAME])

        getDailyAppLoads(app, all_apps[app][NAME])
        getDailyCrashes(app, all_apps[app][NAME])
        get_error_counts(app, all_apps[app][NAME], CRASH)

        get_error_counts(app, all_apps[app][NAME], EXCEPTION)
        get_error_summary(app, all_apps[app][NAME], EXCEPTION)
        get_error_details(app, all_apps[app][NAME], EXCEPTION)

        getGenericPerfMgmt(
            app,
            all_apps[app][NAME],
            VOLUME,
            DEVICE,
            'DailyVolumeByDevice')
        getGenericPerfMgmt(
            app,
            all_apps[app][NAME],
            ERRORS,
            SERVICE,
            'DailyServiceErrorRates')
        getGenericPerfMgmt(app, all_apps[app][NAME], VOLUME, OS, 'DailyVolumeByOS')
        getGenericPerfMgmt(
            app,
            all_apps[app][NAME],
            VOLUME,
            APPVERSION,
            'VolumeByAppVersion')

        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            CRASHES,
            DEVICE,
            'CrashesByDevice')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            CRASHPERCENT,
            DEVICE,
            'CrashPerByDevice')
        getGenericErrorMon(app, all_apps[app][NAME], APPLOADS, OS, 'ApploadsByOs')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            CRASHES,
            OS,
            'DailyCrashesByOs')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            CRASHPERCENT,
            OS,
            'CrashPerByOs')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            CRASHPERCENT,
            APPVERSION,
            'CrashPerByAppVersion')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            CRASHES,
            APPVERSION,
            'CrashByAppVersion')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            APPLOADS,
            APPVERSION,
            'LoadsByAppVersion')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            DAU,
            APPVERSION,
            'DauByAppVersion')
        getGenericErrorMon(
            app,
            all_apps[app][NAME],
            APPLOADS,
            DEVICE,
            'ApploadsByDevice')

        getAPMEndpoints(app, all_apps[app][NAME], LATENCY, 'ApmEndpointsLatency')
        getAPMEndpoints(app, all_apps[app][NAME], VOLUME, 'ApmEndpointsVolume')
        getAPMEndpoints(app, all_apps[app][NAME], ERRORS, 'ApmEndpointsErrors')
        getAPMEndpoints(app, all_apps[app][NAME], DATA, 'ApmEndpointsData')

        getAPMServices(app, all_apps[app][NAME], LATENCY, 'ApmServicesLatency')
        getAPMServices(app, all_apps[app][NAME], VOLUME, 'ApmServicesVolume')
        getAPMServices(app, all_apps[app][NAME], ERRORS, 'ApmServicesErrors')
        getAPMServices(app, all_apps[app][NAME], DATA, 'ApmServicesData')

        getAPMGeo(app, all_apps[app][NAME], LATENCY, 'ApmGeoLatency')
        getAPMGeo(app, all_apps[app][NAME], VOLUME, 'ApmGeoVolume')
        getAPMGeo(app, all_apps[app][NAME], ERRORS, 'ApmGeoErrors')
        getAPMGeo(app, all_apps[app][NAME], DATA, 'ApmGeoData')

        getUserflowsSummary(app, all_apps[app][NAME], 'UserflowsSummary')
        getUserflowsRanked(
            app,
            all_apps[app][NAME],
            FAILED,
            'UserflowsRankedFailed')
        getUserflowsDetails(app, all_apps[app][NAME])

if __name__ == '__main__':
    main()
    print "I made {} calls".format(len(ALL_CALLS))
