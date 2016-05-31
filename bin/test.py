import unittest
import sys
from StringIO import StringIO
import mock
import datetime

import critterget

class TestSplunk(unittest.TestCase):
    def setUp(self):
        # Turn on critterget's debug messages
        critterget.debug = 1

        # By default, critterget's access_token variable is an empty string
        # The access_token must be NOT an empty string for critterget to run properly
        critterget.access_token = "bogustoken"

        # patch out requests
        get_patcher = mock.patch.object(critterget.requests, 'get')
        post_patcher = mock.patch.object(critterget.requests, 'post')

        # patcher will start and stop automatically when these tests are run
        self.mock_get = get_patcher.start()
        self.mock_post = post_patcher.start()
        self.addCleanup(get_patcher.stop)
        self.addCleanup(post_patcher.stop)

    def tearDown(self):
        pass

    # This method was lifted from cypythonlib/soaclients/tests/unit/test_ams_wrapper.py
    @staticmethod
    def _response_with_json_data(status_code, json_data):
        response = mock.Mock()
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    @staticmethod
    def _catch_stdout(func, *args, **kwargs):
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        func(*args, **kwargs)
        output = out.getvalue()
        # Return stdout to its initial state
        sys.stdout = saved_stdout
        return output

    def test_get_credentials(self):
        credentials = critterget.getCredentials('session_key')
        self.assertEqual(credentials, 'boguspassword')

    def test_apicall(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, {'bogusappID': {'bogusresponse': 'bogusdata'}})]
        test_response = critterget.apicall('endpoint', 'attribute string')
        self.assertEqual(test_response, {'bogusappID': {'bogusresponse': 'bogusdata'}})

    def test_apipost(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'bogusappID': {'bogusresponse': 'bogusdata'}})]
        test_response = critterget.apipost('endpoint', 'attribute string')
        self.assertEqual(test_response, {'bogusappID': {'bogusresponse': 'bogusdata'}})

    def test_getAppSummary(self):
        self.mock_get.side_effect = [self._response_with_json_data(200,
                                                                   {'bogusappID':
                                                                        {'appName': 'bogusApp',
                                                                         'appType': 'bogusType',
                                                                         'crashPercent': 'bogusCrash',
                                                                         'dau': 'bogusDAU',
                                                                         'latency': 'bogusLatency',
                                                                         'latestAppStoreReleaseDate': 'bogusDate',
                                                                         'latestVersionString': 'bogusVersion',
                                                                         'linkToAppStore': 'bogusLink',
                                                                         'iconURL': 'bogusURL',
                                                                         'mau': 'bogusMAU',
                                                                         'rating': 'bogusRating',
                                                                         'role': 'bogusRole',
                                                                         'appVersions': ['bogus.version']}
                                                                    }
                                                                   )
                                     ]
        apps = critterget.getAppSummary()
        self.assertEqual(apps.keys()[0], 'bogusappID')
        self.assertEqual(apps[apps.keys()[0]]['name'], 'bogusApp')
        self.assertEqual(apps[apps.keys()[0]]['versions'], ['bogus.version'])

    def test_scopetime(self):
        test_time = critterget.scopetime()
        interval_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        self.assertLessEqual(test_time, interval_time.isoformat())

    def test_getCrashSummary(self):
        self.mock_get.side_effect = [self._response_with_json_data(200,[
                                                                         {'hash': 'bogusHash',
                                                                          'lastOccurred': 'bogusLast',
                                                                          'sessionCount': 'bogusCount',
                                                                          'uniqueSessionCount': 'bogusUniqueCount',
                                                                          'reason': 'bogusReason',
                                                                          'status': 'bogusStatus',
                                                                          'displayReason': 'bogusDisplayReason',
                                                                          'name': 'bogusName'}
                                                                        ]
                                                                   )
                                     ]
        crashes = critterget.getCrashSummary('bogusappID', 'bogusName')
        self.assertEqual(crashes, {'bogusHash': 'bogusName'})

    def test_getBreadcrumbs(self):
        crumbs = [{'aCrumb': 'bogusCrumb'}]

        output = self._catch_stdout(critterget.getBreadcrumbs, crumbs, 'fakeHash', 'appName')

        self.assertIn('MessageType="CrashDetailBreadcrumbs" hash=fakeHash  aCrumb="bogusCrumb"', output)

    def test_getStacktrace(self):
        trace = [{"bogusLine": 0, "bogusTrace": "fakelib"}]

        output = self._catch_stdout(critterget.getStacktrace, trace, 'fakeHash')

        self.assertIn('MessageType="CrashDetailStacktrace"  hash=fakeHash  [\n\t{\n\t\t\'bogusTrace\': \'fakelib\',\n\t\t\'bogusLine\': 0\n\t}\n]\n', output)
        pass

    def test_diag_geo(self):
        geo_data = {'fakeCountry': {'fakeCity': ['fakeLat', 'fakeLon', 'fakeCrashes']}}

        output = self._catch_stdout(critterget.diag_geo, geo_data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsGeo" hash=fakeHash country="fakeCountry" city="fakeCity" lat=fakeLat lon=fakeLon crashes="fakeCrashes"', output)

    def test_diag_discrete(self):
        data = {'fakeStat': [['fakeVar', 'fakeVal']]}

        output = self._catch_stdout(critterget.diag_discrete, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsDiscrete"  hash=fakeHash  "fakeStat:fakeVar"="fakeVal"', output)

    def test_diag_affected_users(self):
        data = {'fakeUser': {'fakeStat': 'fakeData'}}

        output = self._catch_stdout(critterget.diag_affected_users, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsAffectedUser"  hash=fakeHash  userhash=fakeUser  fakeStat="fakeData"', output)

    def test_diag_affected_versions(self):
        data = [['fakeVersion', 'fakeData']]

        output = self._catch_stdout(critterget.diag_affected_versions, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsAffectedVersions"  hash=fakeHash  "fakeVersion"=fakeData', output)

    def test_diag_cont_bar(self):
        data = {'bogusStat': {'bogusCategories': ['bogusCategory'], 'bogusData': ['bogusPoint']}}

        output = self._catch_stdout(critterget.diag_cont_bar, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsContBar"  hash=fakeHash datatype=bogusStat  "bogusPoint"=bogusCategory', output)

    def test_diag_cont(self):
        data = {'bogusStat': {'bogusAve': 'X.X',
                'bogusMax': 'Y.Y',
                'bogusMin': 'Z.Z'}}

        output = self._catch_stdout(critterget.diag_cont, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsContinuous"  hash=fakeHash  bogusStat_bogusAve="X.X" bogusStat_bogusMin="Z.Z" bogusStat_bogusMax="Y.Y"', output)

    def test_getDiagnostics(self):
        diags = {'bogusKey': 'bogusData'}

        output = self._catch_stdout(critterget.getDiagnostics, diags, 'fakeHash')

        self.assertIn('--UNPROCESSED----bogusKey - bogusData', output)

    def test_getDOBV(self):
        data = {'bogusVersion': ['bogusDate',['bogusData']]}

        output = self._catch_stdout(critterget.getDOBV, data, 'fakeHash')

        self.assertIn('MessageType="CrashDetailDailyOccurrencesByVersion"  hash=fakeHash  {\n\t\'bogusVersion\': [\n\t\t\'bogusDate\',\n\t\t[\n\t\t\t\'bogusData\'\n\t\t]\n\t]\n}', output)

    def test_getUSCBV(self):
        data = {'fakeVersion': 'fakeCrashes', 'bogusTotal': 'fakeTotalCrashes'}

        output = self._catch_stdout(critterget.getUSCBV, data, 'fakeHash')

        self.assertIn('MessageType="CrashDetailUniqueSessionCountsByVersion"  hash=fakeHash  {\n\t\'fakeVersion\': \'fakeCrashes\',\n\t\'bogusTotal\': \'fakeTotalCrashes\'\n}', output)

    def test_getSCBV(self):
        data = {'bogusVersion': 'bogusSessions'}

        output = self._catch_stdout(critterget.getSCBV, data, 'fakeHash')

        self.assertIn('MessageType="CrashDetailSessionCountsByVersion"  hash=fakeHash  {\n\t\'bogusVersion\': \'bogusSessions\'\n}', output)

    def test_getSymStacktrace(self):
        data = ['fakeTraceOne', 'fakeTraceTwo']

        output = self._catch_stdout(critterget.getSymStacktrace, data,'fakeHash')

        self.assertIn('MessageType="CrashDetailSymbolizedStacktrace"  hash=fakeHash  [\n\t\'fakeTraceOne\',\n\t\'fakeTraceTwo\'\n]', output)

    def test_getCrashDetail(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, {'bogusStat':'bogusValue'})]

        output = self._catch_stdout(critterget.getCrashDetail, 'fakeHash', 'fakeApp')

        self.assertIn('reqstring is https://developers.crittercism.com/v1.0/crash/fakeHash?diagnostics=True', output)
        self.assertIn('MessageType="CrashDetail"  appName="fakeApp" bogusStat="bogusValue"', output)

    def test_getDailyAppLoads(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data':{'series':[{'points': ['bogusPoint']}]}})]

        output = self._catch_stdout(critterget.getDailyAppLoads, 'appId', 'appName')

        self.assertIn('MessageType=DailyAppLoads appName="appName" appId="appId" dailyAppLoads=bogusPoint', output)

    def test_getDailyCrashes(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, ['bogusData', {'value': 'bogusValue'}])]

        output = self._catch_stdout(critterget.getDailyCrashes, 'appId', 'appName')

        self.assertIn('MessageType=DailyCrashes appName="appName" appId="appId" dailyCrashes=bogusValue', output)

    def test_getCrashCounts(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, [{'date': 'bogusDateOne', 'value': 'bogusValueOne'},
                                                                         {'date': 'bogusDateTwo', 'value': 'bogusValueTwo'}])]

        output = self._catch_stdout(critterget.getCrashCounts, 'appId', 'appName')

        self.assertIn('MessageType=CrashCounts appName="appName" appId="appId" DATA (bogusDateOne,bogusValueOne),(bogusDateTwo,bogusValueTwo)', output)

    def test_getGenericPerfMgmt(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data': {'slices': [{'label': 'bogusLabel', 'value': 'bogusValue'}]}})]

        output = self._catch_stdout(critterget.getGenericPerfMgmt, 'appId', 'appName', 'bogusGraph', 'bogusGroup', 'bogusMessageType')

        self.assertIn('MessageType=bogusMessageType appName="appName" appId="appId"  DATA ("bogusLabel",bogusValue)', output)

    def test_getGenericErrorMon(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data': {'slices': [{'label': 'bogusLabel', 'value': 'bogusValue'}]}})]

        output = self._catch_stdout(critterget.getGenericPerfMgmt, 'appId', 'appName', 'bogusGraph', 'bogusGroup', 'bogusMessageType')

        self.assertIn('MessageType=bogusMessageType appName="appName" appId="appId"  DATA ("bogusLabel",bogusValue)', output)

    def test_getAPMEndpoints(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data': {'endpoints': [{'d': 'bogusD', 'u': 'bogusU', 's': 'bogusS'}]}})]

        output = self._catch_stdout(critterget.getAPMEndpoints, 'appId', 'appName', 'bogusMetric', 'bogusMessageType')

        self.assertIn('MessageType=bogusMessageType appName="appName" appId="appId"  DATA ("bogusDbogusU",bogusS)', output)

    def test_getAPMServices(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data': {'services': [{'name': 'bogusName', 'sort': 'bogusSort'}]}})]

        output = self._catch_stdout(critterget.getAPMServices, 'appId', 'appName', 'bogusMetric', 'bogusMessageType')

        self.assertIn('MessageType=bogusMessageType appName="appName" appId="appId"  DATA ("bogusName",bogusSort)', output)

    def test_getAPMGeo(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data': {'series': [{'geo': {'BogusCountry': 'bogusStat'}}]}})]

        output = self._catch_stdout(critterget.getAPMGeo, 'appId', 'appName', 'bogusMetric', 'bogusMessageType')

        self.assertIn('MessageType=bogusMessageType appName="appName" appId="appId"  DATA ("BogusCountry",bogusStat)', output)

    def test_getTopValues(self):
        trendsData = {u'series':{u'crashesByVersion':{u'todayTopValues': {'bogusVersion': 'bogusCrashes'}},
                        u'appLoadsByVersion':{u'todayTopValues': {'bogusVersion': 'bogusAppLoads'}},
                        u'appLoadsByOs':{u'todayTopValues': {'bogusOS': 'bogusAppLoads'}},
                        u'crashesByOs':{u'todayTopValues': {'bogusOS': 'bogusCrashes'}}
                        }
                    }

        output = self._catch_stdout(critterget.getTopValues, 'appId', 'appName', trendsData)

        self.assertIn('MessageType=crashesByVersion appName="appName" appId="appId" DATA ("bogusVersion",bogusCrashes),', output)
        self.assertIn('MessageType=appLoadsByVersion appName="appName" appId="appId" DATA ("bogusVersion",bogusAppLoads),', output)
        self.assertIn('MessageType=appLoadsByOs appName="appName" appId="appId" DATA ("bogusOS",bogusAppLoads),', output)
        self.assertIn('MessageType=crashesByOs appName="appName" appId="appId" DATA ("bogusOS",bogusCrashes),', output)

    def test_getTimeseriesTrends(self):
        trendsData = {u'series':
                          {u'crashesByVersion':
                               {u'categories':
                                    {'bogusVersion':
                                         {'buckets': [{u'start': 'YYYY-MM-DDTHH:MM:SS+TZ:TZ', u'value': 'bogusVal'}]
                                          }
                                     }
                                }
                          }
                     }

        output = self._catch_stdout(critterget.getTimeseriesTrends, 'appId', 'appName', trendsData)

        self.assertIn('MessageType=TimeseriesTrends appName="appName" appId="appId" appVersion="bogusVersion" DATA (YYYY-MM-DD,bogusVal)', output)

    def test_getUserflowsSummary(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, {'series': {'bogusMetric': {'value': 'bogusValue', 'changePct': 'bogusPct'}}})]

        output = self._catch_stdout(critterget.getUserflowsSummary, 'appId', 'appName', "UserflowsSummary")

        self.assertIn('MessageType=UserflowsSummary appName="appName" appId="appId" DATA ("bogusMetric",bogusValue,bogusPct)', output)

    def test_getUserflowsRanked(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, {'groups': [{'name': 'bogusName', 'failureRate': 'bogusRate', 'unit':{'type':'bogusType'}}]} )]

        output = self._catch_stdout(critterget.getUserflowsRanked, 'appId', 'appName', 'failed', "UserflowsRanked")

        self.assertIn('MessageType=UserflowsRanked appName="appName" appId="appId"  DATA ("bogusName",bogusRate,bogusType)', output)

    def test_getUserflowsChangeDetails(self):
        userflows_data = {'groups': [
            {'name': "Bogus",
             'series': {
                 'startedTransactions': {'value':'bogusVol'},
                 'meanForegroundTime': {'value':'bogusTime'},
                 'failedTransactions': {'value':'bogusFailed'},
                 'failRate': {'value':'bogusRate'},
                 'succeededTransactions': {'value':'bogusSuccess'},
                 'failedMoneyValue': {'value':'bogusRev'}
             }}
        ]}

        output = self._catch_stdout(critterget.getUserflowsChangeDetails, 'appId', 'appName', userflows_data)

        self.assertIn('MessageType=UserflowsChangeDetails appName="appName" appId="appId" DATA (Name="Bogus",volume=bogusVol,foregroundTime=bogusTimes,failed=bogusFailed,failRate=bogusRate%,successful=bogusSuccess,revenueAtRisk=$bogusRev)', output)

    def test_getUserflowsGroups(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, {'series': {'bogusTransaction': {'count': {'value': 'bogusCount'},
                                                                                                         'rate': {'value': 'bogusRate'},
                                                                                                         'moneyValue': {'value': 'bogusMoney'},
                                                                                                         'meanDuration': {'value': 'bogusMean'}
                                                                                                         }}} )]

        output = self._catch_stdout(critterget.getUserflowsGroups, 'appId', 'appName', 'bogusGroup')

        self.assertIn('MessageType=UserflowGroup appName="appName" appId="appId" Userflow="bogusGroup" DATA (Metric="bogusTransaction",count=bogusCount,rate=bogusRate%,moneyValue=$bogusMoney,meanDuration=bogusMean)', output)