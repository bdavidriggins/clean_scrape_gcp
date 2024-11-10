# modules/common_logger.py

import logging
import os
import threading
import uuid
from contextlib import contextmanager
from google.cloud import logging as cloud_logging

# Thread-local storage for job context
_thread_local = threading.local()

class JobContextFilter(logging.Filter):
    def filter(self, record):
        record.job_id = getattr(_thread_local, 'job_id', 'No-Job')
        record.pid = os.getpid()
        record.tid = threading.get_native_id()
        return True
    
@contextmanager
def job_context(job_id=None):
    """
    A context manager to set the current job context.
    Usage:
    with job_context("job-123"):
        logger.info("Processing job")
    """
    if job_id is None:
        job_id = str(uuid.uuid4())  # Generate a unique ID if none provided
    previous_job_id = getattr(_thread_local, 'job_id', None)
    _thread_local.job_id = job_id
    try:
        yield
    finally:
        if previous_job_id:
            _thread_local.job_id = previous_job_id
        else:
            del _thread_local.job_id

class JobContextFilter(logging.Filter):
    def filter(self, record):
        record.job_id = getattr(_thread_local, 'job_id', 'No-Job')
        record.pid = os.getpid()
        record.tid = threading.get_native_id()
        return True

def setup_logger(name, log_file='app.log', level=logging.DEBUG):
    logger = logging.getLogger(name)
    
    # Only set the level and add handlers if they haven't been set before
    if not logger.handlers:
        logger.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - [PID-%(pid)d] [TID-%(tid)d] [JOB-%(job_id)s] - %(message)s')

        if os.getenv('GAE_ENV', '').startswith('standard'):
            # App Engine setup
            client = cloud_logging.Client()
            handler = cloud_logging.handlers.CloudLoggingHandler(client)
        else:
            # Local setup
            handler = logging.FileHandler(log_file)
            # Also add a stream handler for console output in local development
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Add the JobContextFilter only once
        job_context_filter = JobContextFilter()
        logger.addFilter(job_context_filter)

    return logger

# Global logger instance
logger = setup_logger("app_logger")

# Helper functions to set/clear job context
def set_job_context(job_id):
    _thread_local.job_id = job_id

def clear_job_context():
    if hasattr(_thread_local, 'job_id'):
        del _thread_local.job_id


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