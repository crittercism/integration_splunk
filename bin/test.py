import unittest
import mock
import critterget

class TestSplunk(unittest.TestCase):
    def setUp(self):
        self.debug = 1

    def tearDown(self):
        pass

    def testGetCredentials(self):
        credentials = critterget.getCredentials('session_key')
        self.assertEqual(credentials, 'boguspassword')

    @mock.patch('critterget.apicall.request')
    def testGetOk(self, mock_get):
        mock_response = mock.Mock()
        expected_dict = {'appID': {'bogusresponse': 'bogusdata'}}

        mock_response.json.return_value = expected_dict

        mock_get.return_value = mock_response

        response_dict = critterget.apicall('uri', 'attribs')

        mock_get.assert_called_once_with('uri')
        self.assertEqual(1, mock_response.json.call_count)
        self.assertEqual(response_dict, expected_dict)
