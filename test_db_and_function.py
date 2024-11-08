import os
import json
import base64
import wave
import struct
import math
from dotenv import load_dotenv
from modules.db_manager import (
    save_article, get_article_by_id, get_all_articles, get_last_article_id,
    update_article_by_id, delete_article_by_id, create_audio_file,
    get_audio_file_by_article_id, update_audio_file, delete_audio_file,
    get_audio_files_info
)
from local_function import app as local_function_app
from modules.common_logger import setup_logger

logger = setup_logger("test_harness")

# Load environment variables from .env file
load_dotenv()

def create_dummy_wav_file(filename, duration=1, freq=440):
    """Create a dummy WAV file for testing."""
    samplerate = 44100
    amplitude = 32767  # Max amplitude for 16-bit audio

    t = [i / samplerate for i in range(int(samplerate * duration))]
    samples = [int(amplitude * math.sin(2 * math.pi * freq * t)) for t in t]

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(samplerate)
        wav_file.writeframes(struct.pack('h' * len(samples), *samples))

def test_db_manager():
    logger.debug("\nTesting Article Database Functions:")

    # Test save_article
    article_save_success = save_article(
        content="Test content",
        title="Test Title",
        author="Test Author",
        date="2023-05-01",
        description="Test Description",
        url="http://test.com",
        source_type="url"
    )
    logger.debug(f"Article saved successfully: {article_save_success}")

    # Test get_last_article_id
    last_article_id = get_last_article_id()
    logger.debug(f"Last article ID: {last_article_id}")

    # Test get_article_by_id
    article = get_article_by_id(last_article_id)
    logger.debug(f"Retrieved article: {article}")

    # Test update_article_by_id
    update_success = update_article_by_id(
        last_article_id,
        content="Updated content",
        title="Updated Title",
        author="Updated Author",
        description="Updated Description"
    )
    logger.debug(f"Article update success: {update_success}")

    # Test get_all_articles
    all_articles = get_all_articles()
    logger.debug(f"Number of articles: {len(all_articles)}")
    
    # logger.debug article IDs
    logger.debug("Article IDs:")
    for article in all_articles:
        logger.debug(f"- {article.get('id', 'ID not found')}")

    # Test delete_article_by_id
    #delete_success = delete_article_by_id(last_article_id)
    #logger.debug(f"Article deletion success: {delete_success}")

    logger.info(f"Article database tests completed.")

def test_audio_functions():
    logger.debug("\nTesting Audio File Functions:")

    # Create a dummy article for audio testing
    save_article(content="Audio test content", title="Audio Test Article")
    article_id = get_last_article_id()

    # Create a dummy WAV file
    dummy_wav_file = "dummy_audio.wav"
    create_dummy_wav_file(dummy_wav_file)

    # Test create_audio_file
    with open(dummy_wav_file, 'rb') as audio_file:
        audio_content = audio_file.read()
    create_success = create_audio_file(article_id, audio_content)
    logger.debug(f"Audio file creation success: {create_success}")

    # Test get_audio_file_by_article_id
    retrieved_audio = get_audio_file_by_article_id(article_id)
    logger.debug(f"Audio file retrieved: {retrieved_audio is not None}")

    # Test update_audio_file
    update_success = update_audio_file(article_id, audio_content)
    logger.debug(f"Audio file update success: {update_success}")

    # Test get_audio_files_info
    audio_files_info = get_audio_files_info()
    logger.debug(f"Number of audio files: {len(audio_files_info)}")

    # Test delete_audio_file
    #delete_success = delete_audio_file(article_id)
    #logger.debug(f"Audio file deletion success: {delete_success}")

    # Clean up
    os.remove(dummy_wav_file)
    delete_article_by_id(article_id)

    logger.info("Audio file tests completed.")


if __name__ == "__main__":
    # logger.debug environment variables for verification
    logger.debug(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    logger.debug(f"FIRESTORE_EMULATOR_HOST: {os.getenv('FIRESTORE_EMULATOR_HOST')}")
    logger.debug(f"PUBSUB_EMULATOR_HOST: {os.getenv('PUBSUB_EMULATOR_HOST')}")
    logger.debug(f"GCS_BUCKET_NAME: {os.getenv('GCS_BUCKET_NAME')}")

    logger.debug("\nTesting db_manager...")
    test_db_manager()

    logger.debug("\nTesting audio functions...")
    test_audio_functions()