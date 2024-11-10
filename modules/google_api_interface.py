# /home/bdavidriggins/Projects/clean_scrape/modules/google_api_interface.py

"""
Google API Interface Module

This module provides the ContentGenerator class, which interfaces with Google's Vertex AI
to generate content based on user prompts. It includes comprehensive logging, error handling,
and adheres to common development standards to ensure high-quality, maintainable code.

Key Components:
- ContentGenerator: Handles initialization and interaction with Vertex AI for content generation.
- get_content_response: Public function to generate content using ContentGenerator.
- Logging Configuration: Utilizes the common_logger for centralized logging.
"""

import os
import traceback
from typing import List, Optional
import json
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting
from google.oauth2 import service_account
from modules.common_logger import setup_logger, truncate_text
from google.auth import default
import asyncio

# Fixed Variables
PROJECT_ID = 'resewrch-agent'  # Replace with your GCP project ID
DEFAULT_MODEL_NAME = 'gemini-1.5-flash-002'

GENERATION_CONFIG = {
    "max_output_tokens": 8192,  # Limit the number of tokens for testing
    "temperature": 0,
    "top_p": 1.0,
}


# Setup logger for google_api_interface.py
logger = setup_logger("google_api_interface")


class ContentGenerator:
    """
    ContentGenerator interfaces with Google Vertex AI to generate content based on user prompts.
    It includes logging, error handling, and follows best development practices.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initializes the ContentGenerator with Vertex AI configurations and sets up logging.

        :param model_name: The name of the generative model to use. Defaults to DEFAULT_MODEL_NAME.
        """
        self.logger = logger
        self.generation_config = GENERATION_CONFIG
        self.safety_settings = self.default_safety_settings()
        self.model_name = model_name or DEFAULT_MODEL_NAME

        # Use default application credentials
        try:
            vertexai.init(project=PROJECT_ID)
            self.model = GenerativeModel(
                self.model_name
            )
        except Exception as e:
            self.logger.error(f"Failed to load service account credentials: {e}", exc_info=True)
            raise

    @staticmethod
    def default_safety_settings() -> List[SafetySetting]:
        """
        Defines default safety settings.

        :return: List of default SafetySetting instances.
        """
        return [
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=SafetySetting.HarmBlockThreshold.OFF
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=SafetySetting.HarmBlockThreshold.OFF
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=SafetySetting.HarmBlockThreshold.OFF
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=SafetySetting.HarmBlockThreshold.OFF
            ),
        ]


    async def generate_content(self, user_prompt: str) -> str:
        """
        Generates content based on the user prompt and logs the response.
        :param user_prompt: The input prompt from the user.
        :return: Generated content as a string.
        """
        try:
            self.logger.info(f"Generating content for prompt: \n'{truncate_text(user_prompt)}'")
            chat = self.model.start_chat(response_validation=False)
            response = await asyncio.to_thread(
                chat.send_message,
                [user_prompt],
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            generated_text = response.text
            
            self.logger.info(f"Content generation successful: \n'{truncate_text(generated_text)}'")
            return generated_text
        except Exception as e:
            self.logger.error(
                f"Error during content generation: {str(e)}",
                exc_info=True
            )
            raise
