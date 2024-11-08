# modules/web_scraper.py

"""
Web Page Scraper
This Python module defines a WebScraper class designed for robust web scraping and content extraction.
It utilizes libraries such as requests, BeautifulSoup, and spacy to perform tasks ranging from fetching
webpages with retry logic to parsing and cleaning HTML content. The WebScraper class integrates
comprehensive configuration options for customizing request handling, including timeouts, retries,
and content validation settings, making it adaptable to various scraping scenarios. Key features
include the extraction of text content, metadata from HTML, and handling of both URL-based and
direct HTML content input. This module also includes detailed logging throughout the scraping
process to facilitate debugging and optimization.
"""

# Standard library imports
import os
import re
import time
import random
from typing import Optional, Dict, Any, Generator
from urllib.parse import urlparse
from dateutil import parser
import json

# Third-party imports
import requests
from bs4 import BeautifulSoup
import spacy

# Local imports
from modules.common_logger import setup_logger
from modules.config import initialize_nlp

class WebScraper:
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the WebScraper with configuration options."""
        self.logger = setup_logger("web_scraper")
        
        default_config = {
            'timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 2,
            'verify_ssl': True,
            'min_content_length': 1000,
            'max_content_length': 5000000,  # 5MB
        }
        
        # Update configuration with user-provided settings
        self.config = {**default_config, **(config or {})}
        
        # Initialize spaCy NLP model
        try:
            self.nlp = initialize_nlp()
        except Exception as e:
            self.logger.error(f"Failed to initialize NLP model: {str(e)}")
            raise

        # Initialize session
        self.session = requests.Session()
        self.session.verify = self.config['verify_ssl']

    def _get_random_user_agent(self) -> str:
        """Return a random user agent string."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        return random.choice(user_agents)

    def fetch_webpage(self, url: str) -> Optional[str]:
        """
        Fetch webpage content with retry mechanism.
        Args:
            url (str): The URL to fetch
        Returns:
            Optional[str]: HTML content if successfully retrieved, None otherwise
        """
        self.logger.info(f"Fetching webpage: {url}")
        
        for attempt in range(self.config['retry_attempts']):
            self.logger.info(f"Attempt {attempt + 1} of {self.config['retry_attempts']}")
            
            try:
                headers = {'User-Agent': self._get_random_user_agent()}
                response = self.session.get(url, timeout=self.config['timeout'], headers=headers)
                response.raise_for_status()
                
                content = response.text
                if self._is_valid_content(content):
                    self.logger.info("Successfully retrieved content")
                    return content
                
                self.logger.warning("Retrieved content is not valid")
                    
            except requests.RequestException as e:
                self.logger.warning(f"Fetch failed: {str(e)}")
            
            if attempt < self.config['retry_attempts'] - 1:
                wait_time = self._calculate_backoff(attempt)
                self.logger.info(f"Retrying after {wait_time} seconds...")
                time.sleep(wait_time)
        
        self.logger.error("Failed to retrieve content after all attempts")
        return None

    def _is_valid_content(self, content: Optional[str]) -> bool:
        """
        Validate if the retrieved content is proper HTML and has sufficient content.
        """
        if not content:
            return False
            
        # Check for basic HTML structure
        if not ('<html' in content and '</html>' in content):
            return False
            
        # Check for content length
        content_length = len(content)
        if content_length < self.config['min_content_length'] or content_length > self.config['max_content_length']:
            return False
            
        return True

    def extract_content(self, html_content: str) -> Optional[str]:
        """
        Extract main content from HTML.
        """
        self.logger.info("Extracting content")

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)

            self.logger.info(f"Successfully extracted content with length: {len(text)}")
            return text
            
        except Exception as e:
            self.logger.error(f"Content extraction failed: {str(e)}")
            return None

    def process_text(self, text: str) -> Optional[str]:
        """
        Process and clean text while preserving all sentences and structure.
        """
        try:
            self.logger.info(f"Processing text of length: {len(text)} characters")
            
            # Split text into paragraphs while preserving empty lines
            paragraphs = text.split('\n')
            processed_paragraphs = []
            
            for paragraph in paragraphs:
                if paragraph.strip():
                    doc = self.nlp(paragraph)
                    processed_sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
                    processed_paragraphs.append(' '.join(processed_sentences))
                else:
                    processed_paragraphs.append('')
            
            # Join paragraphs with newlines, preserving structure
            final_text = '\n'.join(processed_paragraphs)
            
            # Remove consecutive empty lines while preserving structure
            final_text = re.sub(r'\n{3,}', '\n\n', final_text)
            
            self.logger.info(f"Successfully processed text: {len(final_text)} characters")
            return final_text
            
        except Exception as e:
            self.logger.error(f"Error processing text: {str(e)}", exc_info=True)
            return None

    def extract_article_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract article metadata from HTML.
        """
        self.logger.info("Extracting article metadata")
        
        metadata = {
            'title': '',
            'author': '',
            'date': '',
            'description': ''
        }

        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.text.strip()

        # Extract author
        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag:
            metadata['author'] = author_tag.get('content', '').strip()

        # Extract date
        date_tag = soup.find('meta', attrs={'property': 'article:published_time'})
        if date_tag:
            date_str = date_tag.get('content', '')
            try:
                parsed_date = parser.parse(date_str)
                metadata['date'] = parsed_date.isoformat()
            except ValueError:
                self.logger.warning(f"Could not parse date: {date_str}")

        # Extract description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata['description'] = desc_tag.get('content', '').strip()

        self.logger.info("Metadata extraction completed")
        return metadata

    def scrape_article(self, url: str = None, raw_content: str = None) -> Optional[Dict[str, str]]:
        """
        Main scraping function that retrieves and processes article content and metadata.
        """
        self.logger.info(f"Starting article scraping{' for URL: ' + url if url else ''}")
        
        try:
            if url:
                html_content = self.fetch_webpage(url)
            elif raw_content:
                html_content = raw_content
            else:
                raise ValueError("Either URL or HTML content must be provided")

            if not html_content:
                return None

            soup = BeautifulSoup(html_content, 'html.parser')
            metadata = self.extract_article_metadata(soup)
            
            main_content = self.extract_content(html_content)
            if not main_content:
                return None

            processed_text = self.process_text(main_content)
            if not processed_text:
                return None

            result = {
                'url': url,
                'content': processed_text,
                **metadata
            }

            self._log_extraction_results(result)
            return result

        except Exception as e:
            self.logger.error(f"Scraping failed: {str(e)}")
            return None

    def _calculate_backoff(self, attempt: int) -> int:
        """
        Calculate exponential backoff delay with jitter for retry attempts.
        """
        base_delay = self.config['retry_delay']
        max_delay = 60  # Maximum delay of 1 minute
        jitter_factor = 0.25  # ±25% randomization
        
        delay = base_delay * (2 ** attempt)
        jitter_range = delay * jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)
        
        final_delay = min(delay + jitter, max_delay)
        return max(int(final_delay), 1)  # Ensure at least 1 second

    def _log_extraction_results(self, result: Dict[str, str]) -> None:
        """Log the results of content extraction."""
        self.logger.info("Successfully scraped article:")
        self.logger.info(f"Title: {result.get('title', 'N/A')}")
        self.logger.info(f"Author: {result.get('author', 'N/A')}")
        self.logger.info(f"Date: {result.get('date', 'N/A')}")
        self.logger.info(f"Content length: {len(result.get('content', ''))} characters")

    def __del__(self):
        """Cleanup resources when the scraper is destroyed."""
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except Exception as e:
            self.logger.error(f"Error cleaning up session: {str(e)}")

# Example usage
def main():
    """
    Test function that demonstrates the WebScraper functionality using both
    URL and local HTML file inputs.
    """
    logger = setup_logger("test_web_scraper")

    logger.info("\nTesting URL file scraping...")
    
    scraper = WebScraper()
        
    # Test with URL
    test_url = "https://example.com"
    logger.info("Testing URL scraping...")
    url_result = scraper.scrape_article(url=test_url)
    
    if url_result:
        logger.info("Successfully scraped article from URL:")
        logger.info(f"Title: {url_result.get('title', 'N/A')}")
        logger.info(f"Author: {url_result.get('author', 'N/A')}")
        logger.info(f"Date: {url_result.get('date', 'N/A')}")
        logger.info(f"Description: {url_result.get('description', 'N/A')}")
        logger.info(f"Content length: {len(url_result['content'])} characters")
        logger.info(f"Content preview: {url_result.get('content', 'N/A')[:500]}...")
    else:
        logger.error("Failed to scrape article from URL")

    # Test with local HTML file    
    logger.info("\nTesting HTML file scraping...")
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_file_path = os.path.join(current_dir, "test_data.html")

        with open(test_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        file_result = scraper.scrape_article(raw_content=html_content)
        
        if file_result:
            logger.info("Successfully scraped article from HTML file:")
            logger.info(f"Title: {file_result.get('title', 'N/A')}")
            logger.info(f"Author: {file_result.get('author', 'N/A')}")
            logger.info(f"Date: {file_result.get('date', 'N/A')}")
            logger.info(f"Description: {file_result.get('description', 'N/A')}")
            logger.info(f"Content length: {len(file_result['content'])} characters")
            logger.info(f"Content preview: {file_result.get('content', 'N/A')[:500]}...")
        else:
            logger.error("Failed to scrape article from HTML file")
            
    except FileNotFoundError:
        logger.error(f"Test file not found: {test_file_path}")
    except Exception as e:
        logger.error(f"Error testing HTML file scraping: {str(e)}")

if __name__ == "__main__":
    main()