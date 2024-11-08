import unittest
from modules.web_scraper import WebScraper

class WebScraperTestCase(unittest.TestCase):
    def setUp(self):
        self.scraper = WebScraper()

    def test_fetch_webpage(self):
        result = self.scraper.fetch_webpage("https://en.wikipedia.org/wiki/Earth")
        self.assertIsNotNone(result)
        self.assertIn("Earth", result)  # Assuming "Earth" will be in the content

    def test_extract_content(self):
        html_content = "<html><body><p>Some content</p><script>Some script</script></body></html>"
        result = self.scraper.extract_content(html_content)
        self.assertIsNotNone(result)
        self.assertIn("Some content", result)
        self.assertNotIn("Some script", result)

    def test_process_text(self):
        test_text = '''
The US government has brought charges against an Iranian man in connection with an alleged plot to assassinate Donald Trump before he was elected as the next president.
The Department of Justice on Friday unsealed an indictment against Farhad Shakeri, 51, alleging he was tasked with "providing a plan" to kill Trump.
The US government said Mr Shakeri has not been arrested and is believed to be in Iran.
        '''
        result = self.scraper.process_text(test_text)
        self.assertIsNotNone(result)
        self.assertIn("The US government has brought charges", result)

    def test_scrape_article(self):
        result = self.scraper.scrape_article(url="https://en.wikipedia.org/wiki/Earth")
        self.assertIsNotNone(result)
        self.assertIn('content', result)
        self.assertIn('title', result)
        self.assertIn('Earth', result['title'])
        self.assertTrue(len(result['content']) > 100)  # Assuming content will be substantial

if __name__ == '__main__':
    unittest.main()