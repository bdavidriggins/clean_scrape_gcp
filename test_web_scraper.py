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
        test_text = '''
The US government has brought charges against an Iranian man in connection with an alleged plot to assassinate Donald Trump before he was elected as the next president.

The Department of Justice on Friday unsealed an indictment against Farhad Shakeri, 51, alleging he was tasked with “providing a plan” to kill Trump.

The US government said Mr Shakeri has not been arrested and is believed to be in Iran.

In a criminal complaint filed in Manhattan court, prosecutors allege that an official in Iran’s Revolutionary Guard directed Mr Shakeri in September to devise a plan to surveil and kill Trump.

“The Justice Department has charged an asset of the Iranian regime who was tasked by the regime to direct a network of criminal associates to further Iran’s assassination plots against its targets, including President-elect Donald Trump,” US Attorney General Merrick Garland said in a statement.
                '''
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