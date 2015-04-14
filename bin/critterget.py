#!/usr/bin/python
import urllib2
import urllib
import json
import sys
import datetime, base64
import splunk.entity as entity

#The splunk name for the app.  Needed for the autho storage
myapp = 'crittercism'
access_token = ''
baseurl = "https://developers.crittercism.com:443/v1.0/"
authbaseurl = "https://developers.crittercism.com/v1.0/"

debug = 0
DUMP_DIAGS = 1
interval = 10 #minutes between runs of theis script as performed by Splunk

today = datetime.datetime.now() # calculate this for a common time for all summary data
myruntime = today.strftime('%Y-%m-%d %H:%M:%S %Z')

# a quick command to forman quasi json output nicely
pretty=(lambda a:lambda v,t="\t",n="\n",i=0:a(a,v,t,n,i))(lambda f,v,t,n,i:"{%s%s%s}"%(",".join(["%s%s%s: %s"%(n,t*(i+1),repr(k),f(f,v[k],t,n,i+1))for k in v]),n,(t*i)) if type(v)in[dict] else (type(v)in[list]and"[%s%s%s]"or"(%s%s%s)")%(",".join(["%s%s%s"%(n,t*(i+1),f(f,k,t,n,i+1))for k in v]),n,(t*i)) if type(v)in[list,tuple] else repr(v))



def apicall (uri, attribs=''):
    # perform an API call 
    if (debug) : print "access token is %s" % access_token
    reqstring = baseurl + uri
    
    if ( attribs ) : reqstring += "?"+attribs

    if (debug) : print "reqstring is %s" % reqstring
    
    request = urllib2.Request(reqstring)
    request.add_header('Content-Type','application/json')
    request.add_header('Authorization', "Bearer %s" % access_token)

    try:
        response = urllib2.urlopen(request)
        resptext = response.read()
        data = json.loads(resptext)
    
    except urllib2.URLError, e:
        print 'Crittercism API retuned an error code:', e
        sys.exit(0)
  
    return data
 
def apipost (uri, postdata='',keyget=''):
    # perform an API POST 
    if (debug) : print "access token is %s" % access_token
    reqstring = baseurl + uri
    data = ""
    
    if (debug) : print "reqstring is %s" % reqstring

    pdata = json.dumps(postdata)

    request = urllib2.Request(reqstring,pdata)
    if (keyget==''):
        request.add_header('Content-Type','application/json')
        request.add_header('Authorization', "Bearer %s" % access_token)

    try:
        response = urllib2.urlopen(request)
        resptext = response.read()
        data = json.loads(resptext)
    
    except urllib2.URLError, e:
        print '%s MessageType=\"CrittercismError\" Crittercism API retuned an error code: %s for the call to %s.  Maybe an ENTERPRISE feature?' %( myruntime, e, reqstring)
        data = "ERROR"
#        sys.exit(0)
  
    return data

def authpost (postdata='',keyget=''):
    # perform an API POST to get the auth_token

    reqstring = authbaseurl + "token"

    data = ""

    if (debug) : print "reqstring is %s" % reqstring

    params = urllib.urlencode(postdata)
    request = urllib2.Request(reqstring,params)
    authstr = base64.encodestring('%s' % (keyget)).replace('\n', '')
    request.add_header('Authorization', "Basic %s" % authstr)

    try:

        if (debug) :
            handler=urllib2.HTTPSHandler(debuglevel=1)
        else :
            handler=urllib2.HTTPSHandler(debuglevel=0)
            
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

        resptext=urllib2.urlopen(request).read()
        data = json.loads(resptext)
    
    except urllib2.URLError, e:
        print '%s MessageType=\"CrittercismError\" Crittercism Auth API retuned an error code: %s for the call to %s.  Maybe an ENTERPRISE feature?' %( myruntime, e, reqstring)
        data = "ERROR"
        sys.exit(0)
  
    return data['access_token']
    
def getAccessToken(username,password,myApiKey):
# auth a session key from crittercism
    if (debug) : print "%s MessageType=\"CritterDebug\" Into getAccessTokenuser = %s pass = %s apikey = %s" % (myruntime,username,password,myApiKey)
        
    params = dict([('grant_type', "password"), ('username', username), ('password', password)])        
        	
    accessToken = authpost(params,myApiKey)
    if (debug) : print "apipost returns ",accessToken
    return accessToken




    
def scopetime():
    # return an ISO8601 timestring based on NOW - Interval
    newtime=(datetime.datetime.utcnow() - datetime.timedelta(minutes=interval))
    
    return (newtime.isoformat())
       
def getAppSummary():
# read app summary information.  Print out in Splunk KV format.  Return a dict with appId and appName.

    # list of the attributes we'll hand to Crittercism, also the list we will create as Splunk Keys
    summattrs = "appName,appType,crashPercent,dau,latency,latestAppStoreReleaseDate,latestVersionString,linkToAppStore,iconURL,mau,rating,role"
    atstring = "attributes=%s"%summattrs
    gdata = apicall("apps",atstring)

    AppDict = {}
    for appId in gdata.keys():
        printstring = "%s MessageType=\"AppSummary\" appId=%s " % (myruntime, appId)
        slist = summattrs.split(",")
        for atname in slist:
            printstring += "%s=\"%s\" " %(atname,gdata[appId][atname])
            if atname == "appName" : AppDict[appId]= gdata[appId][atname]
        print printstring

    return AppDict


def getCrashSummary(appId, appName):
# given an appID and an appName, produce a Splunk KV summary of the crashes for a given timeframe
    mystime = scopetime()
    
    crashattrs = "hash,lastOccurred,sessionCount,uniqueSessionCount,reason,status,displayReason,name"
    crashdata = apicall("app/%s/crash/summaries" % appId, "lastOccurredStart=%s" % mystime)
    CrashDict = {}
    for x,y in enumerate(crashdata):
        printstring = "%s MessageType=\"CrashSummary\" appId=%s appName=\"%s\" " % (myruntime, appId, appName)
        slist = crashattrs.split(",")
        for atname in slist:
            printstring += "%s=\"%s\" " %(atname,crashdata[x][atname])
            if atname == "hash" : CrashDict[crashdata[x][atname]]= appName
        print printstring
        
    return CrashDict
    
def getBreadcrumbs(crumbs, hash, appName) :
#breadcrumbs come in as a list.  need to ennumerate
    for i,key in enumerate(crumbs):
        #print "BREADCRUMB i %s key %s" % (i, key)
        printstring = "%s MessageType=\"CrashDetailBreadcrumbs\" hash=%s " % (myruntime, hash)
        for bkey in key.keys():
                        
            if bkey in ("current_session", "previous_session", "crashed_session") :
               printstring += " \nsession=%s " % (bkey ) + pretty(key[bkey]) + "\n"
            else:
                printstring += " %s=\"%s\" " % (bkey, key[bkey])
        print printstring        
            
def getStacktrace(stacktrace,hash) :
    print "%s MessageType=\"CrashDetailStacktrace\"  hash=%s " % (myruntime, hash),pretty(stacktrace)

    

def diag_geo(data,hash):
    if (debug) : print "into diag_geo"
    for country in data.keys():
        for city in data[country].keys():
            if city == '--NAME--': 
                continue
            (lat,lon,crashes) = (str(data[country][city][0]),
                                str(data[country][city][1]),
                                str(data[country][city][2])  )
            print "%s MessageType=\"CrashDiagsGeo\"  hash=%s country=\"%s\" city=\"%s\" lat=%s lon=%s crashes=\"%s\" " % (myruntime, hash,country,city,lat,lon,crashes) 

def diag_discrete(data, hash):
    datastring= ""
    for dstat in data.keys():        
        for (var,val) in data[dstat]:
            datastring += " \"%s:%s\"=\"%s\"" % (dstat,str(var).replace(" ","_"),str(val))
        
    print "%s MessageType=\"CrashDiagsDiscrete\"  hash=%s %s " % (myruntime, hash,datastring) 
        

def diag_affected_users(data,hash) :
    for uhash in data.keys():
        datastring= ""
        for vhash in data[uhash]:
            datastring += " %s=\"%s\"" % (str(vhash).replace(" ","_"),str(data[uhash][vhash]))
        
        print "%s MessageType=\"CrashDiagsAffectedUser\"  hash=%s  userhash=%s %s " % (myruntime, hash, uhash, datastring) 
        
def diag_affected_versions(data,hash):
    datastring = ""
    for x,vpair in data:
        datastring += " \"%s\"=%s" % (str(x).replace(" ","_"),str(vpair))
      
    print "%s MessageType=\"CrashDiagsAffectedVersions\"  hash=%s %s " % (myruntime, hash,datastring) 
   
   
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
         
        print "%s MessageType=\"CrashDiagsContBar\"  hash=%s datatype=%s %s " % (myruntime, hash, dstat, valstr) 


def diag_cont(data, hash):
# Grab all of the continuous data from Crittercism and format into a splunk event
    datastring= ""
    for uhash in data.keys():
        
        for vhash in data[uhash]:
            datastring += " %s_%s=\"%s\"" % (uhash,str(vhash).replace(" ","_"),str(data[uhash][vhash]))
        
    print "%s MessageType=\"CrashDiagsContinuous\"  hash=%s %s " % (myruntime, hash, datastring) 
    
     
#############   
def getDiagnostics(diags,hash) :
# Dump and prettyprint the diags -- might want to expand on this...
    if (DUMP_DIAGS ==0) : 
        print "%s MessageType=\"CrashDetailDiagnostics\" DISABLED PER CONFIG FILE " % (myruntime, hash)
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

        elif (key=="continuous_bar_diagnostic_data"):
            diag_cont_bar(diags[key], hash)
        
        elif (key=='continuous_diagnostic_data'):
            diag_cont(diags[key], hash)
        elif (key=='num_geo_points'):
            continue
        elif (key=='discrete_bar_diagnostic_data'):
            continue    
        else:
            print "--UNPROCESSED----%s - %s" % (key,diags[key])
            
def getDOBV(stacktrace, hash) :
# handle the DailyOccurrencesByVersion coming back from a crashdetail
    print "%s MessageType=\"CrashDetailDailyOccurrencesByVersion\"  hash=%s " % (myruntime, hash),pretty(stacktrace)
    
def getUSCBV(stacktrace,hash) :
# handle the UniqueSessionCountsByVersion coming back from a crashdetail
    print "%s MessageType=\"CrashDetailUniqueSessionCountsByVersion\"  hash=%s " % (myruntime, hash),pretty(stacktrace)


def getSCBV(stacktrace, hash) :
# handle the SessionCountsByVersion coming back from a crashdetail
    print "%s MessageType=\"CrashDetailSessionCountsByVersion\"  hash=%s " % (myruntime, hash),pretty(stacktrace)


def getSymStacktrace(stacktrace,hash) :
# handle the lSymbolizedStacktrace coming back from a crashdetail
    print "%s MessageType=\"CrashDetailSymbolizedStacktrace\"  hash=%s " % (myruntime, hash),pretty(stacktrace)
       
def getCrashDetail(hash, appName):
# given a crashhash, get all of the detail about that crash 

    crashdetail = apicall("crash/%s" % hash, "diagnostics=True")
    printstring = "%s MessageType=\"CrashDetail\"  appName=\"%s\" " % (myruntime, appName)
    for dkey in crashdetail.keys():
        if dkey == "breadcrumbs" :
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
            printstring += "%s=\"%s\" " % (dkey, crashdetail[dkey])
            
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
    print "%s MessageType=HourlyAppLoads AppLoads=%s appId=\"%s\" appName=\"%s\"" % (myruntime, dlist[len(dlist)-1],appId,appName)
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
 
    mystring = ""
    try:
        for series in crashesos['data']['slices']:	
            mystring += "(\"%s\",%s)," % (series['label'], series['value'])

        print "%s MessageType=DailyCrashesByOS appName=\"%s\" appId=\"%s\" DATA %s" %(myruntime, appName,appId,mystring)
        return	
		
    except KeyError as e:
        print '%s MessageType=\"CrittercismError\" Error: Could not access %s in %s.' % (myruntime, str(e), 'get_crashes_by_os')
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

    serverrors = apipost("performanceManagement/pie",params)
    
#    print "%s DEBUG Into getGenericPerfMgmt appId = %s  appName = %s graph= %s groupby = %s messagetype = %s" %(myruntime, appId, appName,graph,groupby,messagetype)
			
    mystring = ""
    try:
        for series in serverrors['data']['slices']:
		    mystring += "(\"%s\",%s)," % (series['label'], series['value'])

        print "%s MessageType=%s appName=\"%s\" appId=\"%s\"  DATA %s" %(myruntime, messagetype, appName,appId,mystring)
        
    except KeyError as e:
        print '%s MessageType=\"CrittercismError\" Error: Could not access %s in %s.' % (myruntime, str(e), messagetype)
        return (None, None)

"""--------------------------------------------------------------"""
def getGenericErrorMon(appId, appName,graph,groupby,messagetype):
    """Generic data return for errorMonitoring/pie end point."""
    
    params={"params":{
        "groupBy": groupby,
        "graph": graph,
        "duration": 1440,
        "appId": appId
        }}

    serverrors = apipost("errorMonitoring/pie",params)
    
#    print "%s DEBUG Into getGenericErrorMon appId = %s  appName = %s graph= %s groupby = %s messagetype = %s" %(myruntime, appId, appName,graph,groupby,messagetype)
		
    mystring = ""
    try:
        for series in serverrors['data']['slices']:
		    mystring += "(\"%s\",%s)," % (series['label'], series['value'])

        print "%s MessageType=%s appName=\"%s\" appId=\"%s\"  DATA %s" %(myruntime, messagetype, appName,appId,mystring)
        
    except KeyError as e:
        print '%s MessageType=\"CrittercismError\" Error: Could not access %s in %s.' % (myruntime, str(e), messagetype)
        return (None, None)

"""--------------------------------------------------------------"""



def getDailyAppLoads(appId,appName):
    """Get the number of daily app loads for a given app."""

    params={"params":{
        "graph": "appLoads",
        "duration": 1440,
        "appId": appId,
        }}
        
    apploadsD = apipost("errorMonitoring/graph",params)
    
    try:
        print "%s MessageType=DailyAppLoads appName=\"%s\" appId=\"%s\" dailyAppLoads=%s" % (myruntime,appName, appId, apploadsD['data']['series'][0]['points'][0])
    except KeyError as e:
        print '%s MessageType=\"CrittercismError\" Error: Could not access %s in %s.' % (myruntime, str(e), 'get_daily_app_loads')
        return None

def getDailyCrashes(appId,appName):
    """Get the number of daily app crashes for a given app."""
    """good candidate for 'backfill' data if needed"""

    crashdata = apicall("app/%s/crash/counts" % appId)
    
    try:
        print "%s MessageType=DailyCrashes appName=\"%s\" appId=\"%s\" dailyCrashes=%s" % (myruntime,appName, appId, crashdata[len(crashdata)-1]['value'])
    except KeyError as e:
        print '%s MessageType=\"CrittercismError\" Error: Could not access %s in %s.' % (myruntime, str(e), 'get_daily_crashes')
        return None
        
    return      
    
def getCrashCounts(appId,appName):
    """Get the number of daily app crashes for a given app."""
    """good candidate for 'backfill' data if needed"""

    crashdata = apicall("app/%s/crash/counts" % appId)
    
    mystring = ""
   
    try:
        for series in crashdata:
		    mystring += "(%s,%s)," % (series['date'], series['value'])

        print "%s MessageType=CrashCounts appName=\"%s\" appId=\"%s\" DATA %s" %(myruntime, appName,appId,mystring)

    except KeyError as e:
        print '%s MessageType=\"CrittercismError\" Error: Could not access %s in %s.' % (myruntime, str(e), 'get_crash_counts')
        return None
        
    return             

def getCredentials(sessionKey):
# access the credentials in /servicesNS/nobody/<MyApp>/admin/passwords

    if (debug) : print '%s MessageType=\"CritterDebug\"  Into getCredentials' % (myruntime)
    
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=sessionKey)
    except Exception, e:
        print '%s MessageType=\"CritterDebug\" Could not get %s credentials from splunk. Error: %s' % (myruntime, myapp, str(e))

    # return first set of credentials
    if (debug) : print "Entities is ", entities
    for i, c in entities.items():
        return c['username'], c['clear_password']

    print "%s MessageType=\"CritterDebug\" No credentials have been found for app %s . Maybe a setup issue?" % (myruntime, myapp)  

def getClientID(sessionKey):
# access the clientID entered in setup.  It should be 
# in $SPLUNK_HOME/etc/apps/crittercism/local/crittercism.conf 

    if (debug) : print '%s MessageType=\"CritterDebug\"  Into getAPI' % (myruntime)

    try:
        # list all credentials
        entities = entity.getEntities(['properties', 'crittercism','api'], namespace=myapp,
                                    owner='nobody', sessionKey=sessionKey)
    except Exception, e:
        print '%s MessageType=\"CritterDebug\" Could not get %s api information from splunk. Error: %s' % (myruntime, myapp, str(e))

    # return first set of credentials
    if (debug) : print "Entities is ", entities
 # for i, c in entities.items():
    try:
        return entities['clientID']

    except Exception, e:
            print "%s MessageType=\"CritterDebug\" %s No credentials have been found for app %s . Maybe a setup issue?" % (myruntime, e, myapp)  



###########
# 

def main():
#NEED test auth and fix keys if needed
    #read session key sent from splunkd
    sessionKey = sys.stdin.readline().strip()
    if (debug) : print '%s MessageType=\"CritterDebug\" sessionKey is %s' % (myruntime, sessionKey)
    
    if len(sessionKey) == 0:
        print "%s MessageType=\"CrittercismError\" Did not receive a session key from splunkd. " % myruntime
        exit(2)
        
    (Cusername, Cpassword) = getCredentials(sessionKey)
    if (debug) : print '%s MessageType=\"CritterDebug\" username is %s password is %s' % (myruntime, Cusername, Cpassword)

    myClientID = getClientID(sessionKey)
    if (debug) : print '%s MessageType=\"CritterDebug\" ClientID is %s' % (myruntime, myClientID)

    # now get crittercism credentials - might exit if no creds are available
    global access_token
    access_token = getAccessToken(Cusername,Cpassword,myClientID)

# Get application summary information.   
    apps = getAppSummary()
    for key in apps.keys():
        crashes = getCrashSummary(key, apps[key]) 
        for ckey in crashes.keys():
            getCrashDetail(ckey, apps[key])
#        errors = getErrorSummary(key,apps[key])
#        cbos = getCrashesByOS(key,apps[key])


        apploadsD = getDailyAppLoads(key,apps[key])
        appCrashD = getDailyCrashes(key,apps[key])
        crashCounts = getCrashCounts(key,apps[key])
        reqByDevice = getGenericPerfMgmt(key,apps[key],"volume","device","DailyVolumeByDevice")
        errByService = getGenericPerfMgmt(key,apps[key],"errors","service","DailyServiceErrorRates")            
        reqByOs = getGenericPerfMgmt(key,apps[key],"volume","os","DailyVolumeByOS")            
 
        crashbydev = getGenericErrorMon(key,apps[key],"crashes","device","CrashesByDevice")
        crashPerbydev = getGenericErrorMon(key,apps[key],"crashPercent","device","CrashPerByDevice")
        apploadsos = getGenericErrorMon(key,apps[key],"appLoads","os","ApploadsByOs")
        crashbyos = getGenericErrorMon(key,apps[key],"crashes","os","DailyCrashesByOs")
        crashPerbyos = getGenericErrorMon(key,apps[key],"crashPercent","os","CrashPerByOs")

        reqbyver = getGenericPerfMgmt(key,apps[key],"volume","appVersion","VolumeByAppVersion")
        crashPbyver = getGenericErrorMon(key,apps[key],"crashPercent","appVersion","CrashPerByAppVersion")
        crashbyver = getGenericErrorMon(key,apps[key],"crashes","appVersion","CrashByAppVersion")
        loadsbyver = getGenericErrorMon(key,apps[key],"appLoads","appVersion","LoadsByAppVersion")
        daubyver = getGenericErrorMon(key,apps[key],"dau","appVersion","DauByAppVersion")
#        userbydev = getGenericErrorMon(key,apps[key],"affectedUsers","device","UserbaseByDevice")
#        userbyos = getGenericErrorMon(key,apps[key],"affectedUsers","os","UserbaseByOs")
        apploadsbydev = getGenericErrorMon(key,apps[key],"appLoads","device","ApploadsByDevice")
        
if __name__=='__main__':
	main()