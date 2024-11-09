# test_text_to_speech.py
import unittest
import io
from pydub import AudioSegment
from modules.text_to_speech_service import text_to_speech
from modules.web_scraper import WebScraper
from modules.db_manager import (
    save_article, 
    get_audio_file_by_article_id, 
    get_last_article_id, 
    delete_article_by_id, 
    delete_audio_file
)
from modules.config import ARTICLE_CLEAN_PROMPT, ARTICLE_IMPROVE_READABILITY_PROMPT
from modules.google_api_interface import ContentGenerator
from modules.common_logger import setup_logger

logger = setup_logger("test_text_to_speech")

class TestTextToSpeech(unittest.TestCase):
    def setUp(self):
        self.scraper = WebScraper()
        self.test_url = "https://en.wikipedia.org/wiki/Miss_Meyers"
        self.content_generator = ContentGenerator()
        self.test_article_id = None

    def tearDown(self):
        if self.test_article_id:
            try:
                delete_audio_file(self.test_article_id)
                logger.info(f"Audio file for test article {self.test_article_id} deleted.")
            except Exception as e:
                logger.warning(f"Failed to delete audio file for test article {self.test_article_id}: {e}")

            try:
                delete_article_by_id(self.test_article_id)
                logger.info(f"Test article {self.test_article_id} deleted.")
            except Exception as e:
                logger.warning(f"Failed to delete test article {self.test_article_id}: {e}")

            self.test_article_id = None

    def test_text_to_speech_integration(self):
        # Step 1: Scrape the article
        scraped_article = self.scraper.scrape_article(url=self.test_url)
        self.assertIsNotNone(scraped_article, "Failed to scrape the article")

        full_prompt = ARTICLE_CLEAN_PROMPT.format(article_text=scraped_article['content'])        
        llm_response = self.content_generator.generate_content(full_prompt)
        full_prompt = ARTICLE_IMPROVE_READABILITY_PROMPT.format(article_text=llm_response)        
        llm_response = self.content_generator.generate_content(full_prompt)

        # Step 2: Save the article to the database
        article_save_success = save_article(
            content=llm_response,
            title=scraped_article['title'],
            author=scraped_article.get('author', ''),
            date=scraped_article.get('date', ''),
            description=scraped_article.get('description', ''),
            url=self.test_url
        )
        self.test_article_id = get_last_article_id()
        self.assertIsNotNone(self.test_article_id, "Failed to save the article to the database")

        # Step 3: Convert text to speech
        result = text_to_speech(self.test_article_id)
        self.assertTrue(result, "Text-to-speech conversion failed")

        # Step 4: Verify the audio file was created
        audio_content = get_audio_file_by_article_id(self.test_article_id)
        self.assertIsNotNone(audio_content, "Failed to retrieve the audio file")

        # Step 5: Validate the audio content
        audio = AudioSegment.from_file(audio_content, format="m4a") 
        self.assertGreater(len(audio), 0, "Audio file is empty")
        self.assertGreater(audio.duration_seconds, 1, "Audio duration is too short")

if __name__ == '__main__':
    unittest.main()