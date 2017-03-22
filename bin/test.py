import unittest
import sys
from StringIO import StringIO
import datetime
import mock

import critterget


class TestSplunk(unittest.TestCase):

    def setUp(self):
        # Turn on critterget's debug messages
        critterget.DEBUG = 1

        # By default, critterget's access_token variable is an empty string
        # The access_token must be NOT an empty string
        # for critterget to run properly
        critterget.ACCESS_TOKEN = "bogustoken"

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

    # This method was lifted from
    # cypythonlib/soaclients/tests/unit/test_ams_wrapper.py
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
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'bogusappID': {'bogusresponse': 'bogusdata'}}
        )]
        test_response = critterget.apicall('endpoint', 'attribute string')
        self.assertEqual(
            test_response,
            {'bogusappID': {'bogusresponse': 'bogusdata'}}
        )

    def test_getAppSummary(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data':
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
            }
        )]
        apps = critterget.getAppSummary()
        self.assertEqual(apps.keys()[0], 'bogusappID')
        self.assertEqual(apps[apps.keys()[0]]['name'], 'bogusApp')
        self.assertEqual(apps[apps.keys()[0]]['versions'], ['bogus.version'])

    def test_scopetime(self):
        test_time = critterget.scopetime()
        interval_time = datetime.datetime.utcnow() - datetime.timedelta(
            minutes=10
        )
        self.assertLessEqual(test_time, interval_time.isoformat())

    def test_get_error_summary_timeout(self):
        self.mock_get.side_effect = [self._response_with_json_data(404, [])]
        critterget.MAX_RETRY = 0
        output = self._catch_stdout(critterget.get_error_summary,
                                    'bogusappID',
                                    'bogusName',
                                    'crash')

        critterget.MAX_RETRY = 10
        self.assertIn('MessageType="CrashSummary" appId=bogusappID '
                      'appName="bogusName" Could not get error summaries for',
                      output)
        self.assertIn('Code: 404 after retry 1', output)

    def test_get_breadcrumbs(self):
        crumbs = [{u'appVersion': u'bogusVersion',
                   u'device': u'bogusDevice',
                   u'deviceId': u'bogusID',
                   u'os': u'bogusOS',
                   u'parsedBreadcrumbs': [
                       {
                           u'deviceOccurredTs': u'bogusTime',
                           u'payload': {
                               u'priority': u'normal',
                               u'text': u'session_start'
                           },
                           u'type': u'bogusType',
                           u'typeCode': 1
                       },
                       {u'deviceOccurredTs': u'bogusTime+1',
                        u'payload': {
                            u'priority': u'normal',
                            u'text': u'Breadcrumb: RuntimeException '
                                     u'Symbolication Test Handled Exception'
                        },
                        u'type': u'bogusType',
                        u'typeCode': 1}]}]

        output = self._catch_stdout(critterget.get_breadcrumbs,
                                    crumbs,
                                    'fakeHash',
                                    'appName')

        self.assertIn('trace="[\'deviceOccurredTs\': \'bogusTime\', \'type\':'
                      ' \'bogusType\', \'payload\': \'priority\': \'normal\', '
                      '\'text\': \'session_start\', \'typeCode\': 1|'
                      '\'deviceOccurredTs\': \'bogusTime+1\', \'type\': '
                      '\'bogusType\', \'payload\': \'priority\': \'normal\', '
                      '\'text\': \'Breadcrumb: RuntimeException Symbolication '
                      'Test Handled Exception\', \'typeCode\': 1]" os="bogusOS"'
                      ' appVersion="bogusVersion" device="bogusDevice"', output)

    def test_getStacktrace(self):
        trace = [{"bogusLine": 0, "bogusTrace": "fakelib"}]

        output = self._catch_stdout(
            critterget.getStacktrace, trace, 'fakeHash')

        self.assertIn('MessageType="CrashDetailStacktrace"  hash=fakeHash  '
                      '[\n\t{\n\t\t\'bogusTrace\': \'fakelib\',\n\t\t\'bogusLine'
                      '\': 0\n\t}\n]\n', output)

    def test_diag_geo(self):
        geo_data = {'fakeCountry':
                    {'fakeCity': ['fakeLat', 'fakeLon', 'fakeCrashes']}
                   }

        output = self._catch_stdout(critterget.diag_geo, geo_data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsGeo" hash=fakeHash '
                      'country="fakeCountry" city="fakeCity" lat=fakeLat '
                      'lon=fakeLon crashes="fakeCrashes"', output)

    def test_diag_discrete(self):
        data = {'fakeStat': [['fakeVar', 'fakeVal']]}

        output = self._catch_stdout(critterget.diag_discrete, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsDiscrete"  hash=fakeHash  '
                      '"fakeStat:fakeVar"="fakeVal"', output)

    def test_diag_affected_users(self):
        data = {'fakeUser': {'fakeStat': 'fakeData'}}

        output = self._catch_stdout(
            critterget.diag_affected_users,
            data,
            'fakeHash'
        )

        self.assertIn('MessageType="CrashDiagsAffectedUser"  hash=fakeHash '
                      ' userhash=fakeUser  fakeStat="fakeData"', output)

    def test_diag_affected_versions(self):
        data = [['fakeVersion', 'fakeData']]

        output = self._catch_stdout(
            critterget.diag_affected_versions,
            data,
            'fakeHash'
        )

        self.assertIn('MessageType="CrashDiagsAffectedVersions"  '
                      'hash=fakeHash  "fakeVersion"=fakeData', output)

    def test_diag_cont_bar(self):
        data = {'bogusStat':
                {'bogusCategories': ['bogusCategory'],
                 'bogusData': ['bogusPoint']}
               }

        output = self._catch_stdout(critterget.diag_cont_bar, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsContBar"  '
                      'hash=fakeHash datatype=bogusStat  '
                      '"bogusPoint"=bogusCategory', output)

    def test_diag_cont(self):
        data = {'bogusStat': {'bogusAve': 'X.X',
                              'bogusMax': 'Y.Y',
                              'bogusMin': 'Z.Z'}}

        output = self._catch_stdout(critterget.diag_cont, data, 'fakeHash')

        self.assertIn('MessageType="CrashDiagsContinuous"  hash=fakeHash  '
                      'bogusStat_bogusAve="X.X" bogusStat_bogusMin="Z.Z" '
                      'bogusStat_bogusMax="Y.Y"', output)

    def test_getDiagnostics(self):
        diags = {'bogusKey': 'bogusData'}

        output = self._catch_stdout(
            critterget.getDiagnostics,
            diags,
            'fakeHash'
        )

        self.assertIn('--UNPROCESSED----bogusKey - bogusData', output)

    def test_getDOBV(self):
        data = {'bogusVersion': ['bogusDate', ['bogusData']]}

        output = self._catch_stdout(critterget.getDOBV, data, 'fakeHash')

        self.assertIn('MessageType="CrashDetailDailyOccurrencesByVersion"  '
                      'hash=fakeHash  {\n\t\'bogusVersion\': [\n\t\t\'bogusDate'
                      '\',\n\t\t[\n\t\t\t\'bogusData\'\n\t\t]\n\t]\n}', output)

    def test_getUSCBV(self):
        data = {'fakeVersion': 'fakeCrashes', 'bogusTotal': 'fakeTotalCrashes'}

        output = self._catch_stdout(critterget.getUSCBV, data, 'fakeHash')

        self.assertIn('MessageType="CrashDetailUniqueSessionCountsByVersion"  '
                      'hash=fakeHash  {\n\t\'fakeVersion\': \'fakeCrashes\''
                      ',\n\t\'bogusTotal\': \'fakeTotalCrashes\'\n}', output)

    def test_getSCBV(self):
        data = {'bogusVersion': 'bogusSessions'}

        output = self._catch_stdout(critterget.getSCBV, data, 'fakeHash')

        self.assertIn('MessageType="CrashDetailSessionCountsByVersion"  '
                      'hash=fakeHash  {\n\t\'bogusVersion\': '
                      '\'bogusSessions\'\n}', output)

    def test_getSymStacktrace(self):
        data = ['fakeTraceOne', 'fakeTraceTwo']

        output = self._catch_stdout(
            critterget.getSymStacktrace,
            data,
            'fakeHash'
        )

        self.assertIn('MessageType="CrashDetailSymbolizedStacktrace"  '
                      'hash=fakeHash  [\n\t\'fakeTraceOne\',\n\t'
                      '\'fakeTraceTwo\'\n]', output)

    def test_getCrashDetail(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': {'bogusStat': 'bogusValue'}}
        )]

        output = self._catch_stdout(
            critterget.getCrashDetail,
            'fakeHash',
            'fakeId',
            'fakeApp'
        )

        self.assertIn('/crash/fakeId/fakeHash', output)
        self.assertIn('MessageType="CrashDetail"  appName="fakeApp" '
                      'bogusStat="bogusValue"', output)

    def test_getErrorSummary(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': {'series': [{'points': ['bogusPoint']}]}}
        )]

        output = self._catch_stdout(
            critterget.getErrorSummary,
            'fakeApp',
            'appName')

        self.assertIn('MessageType=HourlyAppLoads AppLoads=bogusPoint '
                      'appId="fakeApp" appName="appName"', output)

    def test_getCrashesByOS(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data':
             {'slices': [{'label': 'bogusLabel', 'value': 'bogusValue'}]}
            }
        )]

        output = self._catch_stdout(
            critterget.getCrashesByOS,
            'appId',
            'appName'
        )

        self.assertIn('MessageType=DailyCrashesByOS appName="appName" '
                      'appId="appId" DATA ("bogusLabel",bogusValue)', output)

    def test_getDailyAppLoads(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': {'series': [{'points': ['bogusPoint']}]}}
        )]

        output = self._catch_stdout(
            critterget.getDailyAppLoads,
            'appId',
            'appName'
        )

        self.assertIn('MessageType=DailyAppLoads appName="appName" '
                      'appId="appId" dailyAppLoads=bogusPoint', output)

    def test_getDailyCrashes(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': ['bogusData', {'value': 'bogusValue'}]}
        )]

        output = self._catch_stdout(
            critterget.getDailyCrashes,
            'appId',
            'appName'
        )

        self.assertIn('MessageType=DailyCrashes appName="appName" '
                      'appId="appId" dailyCrashes=bogusValue', output)

    def test_getGenericPerfMgmt(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data':
             {'slices': [{'label': 'bogusLabel', 'value': 'bogusValue'}]}
            }
        )]

        output = self._catch_stdout(critterget.getGenericPerfMgmt,
                                    'appId', 'appName', 'bogusGraph',
                                    'bogusGroup', 'bogusMessageType'
                                   )

        self.assertIn('MessageType=bogusMessageType appName="appName" '
                      'appId="appId"  DATA ("bogusLabel",bogusValue)', output)

    def test_getGenericErrorMon(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data':
             {'slices': [{'label': 'bogusLabel', 'value': 'bogusValue'}]}
            }
        )]

        output = self._catch_stdout(critterget.getGenericErrorMon,
                                    'appId', 'appName', 'bogusGraph',
                                    'bogusGroup', 'bogusMessageType')

        self.assertIn('MessageType=bogusMessageType appName="appName" '
                      'appId="appId"  DATA ("bogusLabel",bogusValue)', output)

    def test_getGenericErrorMon_no_data(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': {'slices': []}}
        )]

        output = self._catch_stdout(critterget.getGenericErrorMon,
                                    'appId', 'appName', 'bogusGraph',
                                    'bogusGroup', 'bogusMessageType')

        self.assertIn('MessageType="ApteligentError" Error: API did not '
                      'return bogusMessageType data for appId. Returned '
                      '{\'slices\': []}', output)

    def test_getGenericErrorMon_bad_response(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'error': 'something happened'}
        )]

        output = self._catch_stdout(critterget.getGenericErrorMon,
                                    'appId', 'appName', 'bogusGraph',
                                    'bogusGroup', 'bogusMessageType')

        self.assertIn('MessageType="ApteligentError" Error: API returned '
                      'malformed data in \'data\' of bogusMessageType. Data: '
                      '{\'error\': \'something happened\'}', output)

    def test_getAPMEndpoints(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data':
             {'endpoints': [{'domain': 'bogusD', 'uri': 'bogusU', 'sort': 'bogusS'}]}
            }
        )]

        output = self._catch_stdout(
            critterget.getAPMEndpoints,
            'appId',
            'appName',
            'bogusMetric',
            'bogusMessageType'
        )

        self.assertIn('MessageType=bogusMessageType appName="appName" '
                      'appId="appId"  DATA ("bogusDbogusU",bogusS)', output)

    def test_getAPMServices(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': {'services': [
                {'name': 'bogusName', 'sort': 'bogusSort'}]}}
        )]

        output = self._catch_stdout(
            critterget.getAPMServices,
            'appId',
            'appName',
            'bogusMetric',
            'bogusMessageType'
        )

        self.assertIn('MessageType=bogusMessageType appName="appName" '
                      'appId="appId"  DATA ("bogusName",bogusSort)', output)

    def test_getAPMGeo(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': {'series': [{'geo': {'BogusCountry': 'bogusStat'}}]}}
        )]

        output = self._catch_stdout(
            critterget.getAPMGeo,
            'appId',
            'appName',
            'bogusMetric',
            'bogusMessageType')

        self.assertIn('MessageType=bogusMessageType appName="appName" '
                      'appId="appId"  DATA ("BogusCountry",bogusStat)', output)

    def test_getTopValues(self):
        trendsData = {
            u'series':
                {u'crashesByVersion':
                     {u'todayTopValues':
                      {'bogusVersion': 'bogusCrashes'}},
                 u'appLoadsByVersion':
                 {u'todayTopValues': {'bogusVersion': 'bogusAppLoads'}},
                 u'appLoadsByOs':
                 {u'todayTopValues': {'bogusOS': 'bogusAppLoads'}},
                 u'crashesByOs':
                     {u'todayTopValues': {'bogusOS': 'bogusCrashes'}}
                }
        }

        output = self._catch_stdout(
            critterget.getTopValues,
            'appId',
            'appName',
            trendsData
        )

        self.assertIn('MessageType=crashesByVersion appName="appName" appId='
                      '"appId" DATA ("bogusVersion",bogusCrashes),', output)
        self.assertIn('MessageType=appLoadsByVersion appName="appName" appId='
                      '"appId" DATA ("bogusVersion",bogusAppLoads),', output)
        self.assertIn('MessageType=appLoadsByOs appName="appName" appId="appId"'
                      ' DATA ("bogusOS",bogusAppLoads),', output)
        self.assertIn('MessageType=crashesByOs appName="appName" appId="appId" '
                      'DATA ("bogusOS",bogusCrashes),', output)

    def test_getTimeseriesTrends(self):
        trendsData = {
            u'series':
            {u'crashesByVersion':
             {u'categories':
              {'bogusVersion':
               {'buckets': [
                   {u'start':
                    'YYYY-MM-DDTHH:MM:SS+TZ:TZ',
                    u'value': 'bogusVal'
                   }
               ]
               }
              }
             }
            }
        }

        output = self._catch_stdout(
            critterget.getTimeseriesTrends,
            'appId',
            'appName',
            trendsData
        )

        self.assertIn('MessageType=TimeseriesTrends appName="appName" appId='
                      '"appId" appVersion="bogusVersion" DATA '
                      '(YYYY-MM-DD,bogusVal)', output)

    def test_getUserflowsSummary(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data':
             {'bogusMetric':
              {'value': 'bogusValue', 'changePct': 'bogusPct'}}
            }
        )]

        output = self._catch_stdout(
            critterget.getUserflowsSummary,
            'appId',
            'appName',
            "UserflowsSummary"
        )

        self.assertIn('MessageType=UserflowsSummary appName="appName" '
                      'appId="appId" DATA ("bogusMetric",bogusValue,bogusPct)',
                      output)

    def test_getUserflowsRanked(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': [{'name': 'bogusName',
                       'failureRate': 'bogusRate',
                       'unit': {'type': 'bogusType'}}]
            }
        )]

        output = self._catch_stdout(
            critterget.getUserflowsRanked,
            'appId',
            'appName',
            'failed',
            "UserflowsRanked"
        )

        self.assertIn('MessageType=UserflowsRanked appName="appName" '
                      'appId="appId"  DATA ("bogusName",bogusRate,bogusType)',
                      output)

    def test_getUserflowsChangeDetails(self):
        userflows_data = [
            {'name': "Bogus",
             'series': {
                 'startedTransactions': {'value': 'bogusVol'},
                 'meanForegroundTime': {'value': 'bogusTime'},
                 'failedTransactions': {'value': 'bogusFailed'},
                 'failRate': {'value': 'bogusRate'},
                 'succeededTransactions': {'value': 'bogusSuccess'},
                 'failedMoneyValue': {'value': 'bogusRev'}
             }}
        ]

        output = self._catch_stdout(
            critterget.getUserflowsChangeDetails,
            'appId',
            'appName',
            userflows_data
        )

        self.assertIn('MessageType=UserflowsChangeDetails appName="appName" '
                      'appId="appId" DATA (Name="Bogus",volume=bogusVol,'
                      'foregroundTime=bogusTimes,failed=bogusFailed,failRate='
                      'bogusRate%,successful=bogusSuccess,revenueAtRisk='
                      '$bogusRev)', output)

    def test_getUserflowsGroups(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data':
             {'series':
              {'bogusTransaction':
               {'count': {'value': 'bogusCount'},
                'rate': {'value': 'bogusRate'},
                'moneyValue': {'value': 'bogusMoney'},
                'meanDuration': {'value': 'bogusMean'}
               }
              }
             }
            }
        )]

        output = self._catch_stdout(
            critterget.getUserflowsGroups,
            'appId',
            'appName',
            'bogusGroup'
        )

        self.assertIn('MessageType=UserflowGroup appId="appId" '
                      'appName="appName" Userflow="bogusGroup" DATA '
                      '(Metric="bogusTransaction",count=bogusCount,'
                      'rate=bogusRate%,moneyValue=$bogusMoney,'
                      'meanDuration=bogusMean)', output)

    @mock.patch.object(critterget, 'getUserflowsGroups')
    def test_getUserflowsDetails(self, mock_userflow):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': [
                {
                    'name': 'bogusName'
                }
                ]
            }
        )]

        critterget.getUserflowsDetails('appId', 'appName')

        self.assertTrue(mock_userflow.called)

    def test_get_error_summary_exception(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': [{
                'displayReason': None,
                'hash': 'bogusHash',
                'lastOccurred': '2016-10-25T15:02:33.861761',
                'name': 'bogusName',
                'reason': 'because',
                'sessionCount': 1,
                'status': 'known',
                'uniqueSessionCount': 1
            }]}
        )]
        output = self._catch_stdout(
            critterget.get_error_summary,
            'appId',
            'appName',
            'exception'
        )

        self.assertIn('MessageType="ExceptionSummary" appId=appId '
                      'appName="appName" displayReason="None" hash="bogusHash" '
                      'lastOccurred="2016-10-25T15:02:33.861761" '
                      'name="bogusName" reason="because" sessionCount="1" '
                      'status="known" uniqueSessionCount="1"',
                      output)

    def test_get_error_summary_crash(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': [{
                'displayReason': None,
                'hash': 'bogusHash',
                'lastOccurred': '2016-10-25T15:02:33.861761',
                'name': 'bogusName',
                'reason': 'because',
                'sessionCount': 1,
                'status': 'known',
                'uniqueSessionCount': 1
            }]}
        )]
        output = self._catch_stdout(
            critterget.get_error_summary,
            'appId',
            'appName',
            'crash'
        )

        self.assertIn('MessageType="CrashSummary" appId=appId '
                      'appName="appName" displayReason="None" hash="bogusHash" '
                      'lastOccurred="2016-10-25T15:02:33.861761" '
                      'name="bogusName" reason="because" sessionCount="1" '
                      'status="known" uniqueSessionCount="1"',
                      output)

    def test_get_error_counts_exceptions(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': [
                {
                    'date': 'bogusDate',
                    'value': 'bogusValue'
                }
            ]}
        )]
        output = self._catch_stdout(
            critterget.get_error_counts,
            'appId',
            'appName',
            'exception'
        )
        self.assertIn('MessageType=ExceptionCounts appName="appName" '
                      'appId="appId" DATA (bogusDate,bogusValue)',
                      output)

    def test_get_error_counts_crashes(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'data': [
                {
                    'date': 'bogusDate',
                    'value': 'bogusValue'
                }
            ]}
        )]
        output = self._catch_stdout(
            critterget.get_error_counts,
            'appId',
            'appName',
            'crash'
        )
        self.assertIn('MessageType=CrashCounts appName="appName" '
                      'appId="appId" DATA (bogusDate,bogusValue)',
                      output)

    def test_get_exception_details(self):
        self.mock_get.side_effect = [
            self._response_with_json_data(
                200,
                {
                    'data': {
                        'errors': [
                            {
                                'hash': 'bogusHash',
                                'bogusAttr': 'bogusValue'
                            }
                        ],
                        'pagination': {
                            'pageNum': 1,
                            'totalPages': 2
                        }
                    }
                }
            ),
            self._response_with_json_data(
                200,
                {
                    'data': {
                        'errors': [
                            {
                                'hash': 'bogusHash',
                                'bogusAttr': 'bogusValue'
                            }
                        ],
                        'pagination': {
                            'pageNum': 1,
                            'totalPages': 2
                        }
                    }
                }
            ),
            self._response_with_json_data(
                200,
                {
                    'data': {
                        'errors': [
                            {
                                'hash': 'bogusHashSecond',
                                'bogusParam': 'bar'
                            }
                        ],
                        'pagination': {
                            'pageNum': 2,
                            'totalPages': 2
                        }
                    }
                }
            )
        ]

        output = self._catch_stdout(
            critterget.get_error_details,
            'appId',
            'appName',
            'exception'
        )
        self.assertIn('MessageType="ExceptionDetail" appId=appId '
                      'appName=appName exceptionHash="bogusHash"'
                      'bogusAttr="bogusValue"',
                      output)

    def test_get_all_pages(self):
        self.mock_get.side_effect = [
            self._response_with_json_data(
                200,
                {
                    'data': {
                        'bogusParam': ['foo', 'bar'],
                        'pagination': {
                            'pageNum': 1,
                            'totalPages': 2
                        }
                    }
                }
            ),
            self._response_with_json_data(
                200,
                {
                    'data': {
                        'bogusParam': ['foo', 'bar'],
                        'pagination': {
                            'pageNum': 1,
                            'totalPages': 2
                        }
                    }
                }
            ),
            self._response_with_json_data(
                200,
                {
                    'data': {
                        'bogusParam': ['baz', 'qux'],
                        'pagination': {
                            'pageNum': 2,
                            'totalPages': 2
                        }
                    }
                }
            )
        ]

        all_pages = critterget.get_all_pages('bogusUrl')

        page_one = all_pages.next()['data']['bogusParam']
        page_two = all_pages.next()['data']['bogusParam']

        _, kwargs = self.mock_get.call_args
        self.assertEqual(page_one, ['foo', 'bar'])
        self.assertEqual(page_two, ['baz', 'qux'])
        self.assertEqual(kwargs['params'], {'pageNum': 2})

    @mock.patch.object(critterget, 'get_all_pages')
    @mock.patch.object(critterget, 'get_error_summary')
    @mock.patch.object(critterget, 'getAppSummary')
    def test_main(self, app_mock, crash_mock, all_pages_mock):
        crash_mock.return_value = {'bogusHash': {'name': 'bogusApp'}}
        app_mock.return_value = {'bogusappID': {
            'name': 'bogusApp',
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
        all_pages_mock.return_value = {}
        old_in = sys.stdin
        sys.stdin = mock.MagicMock
        readline = mock.MagicMock(return_value="bogusKey")
        sys.stdin.readline = readline
        critterget.main()
        sys.stdin = old_in

        self.assertTrue(app_mock.called)
        self.assertTrue(crash_mock.called)

    def test_time_floor(self):
        sample_time = datetime.datetime(2016, 2, 10, 12, 4, 32, 123456)
        floored_time = critterget.time_floor(sample_time)

        self.assertEqual(floored_time,
                         datetime.datetime(2016, 2, 10, 12, 0, 0, 123456))

    def test_splunk_api_call(self):
        self.mock_get.side_effect = [self._response_with_json_data(
            200,
            {'splunk response'}
        )]

        splunk_call = critterget.splunk_api_call('/bogus/endpoint',
                                                 'GET',
                                                 'bogus_key')

        self.assertEqual(splunk_call, {'splunk response'})
        self.assertEqual(self.mock_get.call_args[0],
                         ('https://localhost:8089/bogus/endpoint',))
        self.assertEqual(self.mock_get.call_args[1],
                          {'verify': False, 'params': {'output_mode': 'json'},
                           'headers': {'Authorization': 'Splunk bogus_key'}})

    def test_run_splunk_search(self):
        self.mock_get.side_effect = [
            self._response_with_json_data(
                200,
                {'entry': [
                {'name': 'wrong_search',
                 'links': 'bogus.com'},
                {'name': 'right_search',
                 'links': {
                     'dispatch': '/dispatch/search'
                 }}
            ]}),
            self._response_with_json_data(
                200, {'results': 'bogus_search_results'}
            )
        ]
        self.mock_post.side_effect = [
            self._response_with_json_data(
                200,
            {'sid': 'bogus_sid'}
            )
        ]
        results = critterget.run_splunk_search('right_search',
                                               'bogus_session_key')
        print results
        self.assertEqual(results, {'results': 'bogus_search_results'})
