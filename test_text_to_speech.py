# test_text_to_speech.py

import unittest
from modules.text_to_speech_service import text_to_speech
from modules.web_scraper import WebScraper
from modules.db_manager import save_article, get_audio_file_by_article_id, get_last_article_id
import io
from pydub import AudioSegment
from modules.config import MODEL_NAME_FLASH, ARTICLE_CLEAN_PROMPT, ARTICLE_IMPROVE_READABILITY_PROMPT
from modules.google_api_interface import ContentGenerator

class TestTextToSpeech(unittest.TestCase):
    def setUp(self):
        self.scraper = WebScraper()
        self.test_url = "https://en.wikipedia.org/wiki/Miss_Meyers"
        self.content_generator = ContentGenerator()

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
        article_id = get_last_article_id()
        self.assertIsNotNone(article_id, "Failed to save the article to the database")

        # Step 3: Convert text to speech
        result = text_to_speech(article_id)
        self.assertTrue(result, "Text-to-speech conversion failed")

        # Step 4: Verify the audio file was created
        audio_content = get_audio_file_by_article_id(article_id)
        self.assertIsNotNone(audio_content, "Failed to retrieve the audio file")

        # Step 5: Validate the audio content
        audio = AudioSegment.from_wav(io.BytesIO(audio_content))
        self.assertGreater(len(audio), 0, "Audio file is empty")
        self.assertGreater(audio.duration_seconds, 1, "Audio duration is too short")

if __name__ == '__main__':
    unittest.main()