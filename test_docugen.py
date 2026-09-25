import unittest
from main import app

class TestDocuGen(unittest.TestCase):
    def test_homepage(self):
        client = app.test_client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()