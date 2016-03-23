import unittest
import sys
import StringIO
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

    def test_getDailyAppLoads(self):
        mock.patch('sys.stdout', new_callable=StringIO.StringIO)
        self.mock_post.side_effect = [self._response_with_json_data(200, [{}
                                                                          ]
                                                                    )
                                      ]
        appLoads = critterget.getDailyAppLoads('appId', 'appName')
        self.assertIsNone(appLoads)