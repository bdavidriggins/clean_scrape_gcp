# /home/bdavidriggins/Projects/clean_scrape/modules/common_logger.py
import logging
import os
from google.cloud import logging as cloud_logging

def setup_logger(name, log_file='app.log', level=logging.DEBUG):
    """
    Sets up a logger with the specified name and log file.
    Uses App Engine logging when deployed, and file-based logging when running locally.
    :param name: Name of the logger (typically the module name).
    :param log_file: The file where logs will be written (used only for local logging).
    :param level: Logging level.
    :return: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if running on App Engine
    if os.getenv('GAE_ENV', '').startswith('standard'):
        # Running on App Engine, use Cloud Logging
        client = cloud_logging.Client()
        handler = cloud_logging.handlers.CloudLoggingHandler(client)
        handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))
        logger.addHandler(handler)
        
        # Add a custom label to identify your logs
        logger = logging.LoggerAdapter(logger, {'app_name': 'clean_scrape'})
    else:
        # Running locally, use file-based logging
        if not logger.handlers:
            fh = logging.FileHandler(log_file)
            fh.setLevel(level)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    return logger

def truncate_text(text):
    """
    Truncates the text to show only the first and last `max_length` characters.
    If the text is shorter than or equal to 2 * max_length, it returns the original text.
    
    Args:
        text (str): The text to truncate.
        
        
    Returns:
        str: The truncated text with an ellipsis in the middle if necessary.
    """
    #The number of characters to show from the start and end.
    max_length = 100
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= 2 * max_length:
        return text
    return f"{text[:max_length]}\n\n...truncated...\n\n{text[-max_length:]}"