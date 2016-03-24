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
                                                                         'role': 'bogusRole'}
                                                                    }
                                                                   )
                                     ]
        apps = critterget.getAppSummary()
        self.assertEqual(apps.keys()[0], 'bogusappID')
        self.assertEqual(apps[apps.keys()[0]], 'bogusApp')

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
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        critterget.getBreadcrumbs(crumbs, 'fakeHash', 'appName')
        output = out.getvalue()
        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType="CrashDetailBreadcrumbs" hash=fakeHash  aCrumb="bogusCrumb"', output)

    def test_getStacktrace(self):
        trace = [{"bogusLine": 0, "bogusTrace": "fakelib"}]
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        critterget.getStacktrace(trace, 'fakeHash')
        output = out.getvalue()
        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType="CrashDetailStacktrace"  hash=fakeHash  [\n\t{\n\t\t\'bogusTrace\': \'fakelib\',\n\t\t\'bogusLine\': 0\n\t}\n]\n', output)
        pass

    def test_diag_geo(self):
        geo_data = {'fakeCountry': {'fakeCity': ['fakeLat', 'fakeLon', 'fakeCrashes']}}

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        critterget.diag_geo(geo_data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDiagsGeo" hash=fakeHash country="fakeCountry" city="fakeCity" lat=fakeLat lon=fakeLon crashes="fakeCrashes"', output)

    def test_diag_discrete(self):
        data = {'fakeStat': [['fakeVar', 'fakeVal']]}

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        critterget.diag_discrete(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDiagsDiscrete"  hash=fakeHash  "fakeStat:fakeVar"="fakeVal"', output)

    def test_diag_affected_users(self):
        data = {'fakeUser': {'fakeStat': 'fakeData'}}

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        critterget.diag_affected_users(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDiagsAffectedUser"  hash=fakeHash  userhash=fakeUser  fakeStat="fakeData"', output)

    def test_diag_affected_versions(self):
        data = [['fakeVersion', 'fakeData']]
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        critterget.diag_affected_versions(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDiagsAffectedVersions"  hash=fakeHash  "fakeVersion"=fakeData', output)

    def test_diag_cont_bar(self):
        data = {'bogusStat': {'bogusCategories': ['bogusCategory'], 'bogusData': ['bogusPoint']}}
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        critterget.diag_cont_bar(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDiagsContBar"  hash=fakeHash datatype=bogusStat  "bogusPoint"=bogusCategory', output)

    def test_diag_cont(self):
        data = {'bogusStat': {'bogusAve': 'X.X',
                'bogusMax': 'Y.Y',
                'bogusMin': 'Z.Z'}}
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out

        critterget.diag_cont(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDiagsContinuous"  hash=fakeHash  bogusStat_bogusAve="X.X" bogusStat_bogusMin="Z.Z" bogusStat_bogusMax="Y.Y"', output)

    def test_getDiagnostics(self):
        diags = {'bogusKey': 'bogusData'}
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out

        critterget.getDiagnostics(diags, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('--UNPROCESSED----bogusKey - bogusData', output)

    def test_getDOBV(self):
        data = {'bogusVersion': ['bogusDate',['bogusData']]}
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out

        critterget.getDOBV(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDetailDailyOccurrencesByVersion"  hash=fakeHash  {\n\t\'bogusVersion\': [\n\t\t\'bogusDate\',\n\t\t[\n\t\t\t\'bogusData\'\n\t\t]\n\t]\n}', output)

    def test_getUSCBV(self):
        data = {'fakeVersion': 'fakeCrashes', 'bogusTotal': 'fakeTotalCrashes'}
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out

        critterget.getUSCBV(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDetailUniqueSessionCountsByVersion"  hash=fakeHash  {\n\t\'fakeVersion\': \'fakeCrashes\',\n\t\'bogusTotal\': \'fakeTotalCrashes\'\n}', output)

    def test_getSCBV(self):
        data = {'bogusVersion': 'bogusSessions'}
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out

        critterget.getSCBV(data, 'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('MessageType="CrashDetailSessionCountsByVersion"  hash=fakeHash  {\n\t\'bogusVersion\': \'bogusSessions\'\n}', output)

    def test_getSymStacktrace(self):
        data = ['fakeTraceOne', 'fakeTraceTwo']
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out

        critterget.getSymStacktrace(data,'fakeHash')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType="CrashDetailSymbolizedStacktrace"  hash=fakeHash  [\n\t\'fakeTraceOne\',\n\t\'fakeTraceTwo\'\n]', output)

    def test_getCrashDetail(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, {'bogusStat':'bogusValue'})]
        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out

        critterget.getCrashDetail('fakeHash', 'fakeApp')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout
        self.assertIn('reqstring is https://developers.crittercism.com/v1.0/crash/fakeHash?diagnostics=True', output)
        self.assertIn('MessageType="CrashDetail"  appName="fakeApp" bogusStat="bogusValue"', output)

    def test_getDailyAppLoads(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data':
                                                                              {'series':
                                                                                    [{'points': ['bogusPoint']}]
                                                                               }
                                                                          }
                                                                    )
                                      ]

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        appLoads = critterget.getDailyAppLoads('appId', 'appName')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType=DailyAppLoads appName="appName" appId="appId" dailyAppLoads=bogusPoint', output)
        self.assertIsNone(appLoads)

    def test_getDailyCrashes(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, ['bogusData', {'value': 'bogusValue'}])]

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        dailyCrashes = critterget.getDailyCrashes('appId', 'appName')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType=DailyCrashes appName="appName" appId="appId" dailyCrashes=bogusValue', output)
        self.assertIsNone(dailyCrashes)

    def test_getCrashCounts(self):
        self.mock_get.side_effect = [self._response_with_json_data(200, [{'date': 'bogusDateOne', 'value': 'bogusValueOne'},
                                                                         {'date': 'bogusDateTwo', 'value': 'bogusValueTwo'}])]

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        crashCounts = critterget.getCrashCounts('appId', 'appName')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType=CrashCounts appName="appName" appId="appId" DATA (bogusDateOne,bogusValueOne),(bogusDateTwo,bogusValueTwo)', output)
        self.assertIsNone(crashCounts)

    def test_getGenericPerfMgmt(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data': {'slices': [{'label': 'bogusLabel', 'value': 'bogusValue'}]}})]

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        perfMgmt = critterget.getGenericPerfMgmt('appId', 'appName', 'bogusGraph', 'bogusGroup', 'bogusMessageType')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType=bogusMessageType appName="appName" appId="appId"  DATA ("bogusLabel",bogusValue)', output)
        self.assertIsNone(perfMgmt)

    def test_getGenericErrorMon(self):
        self.mock_post.side_effect = [self._response_with_json_data(200, {'data': {'slices': [{'label': 'bogusLabel', 'value': 'bogusValue'}]}})]

        # Capture the initial state of stdout
        saved_stdout = sys.stdout

        # Capture stdout in a StringIO instance
        out = StringIO()
        sys.stdout = out
        errMon = critterget.getGenericPerfMgmt('appId', 'appName', 'bogusGraph', 'bogusGroup', 'bogusMessageType')
        output = out.getvalue()

        # Return stdout to its initial state
        sys.stdout = saved_stdout

        self.assertIn('MessageType=bogusMessageType appName="appName" appId="appId"  DATA ("bogusLabel",bogusValue)', output)
        self.assertIsNone(errMon)