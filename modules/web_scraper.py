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
from typing import Optional, Tuple

# Third-party imports
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import spacy

# Local imports
from modules.common_logger import setup_logger
from modules.config import initialize_nlp
import threading
from functools import lru_cache

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
            'max_sentence_length': 300,
            'max_content_length': 5000000,  # 5MB
        }
        
        # Update configuration with user-provided settings
        self.config = {**default_config, **(config or {})}
        self.cloud_run_url = "https://scrape-webpage-1098359986679.us-south1.run.app" 


        self.nlp_local = threading.local()

        # Initialize session
        self.session = None

    @lru_cache(maxsize=None)
    def get_nlp(self):
        if not hasattr(self.nlp_local, 'nlp'):
            try:
                self.nlp_local.nlp = initialize_nlp()
            except Exception as e:
                self.logger.error(f"Failed to initialize NLP model: {str(e)}")
                raise
        return self.nlp_local.nlp
    
    async def __aenter__(self):
        await self.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
        
    async def create_session(self):
        if self.session is None:
            connector = aiohttp.TCPConnector(verify_ssl=self.config['verify_ssl'])
            self.session = aiohttp.ClientSession(connector=connector)

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    def _get_random_user_agent(self) -> str:
        """Return a random user agent string."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        return random.choice(user_agents)


    async def fetch_webpage(self, url: str) -> Optional[str]:
        """
        Fetch webpage content with retry mechanism, using both local method and Cloud Run service.
        Args:
            url (str): The URL to fetch
        Returns:
            Optional[Tuple[str, str]]: Tuple of (HTML content, source) if successfully retrieved, None otherwise
        """
        self.logger.info(f"Fetching webpage: {url}")
        
        await self.create_session()

        local_content = await self._fetch_local(url)
        cloud_run_content = await self._fetch_cloud_run(url)
        
        if local_content and cloud_run_content:
            if len(local_content) >= len(cloud_run_content):
                return local_content
            else:
                return cloud_run_content
        elif local_content:
            return local_content
        elif cloud_run_content:
            return cloud_run_content
        
        self.logger.error("Failed to retrieve content from both local and Cloud Run methods")
        return None

    async def _fetch_local(self, url: str) -> Optional[str]:
        for attempt in range(self.config['retry_attempts']):
            self.logger.info(f"Local attempt {attempt + 1} of {self.config['retry_attempts']}")
            
            try:
                headers = {'User-Agent': self._get_random_user_agent()}
                async with self.session.get(url, timeout=self.config['timeout'], headers=headers) as response:
                    response.raise_for_status()
                    content = await response.text()
                    if self._is_valid_content(content):
                        self.logger.info("Successfully retrieved content locally")
                        return content
                    
                    self.logger.warning("Retrieved local content is not valid")
                    
            except aiohttp.ClientError as e:
                self.logger.warning(f"Local fetch failed: {str(e)}")
            
            if attempt < self.config['retry_attempts'] - 1:
                wait_time = self._calculate_backoff(attempt)
                self.logger.info(f"Retrying local fetch after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        self.logger.error("Failed to retrieve content locally after all attempts")
        return None
    

    async def _fetch_cloud_run(self, url: str) -> Optional[str]:
        for attempt in range(self.config['retry_attempts']):
            self.logger.info(f"Cloud Run attempt {attempt + 1} of {self.config['retry_attempts']}")
            
            try:
                params = {'url': url}
                async with self.session.get(self.cloud_run_url, params=params, timeout=self.config['timeout']) as response:
                    response.raise_for_status()
                    result = await response.json()
                    if result['status'] == 'success':
                        content = result['content']
                        if self._is_valid_content(content):
                            self.logger.info("Successfully retrieved content from Cloud Run")
                            return content
                        
                        self.logger.warning("Retrieved Cloud Run content is not valid")
                    else:
                        self.logger.warning(f"Cloud Run fetch failed: {result.get('error', 'Unknown error')}")
                        
            except asyncio.TimeoutError:
                self.logger.warning(f"Cloud Run fetch timed out after {self.config['timeout']} seconds")
            except aiohttp.ClientError as e:
                self.logger.warning(f"Cloud Run fetch failed: {str(e)}")
            except Exception as e:
                self.logger.error(f"Unexpected error during Cloud Run fetch: {str(e)}", exc_info=True)
            
            if attempt < self.config['retry_attempts'] - 1:
                wait_time = self._calculate_backoff(attempt)
                self.logger.info(f"Retrying Cloud Run fetch after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        self.logger.error("Failed to retrieve content from Cloud Run after all attempts")
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

    async def extract_content(self, html_content: str) -> Optional[str]:
        """
        Extract main content from HTML.
        """
        self.logger.info("Extracting content")
        try:
            loop = asyncio.get_running_loop()
            soup = await loop.run_in_executor(None, lambda: BeautifulSoup(html_content, 'html.parser'))
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = await loop.run_in_executor(None, soup.get_text)
            
            # Process text (this can be CPU-intensive, so we run it in an executor)
            processed_text = await self.process_text(text)
            
            self.logger.info(f"Successfully extracted content with length: {len(processed_text)}")
            return processed_text
            
        except Exception as e:
            self.logger.error(f"Content extraction failed: {str(e)}", exc_info=True)
            return None

    async def process_text(self, text: str) -> Optional[str]:
        """
        Process and clean text while preserving all sentences and structure.
        """
        try:
            self.logger.info(f"Processing text of length: {len(text)} characters")
            
            loop = asyncio.get_running_loop()
            nlp = self.get_nlp()

            # Split text into paragraphs while preserving empty lines
            paragraphs = text.split('\n')
            processed_paragraphs = []

            for paragraph in paragraphs:
                if paragraph.strip():
                    doc = await loop.run_in_executor(None, nlp, paragraph)
                    processed_sentences = await asyncio.gather(*[
                        loop.run_in_executor(None, self.split_long_sentences, sent.text.strip())
                        for sent in doc.sents if sent.text.strip()
                    ])
                    processed_paragraphs.append(' '.join(processed_sentences))
                else:
                    processed_paragraphs.append('')
            
            # Join paragraphs with newlines, preserving structure
            final_text = '\n'.join(processed_paragraphs)
            
            # Remove consecutive empty lines while preserving structure
            final_text = re.sub(r'\n{3,}', '\n\n', final_text)
            
            self.logger.info(f"Successfully processed text: {len(final_text)} characters. "
                 f"Preview: {final_text[:100]}...{final_text[-100:]}")
            return final_text
            
        except Exception as e:
            self.logger.error(f"Error processing text: {str(e)}", exc_info=True)
            return None

    def split_long_sentences(self, text: str) -> str:
        max_length = self.config['max_sentence_length']
        nlp = self.get_nlp()
        doc = nlp(text)
        split_sentences = []
        for sent in doc.sents:
            if len(sent.text) > max_length:
                # Split long sentence at logical points (e.g., commas, conjunctions)
                sub_sentences = re.split(r'[,;]|\sand\s|\sbut\s', sent.text)
                split_sentences.extend([s.strip() for s in sub_sentences if s.strip()])
            else:
                split_sentences.append(sent.text.strip())
        return ' '.join(split_sentences)


    async def extract_article_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
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
        
        loop = asyncio.get_running_loop()
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = await loop.run_in_executor(None, lambda: title_tag.text.strip())
        
        # Extract author
        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag:
            metadata['author'] = author_tag.get('content', '').strip()
        
        # Extract date
        date_tag = soup.find('meta', attrs={'property': 'article:published_time'})
        if date_tag:
            date_str = date_tag.get('content', '')
            try:
                parsed_date = await loop.run_in_executor(None, parser.parse, date_str)
                metadata['date'] = parsed_date.isoformat()
            except ValueError:
                self.logger.warning(f"Could not parse date: {date_str}")
        
        # Extract description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata['description'] = desc_tag.get('content', '').strip()
        
        self.logger.info("Metadata extraction completed")
        return metadata

    async def scrape_article(self, url: str = None, raw_content: str = None) -> Optional[Dict[str, str]]:
        self.logger.info(f"Starting article scraping{' for URL: ' + url if url else ''}")
        
        try:
            if url:
                html_content = await self.fetch_webpage(url)
            elif raw_content:
                html_content = raw_content
            else:
                raise ValueError("Either URL or HTML content must be provided")
            
            if not html_content:
                self.logger.error("Failed to retrieve HTML content")
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            metadata = await self.extract_article_metadata(soup)
            
            main_content = await self.extract_content(html_content)
            if not main_content:
                self.logger.error("Failed to extract main content")
                return None
            
            processed_text = await self.process_text(main_content)
            if not processed_text:
                self.logger.error("Failed to process text")
                return None
            
            result = {
                'url': url,
                'content': processed_text,
                **metadata
            }
            self._log_extraction_results(result)
            return result
        except ValueError as e:
            self.logger.error(f"Invalid input: {str(e)}")
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during scraping: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during scraping: {str(e)}", exc_info=True)
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

    async def close(self):
        """Close the scraper and cleanup resources."""
        await self.close_session()