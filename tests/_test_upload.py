
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from src.app import app


class TestFileUpload(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test workspaces
        self.test_dir = Path(tempfile.mkdtemp())

        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        app.config['WIKI_WORK_ROOT'] = self.test_dir  # Use temp directory for tests
        self.client = app.test_client()

    def tearDown(self):
        # Clean up the temporary directory after each test
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

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

    def test_line_count_preserved(self):
        """Test that line count is preserved after upload (no extra blank lines)"""
        # Original Infobox text with specific line count
        original_text = """{{Infobox administration
| image = President Rodrigo Duterte portrait (half-body crop).jpg
| name = Presidency of Rodrigo Duterte
| term_start = June 30, 2016
| term_end = June 30, 2022
| president = Rodrigo Roa Duterte
| seat = [[قصر مالاكانانغ]], [[مانيلا]]
| party = [[PDP–Laban]]
| predecessor = [[Presidency of Benigno Aquino III|Benigno Aquino III]]
| successor = [[Presidency of Bongbong Marcos|Bongbong Marcos]]
| president_link = President of the Philippines
| election = [[2016 Philippine presidential election|2016]]
| cabinet = ''[[#Administration and cabinet|See list]]''
}}"""

        # Count original lines
        original_lines = original_text.split('\n')
        original_line_count = len(original_lines)

        print("\n=== Line Count Test ===")
        print(f"Original line count: {original_line_count}")
        print(f"Original text:\n{original_text}")
        print("=" * 50)

        # Upload as file
        data = {
            'title': 'Test Infobox',
            'wikitext_file': (io.BytesIO(original_text.encode('utf-8')), 'infobox.wiki')
        }
        response = self.client.post('/new', data=data, content_type='multipart/form-data', follow_redirects=True)

        # Check workspace was created
        self.assertIn(b'Workspace &#39;test-infobox&#39; created successfully.', response.data)

        # Extract the textarea content from response
        response_text = response.data.decode('utf-8')

        # Find textarea content
        import re
        textarea_match = re.search(r'<textarea[^>]*>([^<]*)</textarea>', response_text, re.DOTALL)
        self.assertIsNotNone(textarea_match, "Could not find textarea in response")

        saved_text = textarea_match.group(1)
        saved_text = saved_text.replace('&lt;', '<').replace('&gt;', '>').replace('&#39;', "'").replace('&amp;', '&')

        # Count saved lines
        saved_lines = saved_text.split('\n')
        saved_line_count = len(saved_lines)

        print(f"\nSaved line count: {saved_line_count}")
        print(f"Saved text:\n{saved_text}")
        print("=" * 50)

        # Print line-by-line comparison
        print("\n=== Line-by-Line Comparison ===")
        max_lines = max(original_line_count, saved_line_count)
        for i in range(max_lines):
            orig_line = original_lines[i] if i < original_line_count else "[MISSING]"
            saved_line = saved_lines[i] if i < saved_line_count else "[MISSING]"
            match = "✓" if orig_line == saved_line else "✗"
            print(f"{match} Line {i+1:2d}: Original: {repr(orig_line)}")
            print(f"          Saved:    {repr(saved_line)}")

        # Assert line counts match
        self.assertEqual(original_line_count, saved_line_count,
                         f"Line count mismatch! Original: {original_line_count}, Saved: {saved_line_count}")

        # Assert content matches (accounting for ref extraction)
        # Note: This test checks editable.wiki which has refs replaced with placeholders


if __name__ == '__main__':
    unittest.main()
