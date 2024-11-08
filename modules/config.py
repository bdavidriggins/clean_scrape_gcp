# /home/bdavidriggins/Projects/clean_scrape/config.py
"""
config.py

This module is responsible for initializing and validating the configuration settings 
required for the clean_scrape application. It sets up essential directories, database 
connections, web request headers, and initializes the spaCy NLP model. The configurations 
are crucial for the application's functionality, ensuring that articles are properly 
stored, processed, and cleaned before further processing.
"""

import os
import spacy
import subprocess
from modules.common_logger import setup_logger
import sys 

# Initialize the logger for the config module
logger = setup_logger("config")



def initialize_nlp():
    """Initialize spaCy NLP model"""
    try:
        # Try to load the model directly
        nlp = spacy.load('en_core_web_sm')
        return nlp
    except OSError:
        logger.warning("Could not load spaCy model directly, attempting download...")
        try:
            # If the model isn't found, download it
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], 
                         check=True, capture_output=True)
            nlp = spacy.load('en_core_web_sm')
            return nlp
        except Exception as e:
            logger.error(f"Failed to download spaCy model: {str(e)}")
            raise

def initialize_config():
    """
    Initialize and validate configuration settings.

    This function sets up the necessary paths, ensures that the articles directory exists,
    configures the database path, sets up web request headers, and defines prompts and model names
    for article cleaning.

    Returns:
        tuple: Contains application path, articles directory, database name, headers, 
               model flash name, and article clean prompt.

    Raises:
        ValueError: If the articles path exists but is not a directory.
        PermissionError: If there are permission issues creating the articles directory.
        Exception: For any other errors during configuration initialization.
    """
    logger.info("Initializing configuration settings")
    
    try:
        # Base configurations
        app_path = os.path.dirname(os.path.abspath(__file__))
        logger.debug(f"Application path: {app_path}")
                   
        # Database configuration
        db_name = "articles.db"
        db_path = os.path.join(app_path, db_name)
        logger.debug(f"Database path: {db_path}")
        
        # Headers configuration
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        logger.debug("Web request headers configured")
        
        # Define the NLP model and prompt for cleaning articles
        model_flash_name = "gemini-1.5-flash-002"
        
        article_clean_prompt = '''You are an expert content curator and text cleaning specialist. Your task is to process web-scraped content and extract only the meaningful article text while maintaining its full integrity. Follow these precise guidelines:

    Content Removal - Eliminate Only Non-Essential Elements:
        Advertisements and Promotional Content: Remove all ads, banner texts, and promotional sections.
        Cookie Notices and Privacy Policy Popups: Delete any mentions of cookies, privacy policies, or related popups.
        Newsletter/Subscription Prompts: Eliminate prompts for signing up to newsletters, subscriptions, or email lists.
        Social Media Buttons and Sharing Options: Remove social media icons, share buttons, and related links.
        Navigation Elements and Menu Text: Delete navigation bars, menus, and any related text not part of the main article.
        Image Captions, Alt Text, and Metadata: Remove captions, alternative text descriptions, and any image metadata.
        Comment Sections and Reader Feedback: Eliminate sections containing comments, reader feedback, or discussion threads.
        Related Article Suggestions: Remove links or sections suggesting related articles.
        Author Bios and Timestamps: Delete author biographies and publication timestamps unless they are integral to the article's content.
        Footer Information and Site Navigation: Remove footer details, additional navigation links, and any site-wide information.
        JavaScript or HTML Artifacts: Delete any residual JavaScript code, HTML tags, or artifacts that may have been captured.

    Content Preservation - Maintain Complete Article Integrity:
        Main Article Text: Preserve the entire main body of the article without any omissions.
        Headlines and Subheadings: Keep all headlines, subheadings, and section titles as they are part of the article structure.
        Paragraph Structure: Maintain the original paragraphing to ensure logical flow and readability.
        Lists and Bullet Points: Retain all lists, bullet points, and numbered items that are part of the article.
        Quotes and Citations: Keep all direct quotes, citations, and references included in the article.
        Statistical Data and Figures: Preserve all important statistics, data points, tables, and figures that are essential to the article.

    Avoid Altering Content:
        No Summarization: Do not condense or summarize any part of the article.
        No Meaning Alteration: Ensure that the original meaning, context, and information of the article remain unchanged.
        No Content Modification: Do not rephrase, edit for style, or make any changes to the wording of the article content.

    Formatting for Voice-to-Text Compatibility:
        Clear Formatting: Ensure the cleaned text is well-formatted with proper spacing and indentation to facilitate accurate voice-to-text conversion.
        Consistent Style: Maintain consistent formatting throughout the document without introducing new formatting styles.

    Final Quality Check:
        Logical Flow: Verify that the cleaned text flows logically from start to finish.
        Complete Sentences: Ensure all sentences are complete and coherent.
        No Content Loss: Double-check that no essential content from the original article has been removed or altered.

Please process the following web-scraped content according to these guidelines:
Article:

{article_text}'''

        article_improve_readability_prompt = '''You are an expert text optimization specialist focusing on converting articles into formats perfectly suited for Text-to-Speech (TTS) systems. Your task is to transform the input text while maintaining its meaning and enhancing its clarity for audio consumption, do not replace words for simpler words do not remove sentences, try your best to maintain the integrity of the article while making minor adjustments for text to speech readability only. Apply the following comprehensive rules:

1. NUMBERS AND MEASUREMENTS
  • Convert all numerical digits to words
    - Cardinal: "2002" → "two thousand two"
    - Ordinal: "1st" → "first"
    - Fractions: "1/2" → "one half"
  • Expand all measurements with full units
    - "5 km" → "five kilometers"
    - "3 hrs" → "three hours"
    - Temperature: "72°F" → "seventy-two degrees Fahrenheit"

2. DATES AND TIME
  • Convert all dates to spoken format
    - "1/15/2023" → "January fifteenth, two thousand twenty-three"
  • Convert times to natural speech
    - "9:30 AM" → "nine thirty in the morning"
    - "23:45" → "eleven forty-five at night"

3. ABBREVIATIONS AND ACRONYMS
  • First usage: Provide full form with acronym in parentheses
    - "The National Aeronautics and Space Administration (NASA)"
  • Common titles and terms
    - "Dr." → "Doctor"
    - "Mr." → "Mister"
    - "etc." → "etcetera"
    - "e.g." → "for example"

4. SYMBOLS AND SPECIAL CHARACTERS
  • Convert to spoken words
    - "&" → "and"
    - "@" → "at"
    - "%" → "percent"
    - "$" → "dollars"
    - "+" → "plus"
    - "=" → "equals"

5. DIGITAL ELEMENTS
  • Convert web elements to spoken format
    - "example@gmail.com" → "example at gmail dot com"
    - "www.website.com" → "w w w dot website dot com"
  • Technical symbols
    - "/" → "forward slash"
    - "_" → "underscore"

6. FORMATTING AND STRUCTURE
  • Mathematical expressions
    - "5x3" → "five times three"
    - "10²" → "ten squared"

7. CLARITY ENHANCEMENTS
  • Add brief contextual clarifications when needed
  • Expand confusing abbreviations
  • Convert complex symbols to simple spoken equivalents

8. CONSISTENCY RULES
  • Maintain uniform treatment of similar elements
  • Keep well-known acronyms as is (NASA, FBI)
  • Use full forms for first mention of technical terms

INSTRUCTIONS:
1. Read through the entire text first
2. Apply all transformation rules systematically
4. Maintain the original meaning and context
5. Double-check all numerical conversions
6. Verify that all abbreviations are properly expanded
7. Ensure consistent formatting throughout
8. Remove any elements that wouldn't make sense in spoken form

Please transform the following text according to these rules while maintaining its professional tone and clarity:

{article_text}

OUTPUT FORMAT:
- Provide the optimized text in clear paragraphs
- Maintain appropriate punctuation for natural speech breaks
- Use standard capitalization unless specifically needed
'''

        return app_path, db_name, headers, model_flash_name, article_clean_prompt, article_improve_readability_prompt
        
    except Exception as e:
        logger.critical(f"Critical error during configuration initialization: {str(e)}")
        raise


# Main initialization block
try:
    # Initialize configuration
    APP_PATH, DB_NAME, HEADERS, MODEL_NAME_FLASH, ARTICLE_CLEAN_PROMPT, ARTICLE_IMPROVE_READABILITY_PROMPT = initialize_config()
    logger.info("Configuration initialized successfully")
        
    # Log successful initialization
    logger.info("Configuration module fully initialized")
    logger.debug(f"Model info: {NLP.meta}")
    
except Exception as e:
    logger.critical(f"Failed to initialize configuration: {str(e)}")
    raise RuntimeError("Configuration initialization failed")

# Export all configuration variables
__all__ = ['APP_PATH', 'ARTICLES_DIR', 'DB_NAME', 'HEADERS', 'NLP']
