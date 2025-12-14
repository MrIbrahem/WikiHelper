
import io
import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


class TestFileUpload(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.client = app.test_client()

    def test_upload_wikitext_file(self):
        data = {
            'title': 'Test Workspace',
            'wikitext_file': (io.BytesIO(b'This is content from file.'), 'test.wiki')
        }
        response = self.client.post('/new', data=data, content_type='multipart/form-data', follow_redirects=True)

        # Check if workspace was created
        self.assertIn(b'Workspace &#39;test-workspace&#39; created successfully.', response.data)

        # Check if content matches
        # The redirect goes to /w/test-workspace/edit
        # The edit page shows the content in the textarea
        self.assertIn(b'This is content from file.', response.data)

    def test_upload_overrides_textarea(self):
        data = {
            'title': 'Test Workspace 2',
            'wikitext': 'This text should be ignored.',
            'wikitext_file': (io.BytesIO(b'This is content from file.'), 'test2.wiki')
        }
        response = self.client.post('/new', data=data, content_type='multipart/form-data', follow_redirects=True)

        self.assertIn(b'Workspace &#39;test-workspace-2&#39; created successfully.', response.data)
        self.assertIn(b'This is content from file.', response.data)
        self.assertNotIn(b'This text should be ignored.', response.data)


if __name__ == '__main__':
    unittest.main()
