import unittest
from modules.web_scraper import WebScraper
from unittest.mock import patch, MagicMock

class WebScraperTestCase(unittest.TestCase):
    def setUp(self):
        self.scraper = WebScraper()

    @patch('modules.web_scraper.requests_html.HTMLSession')
    def test_fetch_webpage(self, mock_session):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.html.html = "<html><body>Test content</body></html>"
        mock_session.return_value.get.return_value = mock_response

        result = self.scraper.fetch_webpage("https://example.com")
        self.assertIsNotNone(result)
        self.assertIn("Test content", result)

    @patch('modules.web_scraper.trafilatura.extract')
    def test_extract_content(self, mock_extract):
        mock_extract.return_value = "Extracted content"
        html_content = "<html><body><p>Some content</p></body></html>"
        
        result = self.scraper.extract_content(html_content)
        self.assertEqual(result, "Extracted content")

    def test_process_text(self):
        test_text = "This is a test sentence. Another sentence here."
        result = self.scraper.process_text(test_text)
        self.assertIsNotNone(result)
        self.assertIn("This is a test sentence.", result)

    @patch('modules.web_scraper.WebScraper._fetch_with_fallback')
    @patch('modules.web_scraper.WebScraper.extract_content')
    @patch('modules.web_scraper.WebScraper.process_text')
    def test_scrape_article(self, mock_process, mock_extract, mock_fetch):
        mock_fetch.return_value = "<html><body>Test HTML</body></html>"
        mock_extract.return_value = "Extracted content"
        mock_process.return_value = "Processed content"

        result = self.scraper.scrape_article(url="https://example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result['content'], "Processed content")

if __name__ == '__main__':
    unittest.main()