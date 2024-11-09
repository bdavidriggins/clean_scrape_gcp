"""
/home/bdavidriggins/Projects/voicescribe_TTS/text_to_speech_service.py
===========================================
Text-to-Speech Module using Google Cloud API
===========================================
"""
import os
os.environ['PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT'] = '5.0' 
import json
from datetime import datetime
from typing import Optional, List, Generator, Any, ContextManager
from google.oauth2 import service_account
from google.cloud import texttospeech
from google.api_core.exceptions import GoogleAPIError
from google.api_core import client_options as client_options_lib
from google.api_core import retry as retries
from google.api_core import exceptions
from google.cloud import storage
from modules.common_logger import setup_logger
from pydub import AudioSegment
import io
from contextlib import contextmanager
import time
import gc
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import subprocess
from io import BytesIO
import wave

from pydub import AudioSegment
import stat

# Constants for ffmpeg
FFMPEG_PATH = os.path.join(os.getcwd(), 'ffmpeg')
AudioSegment.converter = FFMPEG_PATH

# Ensure ffmpeg is executable
st = os.stat(FFMPEG_PATH)
#os.chmod(FFMPEG_PATH, st.st_mode | stat.S_IEXEC)


from modules.db_manager import (
    get_article_by_id, 
    create_audio_file
)


# ============================
# Logger Setup
# ============================
# Initialize the logger for the TextToSpeech module
logger = setup_logger("text_to_speech")

# ============================
# TextToSpeech Class
# ============================
class TextToSpeech:
    """
    A class to handle text-to-speech conversion using Google Cloud Text-to-Speech API.
    
    Attributes:
        LANGUAGE_CODE (str): The language code for the synthesized voice.
        VOICE_NAME (str): The name of the voice to use for synthesis.
        AUDIO_ENCODING (texttospeech.AudioEncoding): The audio encoding format.
        SPEAKING_RATE (float): The speaking rate for the synthesized voice.
        PROJECT_ID (str): Google Cloud project ID.
        LOCATION (str): The location of the Google Cloud service.
        credentials (service_account.Credentials): Credentials for authenticating with Google Cloud.
    """
    
    # ========================
    # Class Constants
    # ========================
    # LANGUAGE_CODE: str = "en-GB"
    # VOICE_NAME: str = "en-GB-Neural2-D"

    LANGUAGE_CODE: str = "en-GB"
    VOICE_NAME: str = "en-GB-Journey-D"

    AUDIO_ENCODING: texttospeech.AudioEncoding = texttospeech.AudioEncoding.LINEAR16  # "LINEAR16"
    SPEAKING_RATE: float = 0.75
    MIN_AUDIO_DURATION: float = 0.1  # minimum audio duration in seconds
    ERROR_THRESHOLD: float = 0.2
    PROGRESS_LOG_INTERVAL: int = 10
    MIN_FRAME_RATE: int = 16000
    MAX_FRAME_RATE: int = 48000

    # ========================
    # Fixed Variables
    # ========================
    PROJECT_ID: str = 'resewrch-agent'  # Replace with your GCP project ID
    LOCATION: str = 'us-central1'
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
        
    def __init__(self) -> None:
        """
        Initializes the TextToSpeech instance by loading service account credentials.
        
        Args:
        
        Raises:
            FileNotFoundError: If the service account JSON file does not exist.
            json.JSONDecodeError: If the JSON file is malformed.
            ValueError: If credentials cannot be created from the provided information.
        """
       
        gc.enable()

        self.storage_client = storage.Client()
        self.bucket_name = 'clean-scrape-temp-bucket'
        self.bucket = self.storage_client.bucket(self.bucket_name)


    def get_temp_gcs_path(self, filename: str) -> str:
        return f"tmp_audio_files/{filename}"
    
    
    
    def _validate_audio_segment(self, segment: AudioSegment) -> bool:
        """
        Validate audio segment properties to ensure quality and integrity.
        
        Args:
            segment (AudioSegment): The audio segment to validate
            
        Returns:
            bool: True if the segment meets all quality criteria, False otherwise
        """
        try:
            if segment.duration_seconds < self.MIN_AUDIO_DURATION:
                logger.warning(f"Audio segment too short: {segment.duration_seconds} seconds")
                return False
                
            if not (self.MIN_FRAME_RATE <= segment.frame_rate <= self.MAX_FRAME_RATE):
                logger.warning(f"Invalid frame rate: {segment.frame_rate}")
                return False
                
            if segment.channels not in [1, 2]:  # Mono or Stereo only
                logger.warning(f"Unsupported channel count: {segment.channels}")
                return False
                
            if segment.max_dBFS > 0:  # Check for audio clipping
                logger.warning("Audio contains clipping")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating audio segment: {e}", exc_info=True)
            return False
    
        
    def _make_tts_request(self, client: texttospeech.TextToSpeechClient, request: dict, timeout: float = 120.0) -> Optional[bytes]:
        """
        Make TTS API request with timeout monitoring.
        """
        start_time = time.time()
        try:
            logger.info(f"Starting TTS API request with {timeout}s timeout")
            
            # Add timeout context
            from concurrent.futures import ThreadPoolExecutor, TimeoutError
            with ThreadPoolExecutor() as executor:
                future = executor.submit(client.synthesize_speech, request=request, timeout=timeout)
                try:
                    response = future.result(timeout=timeout)
                    elapsed_time = time.time() - start_time
                    logger.info(f"TTS API request completed in {elapsed_time:.2f} seconds")
                    return response.audio_content
                except TimeoutError:
                    logger.error(f"TTS API request timed out after {timeout} seconds")
                    raise exceptions.DeadlineExceeded("Request timed out")
                    
        except exceptions.DeadlineExceeded:
            logger.error(f"TTS API request timed out after {time.time() - start_time:.2f} seconds")
            raise
        except Exception as e:
            logger.error(f"TTS API request failed after {time.time() - start_time:.2f} seconds: {str(e)}")
            raise
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
        retry=(retry_if_exception_type(
            (
                exceptions.DeadlineExceeded,
                exceptions.ServiceUnavailable,
                exceptions.InternalServerError,
                ConnectionError,
                socket.timeout,
                TimeoutError
            )
        )),
        before=lambda retry_state: logger.info(f"Attempt {retry_state.attempt_number} of 3"),
        after=lambda retry_state: logger.info(
            f"Attempt {retry_state.attempt_number} {'successful' if not retry_state.outcome.failed else 'failed'}"
        )
    )
    def convert_text_to_speech(self, text: str) -> Optional[bytes]:
        """Converts text to speech with enhanced error handling."""
        if not isinstance(text, str):
            logger.error("Input must be a string")
            return None

        text_bytes = text.encode('utf-8')
        if len(text_bytes) > 5000:
            logger.error("Text exceeds 5000 bytes limit")
            raise ValueError("Text exceeds maximum allowed size of 5000 bytes")

        logger.info("Starting single-chunk text-to-speech conversion")
        

        try:
            with self._get_client() as client:
                request = {
                    "input": texttospeech.SynthesisInput(text=text),
                    "voice": texttospeech.VoiceSelectionParams(
                        language_code=self.LANGUAGE_CODE,
                        name=self.VOICE_NAME
                    ),
                    "audio_config": texttospeech.AudioConfig(
                        audio_encoding=self.AUDIO_ENCODING
                    )
                }
                
                logger.info("Sending request to Google Cloud TTS API")
                start_time = time.time()
                
                try:
                    audio_content = self._make_tts_request(client, request)
                    if not audio_content:
                        logger.error("Received empty response from TTS API")
                        return None
                        
                    logger.info(f"Received audio content of size: {len(audio_content)} bytes")
                    
                    # Validate the audio content
                    with io.BytesIO(audio_content) as audio_buffer:
                        audio_segment = AudioSegment.from_wav(audio_buffer)
                        if not self._validate_audio_segment(audio_segment):
                            logger.error("Generated audio failed validation")
                            return None
                            
                    logger.info(f"Successfully converted text to speech in {time.time() - start_time:.2f} seconds")
                    return audio_content
                    
                except Exception as e:
                    logger.error(f"TTS conversion failed: {str(e)}", exc_info=True)
                    raise
                    
        except Exception as e:
            logger.error(f"Error in convert_text_to_speech: {str(e)}", exc_info=True)
            raise

       

    def _process_chunk(self, chunk: str, output_file: str, chunk_index: int, total_chunks: int) -> bool:
        try:
            audio_content = self.convert_text_to_speech(chunk)
            if audio_content is None:
                logger.error(f"Failed to convert chunk {chunk_index}/{total_chunks}")
                return False
            
            # Validate audio content
            with io.BytesIO(audio_content) as buffer:
                audio_segment = AudioSegment.from_wav(buffer)
                if not self._validate_audio_segment(audio_segment):
                    logger.error(f"Audio validation failed for chunk {chunk_index}/{total_chunks}")
                    return False
            
            # Write to Cloud Storage
            blob = self.bucket.blob(self.get_temp_gcs_path(output_file))
            with BytesIO(audio_content) as audio_file:
                blob.upload_from_file(
                    audio_file,
                    content_type='audio/wav',
                    rewind=True
                )
            
            logger.info(f"Successfully processed chunk {chunk_index}/{total_chunks}")
            return True
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_index}/{total_chunks}: {str(e)}")
            return False


    def process_large_text(self, text: str, chunk_size: int = 5000) -> Optional[bytes]:
        try:
            text_bytes = len(text.encode('utf-8'))
            logger.info(f"Starting process_large_text - Total text size: {text_bytes} bytes")
            
            with self.temporary_directory() as temp_prefix:
                chunks = self._chunk_text(text, chunk_size)
                total_chunks = len(chunks)
                chunk_files = []
                failed_chunks = 0
                
                for idx, chunk in enumerate(chunks, 1):
                    chunk_file = f"{temp_prefix}/chunk_{idx}.wav"
                    if self._process_chunk(chunk, chunk_file, idx, total_chunks):
                        chunk_files.append(chunk_file)
                    else:
                        failed_chunks += 1
                        if failed_chunks / total_chunks > self.ERROR_THRESHOLD:
                            raise Exception(f"Error threshold exceeded: {failed_chunks}/{total_chunks} chunks failed")
                
                if not chunk_files:
                    raise Exception("No valid audio chunks generated")
                
                final_audio = self._combine_audio_files(chunk_files)
                if final_audio is None:
                    raise Exception("Failed to combine audio files")
                    
                return final_audio
                
        except Exception as e:
            logger.error(f"Critical error in process_large_text: {str(e)}")
            return None

    def _combine_audio_files(self, file_paths: List[str]) -> Optional[bytes]:
        """Combines multiple audio files using Google Cloud Storage."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.bucket_name)
        combined_audio = BytesIO()
        
        try:
            # Open a wave writer for the combined audio
            with wave.open(combined_audio, 'wb') as outwave:
                for i, file_path in enumerate(file_paths):
                    blob = bucket.blob(self.get_temp_gcs_path(file_path))
                    if not blob.exists():
                        logger.error(f"Blob does not exist: {file_path}")
                        continue

                    # Download the audio file to memory
                    audio_data = BytesIO()
                    blob.download_to_file(audio_data)
                    audio_data.seek(0)

                    # Read the wave file
                    with wave.open(audio_data, 'rb') as inwave:
                        if i == 0:
                            # Set parameters for the output wave file
                            outwave.setnchannels(inwave.getnchannels())
                            outwave.setsampwidth(inwave.getsampwidth())
                            outwave.setframerate(inwave.getframerate())

                        # Write audio frames
                        outwave.writeframes(inwave.readframes(inwave.getnframes()))

            # Get the combined audio data
            combined_audio.seek(0)
            return combined_audio.getvalue()

        except Exception as e:
            logger.error(f"Error in _combine_audio_files: {str(e)}", exc_info=True)
            return None

        finally:
            # Clean up temporary files in GCS
            if file_paths:
                prefix = os.path.dirname(self.get_temp_gcs_path(file_paths[0])) + '/'
                blobs = bucket.list_blobs(prefix=prefix)
                for blob in blobs:
                    try:
                        blob.delete()
                        logger.debug(f"Deleted temporary file: {blob.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary file {blob.name}: {str(e)}")
                
                logger.info(f"Cleanup completed for prefix: {prefix}")



    @contextmanager
    def _manage_ffmpeg_process(self, process: subprocess.Popen):
        """Context manager for FFmpeg process management."""
        try:
            yield process
        finally:
            if process and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception as e:
                    logger.error(f"Error cleaning up FFmpeg process: {e}")




    def _cleanup_old_temp_files(self, max_age_hours: int = 24, prefix: str = 'tmp_audio_files/'):
        try:
            current_time = time.time()
            blobs = self.bucket.list_blobs(prefix=prefix)
            for blob in blobs:
                if (current_time - blob.time_created.timestamp()) > (max_age_hours * 3600):
                    blob.delete()
                    logger.debug(f"Removed old temporary file: {blob.name}")
        except Exception as e:
            logger.error(f"Error during cleanup of old temporary files: {e}")
    

    def cleanup(self):
        """Cleanup method to be called when done with the instance"""
        try:
            blobs = self.bucket.list_blobs(prefix='tmp_audio_files/')
            for blob in blobs:
                blob.delete()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

            
    @contextmanager
    def temporary_directory(self):
        prefix = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            logger.debug(f"Created temporary prefix in Cloud Storage: {prefix}")
            yield prefix
        finally:
            self._cleanup_temp_files(prefix)

    def _cleanup_temp_files(self, prefix):
        blobs = self.bucket.list_blobs(prefix=f"tmp_audio_files/{prefix}")
        for blob in blobs:
            try:
                blob.delete()
                logger.debug(f"Cleaned up temporary file: {blob.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {blob.name}: {e}")


    @contextmanager
    def _get_client(self) -> Generator[texttospeech.TextToSpeechClient, None, None]:
        """
        Context manager for handling the Text-to-Speech client with timeout handling.
        """
        client = None
        try:
            # Create client options
            client_options = client_options_lib.ClientOptions(
                api_endpoint=f'{self.LOCATION}-texttospeech.googleapis.com'
            )

            # Create retry strategy
            retry_config = retries.Retry(
                initial=1.0,  # Initial delay in seconds
                maximum=60.0,  # Maximum delay in seconds
                multiplier=2.0,  # Delay multiplier
                predicate=retries.if_exception_type(
                    exceptions.DeadlineExceeded,
                    exceptions.ServiceUnavailable,
                ),
            )

            logger.debug("Creating TextToSpeechClient with configured options")
            client = texttospeech.TextToSpeechClient(
                client_options=client_options
            )
            
            logger.debug("TextToSpeechClient created successfully")
            yield client
            
        except Exception as e:
            logger.error(f"Error creating TextToSpeechClient: {str(e)}", exc_info=True)
            raise
        finally:
            if client:
                try:
                    if hasattr(client, 'transport'):
                        transport = client.transport
                        if hasattr(transport, 'grpc_channel'):
                            transport.grpc_channel.close()
                        elif hasattr(transport, '_channel'):
                            transport._channel.close()
                    logger.debug("Client resources cleaned up successfully")
                except Exception as e:
                    logger.warning(f"Error during client cleanup: {e}")


    def _chunk_text(self, text: str, max_bytes: int = 5000) -> List[str]:
        """
        Splits the input text into chunks that don't exceed the maximum byte size.
        Ensures splitting occurs at sentence boundaries when possible, falling back to word boundaries.
        
        Args:
            text (str): The text to be split into chunks
            max_bytes (int): Maximum size of each chunk in bytes
            
        Returns:
            List[str]: List of text chunks
        """
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided")
            return []
        
        sentences = text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Add period back if it's not the last sentence
            sentence = sentence + '. ' if sentence != sentences[-1] else sentence
            
            # Check if adding this sentence would exceed the byte limit
            potential_chunk = current_chunk + sentence
            if len(potential_chunk.encode('utf-8')) > max_bytes:
                # If the sentence itself is too long, split by words
                if not current_chunk:
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len((temp_chunk + " " + word).encode('utf-8')) > max_bytes:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = word
                        else:
                            temp_chunk += " " + word if temp_chunk else word
                    current_chunk = temp_chunk
                else:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
            else:
                current_chunk = potential_chunk
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.debug(f"Text split into {len(chunks)} chunks")
        return chunks


def text_to_speech(article_id) -> bool:
    """
    Main entry point for text-to-speech conversion using an article ID.
    """
    
    try:
        # Retrieve article content
        logger.info(f"Attempting to retrieve article with ID {article_id}")
        article = get_article_by_id(article_id)
        if not article:
            logger.error(f"Article with ID {article_id} does not exist.")
            return False
            
        text_content = article['content']
        content_length = len(text_content.encode('utf-8'))
        logger.info(f"Retrieved article content. Length: {content_length} bytes")
        
        if not text_content.strip():
            logger.error(f"Article with ID {article_id} has empty content.")
            return False

        # Initialize TextToSpeech instance
        logger.info("Initializing TextToSpeech instance")
        text_converter = TextToSpeech()

        # Convert text to speech based on content size
        logger.info(f"Starting conversion for content of size {content_length} bytes")
        if content_length <= 5000:
            logger.info("Using single-chunk conversion method")
            audio_response = text_converter.convert_text_to_speech(text_content)
        else:
            logger.info("Using multi-chunk conversion method")
            audio_response = text_converter.process_large_text(text_content)

        if audio_response is None:
            logger.error("Text-to-speech conversion failed - audio_response is None")
            return False

        # Convert WAV to M4A
        logger.info("Converting WAV to M4A")
        wav_audio = io.BytesIO(audio_response)
        audio = AudioSegment.from_wav(wav_audio)
        m4a_audio = io.BytesIO()
        audio.export(m4a_audio, format="ipod", bitrate="64k")
        m4a_audio.seek(0)
        
        # Log audio response details
        audio_size = m4a_audio.getbuffer().nbytes
        logger.info(f"Audio conversion completed. M4A audio size: {audio_size} bytes")

        logger.info(f"Attempting to save M4A audio file for article ID {article_id}")
        success = create_audio_file(article_id, m4a_audio)
        if not success:
            logger.error("Failed to save M4A audio to the database.")
            return False

        logger.info(f"M4A audio successfully saved for article ID {article_id}")
        return True

    except Exception as e:
        logger.error(f"An unexpected error occurred in text_to_speech: {str(e)}", exc_info=True)
        return False

