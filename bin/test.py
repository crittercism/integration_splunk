import unittest

class TestSplunk(unittest.TestCase):
    def setUp(self):
        import critterget
        self.critterget = critterget

    def tearDown(self):
        pass

    def testBasic(self):
        cred = self.critterget.getCredentials('session_key')
        print cred
        self.assertEqual(cred, 'onepass')



# import splunk.entity as entity
# entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
#                             owner='nobody', sessionKey=sessionKey)

# entities = entity.getEntities(['properties', 'crittercism_integration','api'], namespace=myapp,
#                          owner='nobody', sessionKey=sessionKey)

# for i, c in entities.items():
#     return c['username'], c['clear_password']