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
from modules.common_logger import setup_logger


# Fixed Variables
PROJECT_ID = 'resewrch-agent'  # Replace with your GCP project ID
LOCATION = 'us-central1'
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
        
        # Get the path to the JSON file in the same directory as this script
        current_dir = os.path.dirname(__file__)
        json_path = os.path.join(current_dir, 'service_account.json')

        # Load the JSON credentials from the file
        try:
            with open(json_path, 'r') as file:
                service_account_info = json.load(file)
            self.credentials = service_account.Credentials.from_service_account_info(service_account_info)
            self._initialize_vertexai()
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

    def _initialize_vertexai(self):
        """
        Initializes the Vertex AI client and loads the generative model.
        """
        try:
            vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=self.credentials)
            self.model = GenerativeModel(
                self.model_name
            )
            self.logger.info(f"Vertex AI initialized successfully with model '{self.model_name}'.")
        except Exception as e:
            self.logger.error(
                f"Failed to initialize Vertex AI with model '{self.model_name}': {str(e)}",
                exc_info=True
            )
            raise

    def generate_content(self, user_prompt: str) -> str:
        """
        Generates content based on the user prompt and logs the response.

        :param user_prompt: The input prompt from the user.
        :return: Generated content as a string.
        """
        try:
            self.logger.info(f"Generating content for prompt: '{user_prompt}'")
            chat = self.model.start_chat(response_validation=False)
            response = chat.send_message(
                [user_prompt],
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            generated_text = response.text  # Assuming response has a 'text' attribute
            
            self.logger.info("Content generation successful.")
            return generated_text
        except Exception as e:
            self.logger.error(
                f"Error during content generation: {str(e)}",
                exc_info=True
            )
            raise


def get_content_response(
    user_prompt: str,
    model_name: Optional[str] = None
) -> str:
    """
    Public function to generate content based on user prompt using ContentGenerator.

    :param user_prompt: The input prompt from the user.
    :param model_name: Optional model name to use. If not provided, defaults are used.
    :return: Generated content as a string.
    """
    try:
        # Initialize ContentGenerator with provided parameters
        content_generator = ContentGenerator(
            model_name=model_name
        )

        # Generate content
        response = content_generator.generate_content(user_prompt)
        
        return response
    except Exception as e:
        logger.error(
            f"Error in get_content_response: {str(e)}",
            exc_info=True
        )
        return "An error occurred while generating the content."


if __name__ == '__main__':
    import sys

    def main():
        """
        Main function to test the ContentGenerator class.
        """
        # Define a test prompt
        test_prompt = "Who was Robert Rogers and what was his leadership style?"
        custom_model_name = "gemini-1.5-flash-002"

        # Generate content using the public interface
        try:
            generated_content = get_content_response(
                user_prompt=test_prompt,
                model_name=custom_model_name  # Pass custom model name
            )
            print("\n--- Generated Content ---\n")
            print(generated_content)
            print("\n--- End of Generated Content ---\n")
        except Exception as gen_error:
            logger.error(f"An error occurred during content generation: {gen_error}", exc_info=True)
            traceback.print_exc()
            sys.exit(1)

    main()
