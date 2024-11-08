# modules/web_scraper.py


"""
Web Page Scraper
This Python module defines a WebScraper class designed for robust web scraping and content extraction. It utilizes libraries such as requests-html, BeautifulSoup, spacy, and trafilatura to perform tasks ranging from fetching webpages with retry logic and JS rendering fallbacks to parsing and cleaning HTML content. The WebScraper class integrates comprehensive configuration options for customizing request handling, including timeouts, retries, and content validation settings, making it adaptable to various scraping scenarios. Key features include the extraction of text content, metadata from HTML, and handling of both URL-based and direct HTML content input. This module also includes detailed logging throughout the scraping process to facilitate debugging and optimization. Example usage is provided to demonstrate the functionalities of the WebScraper class in practical scenarios.
"""



# Standard library imports
import os
import re
import time
import random
from typing import Optional, Dict, Any, Generator
from urllib.parse import urlparse
from dateutil import parser
from modules.config import initialize_nlp

# Third-party imports
import spacy
from bs4 import BeautifulSoup
from requests_html import HTMLSession
import trafilatura
import json

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Local imports
from modules.common_logger import setup_logger
#from modules.config import NLP

class WebScraper:
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the WebScraper with configuration options."""
        self.logger = setup_logger("web_scraper")
        
        default_config = {
            # Existing settings
            'timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 2,
            'render_timeout': 30,
            'headless': True,
            'verify_ssl': True,
            
            # Add text processing settings
            'min_sentence_chars': 10,
            'max_sentence_chars': 1000,
            'min_sentence_words': 2,
            'max_sentence_words': 200,
            'max_chunk_size': 100000,
            'min_input_length': 100,
            'max_input_length': 1000000,
            'min_processed_length': 100,
            'max_processed_length': 500000
        }
        
        # Update configuration with user-provided settings
        self.config = {**default_config, **(config or {})}
        

        # Initialize spaCy NLP model
        try:
            self.nlp = initialize_nlp()
        except Exception as e:
            self.logger.error(f"Failed to initialize NLP model: {str(e)}")
            raise

        # Initialize session with retry strategy
        retry_strategy = Retry(
            total=self.config['retry_attempts'],
            backoff_factor=self.config['retry_delay'],
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_redirect=True,
            raise_on_status=True
        )
        
        # Configure session with additional settings
        self.session = HTMLSession()
        self.session.verify = True  # Enable SSL verification
        
        # Configure timeout for different operations
        self.session.timeout = (
            self.config.get('connect_timeout', 5),  # Connection timeout
            self.config.get('read_timeout', 30)     # Read timeout
        )
        
        # Set up connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    
    def _get_random_user_agent(self) -> str:
        """Return a random user agent string."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        return random.choice(user_agents)

    
    def requests_html_with_js(self, url: str) -> Optional[str]:
        """
        Fetch webpage using requests-HTML with a simplified synchronous approach.
        """
        self.logger.info("Attempting requests-HTML fetch for: %s", url)
        
        try:
            # Create a new session for this request
            session = HTMLSession()
            
            headers = {'User-Agent': self._get_random_user_agent()}
            response = session.get(
                url,
                timeout=self.config['timeout'],
                headers=headers,
                verify=True
            )
            
            if response.status_code != 200:
                self.logger.warning(
                    "Failed to fetch URL. Status code: %d, URL: %s",
                    response.status_code, url
                )
                return None

            # Get the HTML content without JavaScript rendering
            html_content = response.html.raw_html.decode()
            
            # Attempt to extract any necessary dynamic content using basic selectors
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Clean up
            session.close()
            
            if not self._is_valid_content(html_content):
                return None
                
            self.logger.info("Successfully retrieved content")
            return html_content
            
        except Exception as e:
            self.logger.warning(
                "Fetch failed for %s: %s",
                url, str(e)
            )
            return None



    def fetch_webpage(self, url: str) -> Optional[str]:
        """
        Fetch webpage content with retry mechanism.
        Args:
            url (str): The URL to fetch
        Returns:
            Optional[str]: HTML content if successfully retrieved, None otherwise
        """
        self.logger.info("Fetching webpage: %s", url)
        
        for attempt in range(self.config['retry_attempts']):
            self.logger.info("Attempt %d of %d", attempt + 1, self.config['retry_attempts'])
            
            try:
                headers = {'User-Agent': self._get_random_user_agent()}
                response = self.session.get(url, timeout=self.config['timeout'], headers=headers)
                
                if response.status_code == 200:
                    content = response.html.html
                    if self._is_valid_content(content):
                        self.logger.info("Successfully retrieved content")
                        return content
                    
                self.logger.warning(f"Failed to fetch URL. Status code: {response.status_code}")
                    
            except Exception as e:
                self.logger.warning(f"Fetch failed: {str(e)}")
            
            if attempt < self.config['retry_attempts'] - 1:
                wait_time = self._calculate_backoff(attempt)
                self.logger.info("Retrying after %d seconds...", wait_time)
                time.sleep(wait_time)
        
        self.logger.error("Failed to retrieve content after all attempts")
        return None

    def _fetch_with_fallback(self, url: str) -> Optional[str]:
        """
        Attempt to fetch content with JS rendering fallback.
        """
        # Try with JS rendering first
        content = self.requests_html_with_js(url)
        
        # Fallback to simple fetch if JS rendering fails
        if not content:
            self.logger.info("JS rendering failed, falling back to simple fetch")
            content = self.fetch_webpage(url)
        
        return content

    def _is_valid_content(self, content: Optional[str]) -> bool:
        """
        Validate if the retrieved content is proper HTML and has sufficient content.

        Args:
            content: The HTML content to validate

        Returns:
            bool: True if content is valid, False otherwise
        """
        if not content:
            return False
            
        # Check for basic HTML structure
        if not ('<html' in content and '</html>' in content):
            return False
            
        # Check for minimum content length (arbitrary but configurable)
        min_length = self.config.get('min_content_length', 1000)
        if len(content) < min_length:
            return False
            
        return True

    
    def extract_content(self, html_content: str) -> Optional[str]:
        """
        Extract content using multiple methods and select the best result.
        Returns the extracted content with the largest length.
        """
        self.logger.info("Extracting content using trafilatura")

        try:
            extracted_text = trafilatura.extract(html_content)
            if not extracted_text:
                self.logger.error("No content could be extracted")
                return None
                
            self.logger.info("Successfully extracted content with length: %d", len(extracted_text))
            return extracted_text
            
        except Exception as e:
            self.logger.error("Trafilatura extraction failed: %s", str(e))
            return None
    



    def process_text(self, text: str) -> Optional[str]:
        """
        Process and clean text while preserving all sentences and structure.
        
        Args:
            text (str): Raw text to process
        Returns:
            Optional[str]: Processed text if successful, None otherwise
        """
        
        try:
            self.logger.info(f"Processing text of length: {len(text)} characters")
            
            # Split text into paragraphs while preserving empty lines
            paragraphs = text.split('\n')
            processed_paragraphs = []
            current_paragraph = []
            
            for line in paragraphs:
                # Handle empty lines as paragraph separators
                if not line.strip():
                    if current_paragraph:
                        processed_text = ' '.join(current_paragraph)
                        if processed_text:
                            processed_paragraphs.append(processed_text)
                        current_paragraph = []
                    processed_paragraphs.append('')  # Preserve empty lines
                    continue
                    
                # Process the current line
                processed_line = self._process_line(line.strip())
                if processed_line:
                    current_paragraph.append(processed_line)
            
            # Handle any remaining paragraph
            if current_paragraph:
                processed_text = ' '.join(current_paragraph)
                if processed_text:
                    processed_paragraphs.append(processed_text)
            
            # Join paragraphs with newlines, preserving structure
            final_text = '\n'.join(
                para if para else '' 
                for para in processed_paragraphs
            )
            
            # Remove consecutive empty lines while preserving structure
            final_text = re.sub(r'\n{3,}', '\n\n', final_text)
            
            self.logger.info(f"Successfully processed text: {len(final_text)} characters")
            return final_text
            
        except Exception as e:
            self.logger.error(f"Error processing text: {str(e)}", exc_info=True)
            return None

    def _process_line(self, line: str) -> Optional[str]:
        """
        Process a single line of text while preserving all content.
        
        Args:
            line (str): Line to process
        Returns:
            Optional[str]: Processed line if valid, None otherwise
        """
        if not line:
            return None
            
        try:
            # Process text in smaller chunks if needed
            chunk_size = self.config.get('max_chunk_size', 100000)
            processed_chunks = []
            
            for chunk in self._chunk_text(line, chunk_size):
                doc = self.nlp(chunk)
                
                # Preserve all sentences while maintaining quotes and structure
                for sent in doc.sents:
                    sent_text = sent.text.strip()
                    if sent_text:
                        processed_chunks.append(sent_text)
            
            return ' '.join(processed_chunks) if processed_chunks else None
            
        except Exception as e:
            self.logger.warning(f"Error processing line: {str(e)}")
            return line  # Return original line if processing fails
        

    def _is_valid_sentence_lenient(self, sentence) -> bool:
        """
        Simplified sentence validation that preserves most content.
        
        Args:
            sentence: spaCy Span object representing a sentence
        Returns:
            bool: True if sentence should be kept, False otherwise
        """
        text = sentence.text.strip()
        
        # Only filter out completely empty sentences
        if not text:
            return False
            
        # Keep sentences with actual content
        has_content = any(not token.is_space for token in sentence)
        
        return has_content

    def _chunk_text(self, text: str, chunk_size: int) -> Generator[str, None, None]:
        """
        Split text into manageable chunks for processing.
        
        Args:
            text (str): Text to chunk
            chunk_size (int): Maximum size of each chunk

        Yields:
            str: Text chunks
        """
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            
            if end < text_length:
                # Try to find a sentence boundary
                while end < text_length and text[end] not in '.!?\n':
                    end += 1
                end += 1  # Include the sentence boundary
            
            yield text[start:end]
            start = end
        





    def extract_article_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract article metadata from HTML using a comprehensive set of selectors.
        
        Args:
            soup: BeautifulSoup object of the HTML content
            
        Returns:
            Dictionary containing metadata (title, author, date, description)
        """
        self.logger.info("Extracting article metadata")
        
        # Define metadata selectors with priority ordering
        METADATA_SELECTORS = {
            'title': [
                {'type': 'meta', 'attrs': {'property': 'og:title'}},
                {'type': 'meta', 'attrs': {'name': 'twitter:title'}},
                {'type': 'meta', 'attrs': {'property': 'article:title'}},
                {'type': 'json-ld', 'key': 'headline'},
                {'type': 'h1'},
                {'type': 'title'},
                {'type': 'meta', 'attrs': {'name': 'title'}}
            ],
            'author': [
                {'type': 'meta', 'attrs': {'name': 'author'}},
                {'type': 'meta', 'attrs': {'property': 'article:author'}},
                {'type': 'meta', 'attrs': {'property': 'og:article:author'}},
                {'type': 'json-ld', 'key': 'author.name'},
                {'type': 'a', 'attrs': {'class': re.compile(r'author|byline', re.I)}},
                {'type': 'span', 'attrs': {'class': re.compile(r'author|byline', re.I)}},
                {'type': 'meta', 'attrs': {'name': 'twitter:creator'}}
            ],
            'date': [
                {'type': 'meta', 'attrs': {'property': 'article:published_time'}},
                {'type': 'meta', 'attrs': {'property': 'og:article:published_time'}},
                {'type': 'meta', 'attrs': {'name': 'publication_date'}},
                {'type': 'meta', 'attrs': {'name': 'pubdate'}},
                {'type': 'json-ld', 'key': 'datePublished'},
                {'type': 'time', 'attrs': {'datetime': True}},
                {'type': 'time', 'attrs': {'class': re.compile(r'date|published|posted', re.I)}}
            ],
            'description': [
                {'type': 'meta', 'attrs': {'property': 'og:description'}},
                {'type': 'meta', 'attrs': {'name': 'description'}},
                {'type': 'meta', 'attrs': {'name': 'twitter:description'}},
                {'type': 'json-ld', 'key': 'description'},
                {'type': 'meta', 'attrs': {'property': 'article:description'}}
            ]
        }

        def extract_json_ld(soup) -> Dict:
            """Extract JSON-LD data from script tags."""
            try:
                
                json_ld = {}
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            data = data[0]
                        json_ld.update(data)
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue
                return json_ld
            except Exception as e:
                self.logger.warning(f"JSON-LD extraction failed: {str(e)}")
                return {}

        def get_nested_dict_value(d: Dict, key: str) -> Optional[str]:
            """Get nested dictionary value using dot notation."""
            keys = key.split('.')
            for k in keys:
                if isinstance(d, dict):
                    d = d.get(k, {})
                else:
                    return None
            return d if isinstance(d, str) else None

        metadata = {key: '' for key in METADATA_SELECTORS.keys()}
        json_ld_data = extract_json_ld(soup)

        try:
            for field, selectors in METADATA_SELECTORS.items():
                for selector in selectors:
                    selector_type = selector['type']
                    
                    if selector_type == 'json-ld':
                        value = get_nested_dict_value(json_ld_data, selector['key'])
                        if value:
                            metadata[field] = value.strip()
                            self.logger.info(f"{field.title()} extracted from JSON-LD")
                            break

                    elif selector_type in ['meta', 'time', 'a', 'span', 'h1', 'title']:
                        attrs = selector.get('attrs', {})
                        element = soup.find(selector_type, attrs=attrs)
                        
                        if element:
                            if selector_type == 'meta':
                                value = element.get('content')
                            elif 'datetime' in attrs:
                                value = element.get('datetime')
                            else:
                                value = element.text
                                
                            if value:
                                metadata[field] = value.strip()
                                self.logger.info(f"{field.title()} extracted from {selector_type}")
                                break

            # Post-process date format if needed
            if metadata['date']:
                try:                    
                    parsed_date = parser.parse(metadata['date'])
                    metadata['date'] = parsed_date.isoformat()
                except Exception as e:
                    self.logger.warning(f"Date parsing failed: {str(e)}")

            self.logger.info("Metadata extraction completed")
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata: {str(e)}")
        
        return metadata


    def scrape_article(self, url: str = None, raw_content: str = None) -> Optional[Dict[str, str]]:
        """
        Main scraping function that retrieves and processes article content and metadata.
        
        Args:
            url (str, optional): The URL to scrape
            raw_content (str, optional): Raw HTML content to process
            
        Returns:
            Optional[Dict[str, str]]: Dictionary containing:
                - url: Original URL (if provided)
                - content: Processed text content
                - title: Article title
                - author: Article author
                - date: Publication date
                - description: Article description
                
        Note:
            Either URL or raw_content must be provided. If both are provided,
            URL is used for logging but raw_content is processed directly.
        """
        self.logger.info("Starting article scraping%s", f" for URL: {url}" if url else "")
        
        try:
            # Input validation
            if not url and not raw_content:
                raise ValueError("Either URL or HTML content must be provided")
                
            # Handle direct HTML content
            if raw_content:
                return self._process_content(raw_content, url)
                
            # Handle URL-based scraping
            return self._process_url_content(url)
                
        except Exception as e:
            self.logger.error("Scraping failed: %s", str(e))
            return None

    def _process_content(self, raw_content: str, url: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Process provided content (HTML or plain text) and extract article information.
        
        Args:
            raw_content: Raw content (HTML or plain text) to process
            url: Optional URL for reference
            
        Returns:
            Optional[Dict[str, str]]: Processed article data
        """
        try:
            # Determine if the content is HTML
            if '<' in raw_content and '>' in raw_content:  # Basic check for HTML tags
                # Parse HTML
                soup = BeautifulSoup(raw_content, 'html.parser')
                
                # Extract metadata from the soup
                metadata = self.extract_article_metadata(soup)
                
                # Extract main content from soup if it's HTML
                main_content = self.extract_content(raw_content)
            else:
                # Treat raw_content as plain text
                main_content = raw_content
                metadata = {}  # No metadata to extract from plain text
            
            # Handle case where main_content is not properly extracted
            if not main_content:
                self.logger.error("Failed to extract main content")
                return None
                    
            # Process extracted text
            processed_text = self.process_text(main_content)
            if not processed_text:
                self.logger.error("Failed to process extracted text")
                return None
                    
            result = {
                'url': url,
                'content': processed_text,
                **metadata
            }
            
            self._log_extraction_results(result)
            return result
                
        except Exception as e:
            self.logger.error("Content processing failed: %s", str(e))
            return None

    def _process_url_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fetch and process content from URL with retry mechanism.
        
        Args:
            url: URL to scrape
            
        Returns:
            Optional[Dict[str, str]]: Processed article data
        """
        # Validate URL
        if not self._is_valid_url(url):
            return None
            
        max_retries = self.config['retry_attempts']
        
        for retry in range(max_retries):
            try:
                # Try to fetch content
                html_content = self._fetch_with_fallback(url)
                
                if not html_content:
                    raise Exception("Failed to retrieve HTML content")
                    
                return self._process_content(html_content, url)
                
            except Exception as e:
                self.logger.error("Attempt %d/%d failed: %s", 
                                retry + 1, max_retries, str(e))
                
                if retry < max_retries - 1:
                    wait_time = self._calculate_backoff(retry)
                    self.logger.info("Retrying after %d seconds...", wait_time)
                    time.sleep(wait_time)
                else:
                    self.logger.error("All retry attempts failed")
                    return None

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            parsed_url = urlparse(url)
            return all([parsed_url.scheme, parsed_url.netloc])
        except Exception as e:
            self.logger.error("Invalid URL format: %s", str(e))
            return False

    def _calculate_backoff(self, attempt: int) -> int:
        """
        Calculate exponential backoff delay with jitter for retry attempts.
        """
        # Get configuration values with defaults
        base_delay = self.config['retry_delay']
        max_delay = self.config.get('max_retry_delay', 60)
        jitter_factor = 0.25  # ±25% randomization
        
        # Calculate exponential backoff
        delay = base_delay * (2 ** attempt)
        
        # Add jitter to prevent thundering herd
        jitter_range = delay * jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)
        
        # Apply jitter and ensure within bounds
        final_delay = min(delay + jitter, max_delay)
        
        return max(int(final_delay), 1)  # Ensure at least 1 second
    

    def _log_extraction_results(self, result: Dict[str, str]) -> None:
        """Log the results of content extraction."""
        self.logger.info("Successfully scraped article:")
        self.logger.info("Title: %s", result.get('title', 'N/A'))
        self.logger.info("Author: %s", result.get('author', 'N/A'))
        self.logger.info("Date: %s", result.get('date', 'N/A'))
        self.logger.info("Content length: %d characters", 
                        len(result.get('content', '')))


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
    test_url = "https://bigthink.com/the-past/a-new-spin-on-the-stoned-ape-hypothesis/"
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
