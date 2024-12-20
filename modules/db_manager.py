# /home/bdavidriggins/Projects/clean_scrape_gcp/modules/db_manager.py

"""
Database Module
This module handles all database interactions related to articles within the application.
It provides functions to initialize the database, retrieve, create, update, and delete articles.
Designed to work with a Flask application using Google Cloud Firestore as the database backend
and Google Cloud Storage for audio file storage.
"""

from google.cloud.firestore_v1 import AsyncClient
from google.cloud import firestore
from google.cloud import storage
from google.cloud import exceptions as gcp_exceptions
from modules.common_logger import setup_logger
from typing import Optional, List, Dict, Union
import datetime
import os
from google.auth.credentials import AnonymousCredentials
from google.oauth2 import service_account
import json
from io import BytesIO
from google.cloud import storage

import asyncio
from functools import partial

# Determine if we're running on App Engine
is_appengine = os.getenv('GAE_ENV', '').startswith('standard')

# # FireStore
# Get the database name from environment variables
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
DATABASE_NAME = os.getenv('FIRESTORE_DATABASE', 'clean-scrape-articles')
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'clean-scrape-audio-files')


# Initialize clients based on environment
if is_appengine:
    # On App Engine, use default credentials
    db = AsyncClient(project=PROJECT_ID, database=DATABASE_NAME)

    storage_client = storage.Client()
else:
    # Clear any local emulator settings
    os.environ.pop('FIRESTORE_EMULATOR_HOST', None)
    os.environ.pop('GOOGLE_CLOUD_FIRESTORE_EMULATOR_HOST', None)

    # Locally, use service account key
    json_path = os.path.join(os.getcwd(), 'service-account-key.json')
    with open(json_path, 'r') as file:
        service_account_info = json.load(file)
    
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    
    db = AsyncClient(
        project=PROJECT_ID,
        credentials=credentials,
        database=DATABASE_NAME
    )
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)


bucket = storage_client.bucket(GCS_BUCKET_NAME)




logger = setup_logger("database")



async def get_all_articles():
    """
    Retrieve all articles from the database.
    """
    try:        
        articles = await db.collection('articles').order_by('id', direction=firestore.Query.DESCENDING).get()
        logger.debug(f"Retrieved {len(articles)} articles from the database.")
        return [doc.to_dict() for doc in articles]
    except Exception as e:
        logger.error(f"Error retrieving articles: {str(e)}")
        return []

async def get_article_by_id(article_id):
    """
    Retrieve a specific article by its ID.
    """
    try:
        doc_ref = db.collection('articles').document(str(article_id))
        doc = await doc_ref.get()
        if doc.exists:
            logger.debug(f"Article found with ID {article_id}.")
            return doc.to_dict()
        logger.warning(f"No article found with ID {article_id}.")
        return None
    except Exception as e:
        logger.error(f"Error retrieving article {article_id}: {str(e)}")
        return None

async def get_articles_with_audio_status() -> List[Dict]:
    """
    Retrieve all articles with their audio status.
    Determines if an article has associated audio by checking the 'audio_file_path' field.
    Orders articles by creation date, descending.
    
    :return: List of articles with 'has_audio' boolean field.
    """
    try:
        articles_ref = db.collection('articles').order_by('created_at', direction=firestore.Query.DESCENDING)
        articles = await articles_ref.get()
        articles_with_status = []
        for doc in articles:
            data = doc.to_dict()
            has_audio = bool(data.get('audio_file_path'))
            article = {
                'id': doc.id,  # Use document ID directly
                'url': data.get('url'),
                'content': data.get('content'),
                'title': data.get('title'),
                'author': data.get('author'),
                'date': data.get('date'),
                'description': data.get('description'),
                'has_audio': has_audio
            }
            articles_with_status.append(article)
        logger.debug(f"Retrieved {len(articles_with_status)} articles with audio status.")
        return articles_with_status
    except Exception as e:
        logger.error(f"Error retrieving articles with audio status: {e}")
        return []
    
async def save_article(content, title="", author="", date="", description="", url=None, source_type="url"):
    """
    Save a new article to the database.
    """
    try:
        doc_ref = db.collection('articles').document()
        article_data = {
            'id': doc_ref.id,
            'url': url,
            'content': content,
            'title': title,
            'author': author,
            'date': date,
            'description': description,
            'source_type': source_type,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        await doc_ref.set(article_data)
        logger.info(f"Article saved successfully: {title or 'N/A'} (Source: {source_type})")
        return True
    except Exception as e:
        logger.error(f"Error saving article: {str(e)}")
        return False

async def get_last_article_id() -> Optional[str]:
    """
    Retrieve the ID of the last inserted article.
    """
    try:
        articles = await db.collection('articles').order_by('created_at', direction=firestore.Query.DESCENDING).limit(1).get()
        for doc in articles:
            logger.info(f"Retrieved last article ID: {doc.id}")
            return doc.id
        logger.warning("No articles found in the database")
        return None
    except Exception as e:
        logger.error(f"Database error when retrieving last article ID: {e}")
        return None

async def update_article_by_id(article_id, content, title=None, author=None, description=None):
    """
    Update an existing article in the database.
    """
    try:
        doc_ref = db.collection('articles').document(str(article_id))
        update_data = {'content': content, 'updated_at': firestore.SERVER_TIMESTAMP}
        if title is not None:
            update_data['title'] = title
        if author is not None:
            update_data['author'] = author
        if description is not None:
            update_data['description'] = description

        await doc_ref.update(update_data)
        logger.info(f"Article {article_id} updated successfully.")
        return True
    except Exception as e:
        logger.error(f"Error updating article {article_id}: {str(e)}")
        return False

async def delete_article_by_id(article_id):
    """
    Delete an article from the database by its ID, along with its associated audio file if it exists.
    """
    try:
        # Delete the article from Firestore
        await db.collection('articles').document(str(article_id)).delete()
        logger.info(f"Article {article_id} deleted from Firestore.")

        # Attempt to delete associated audio file from Cloud Storage
        try:
            blob = bucket.blob(f'audio_files/{article_id}.m4a')
            await asyncio.to_thread(blob.delete)
            logger.info(f"Associated audio file for article {article_id} deleted successfully.")
        except gcp_exceptions.NotFound:
            logger.info(f"No associated audio file found for article {article_id}.")
        except Exception as audio_error:
            logger.warning(f"Error deleting audio file for article {article_id}: {str(audio_error)}")

        return True
    except Exception as e:
        logger.error(f"Error deleting article {article_id}: {str(e)}")
        return False


async def create_audio_file(article_id: str, m4a_audio: Union[BytesIO, bytes]) -> bool:
    """
    Save a new M4A audio file associated with an article in Cloud Storage.
    
    :param article_id: The ID of the article
    :param m4a_audio: BytesIO or bytes object containing the M4A audio data
    :return: True if successful, False otherwise
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.m4a')
        
        # Convert bytes to BytesIO if necessary
        if isinstance(m4a_audio, bytes):
            m4a_audio = BytesIO(m4a_audio)
        
        m4a_audio.seek(0)
        await asyncio.to_thread(blob.upload_from_file, m4a_audio, content_type='audio/mp4')
        
        # Update the article document in Firestore with the audio file reference
        doc_ref = db.collection('articles').document(str(article_id))
        await doc_ref.update({
            'audio_file_path': f'audio_files/{article_id}.m4a',
            'audio_updated_at': firestore.SERVER_TIMESTAMP
        })
        logger.info(f"M4A audio file created for article ID {article_id}.")
        return True
    except Exception as e:
        logger.error(f"Error creating M4A audio file for article ID {article_id}: {e}")
        return False


async def get_audio_file_by_article_id(article_id: str) -> Optional[BytesIO]:
    """
    Retrieve the M4A audio file associated with a specific article from Cloud Storage.
    
    :param article_id: The ID of the article
    :return: BytesIO object containing the audio file data, or None if not found
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.m4a')
        audio_content = await asyncio.to_thread(blob.download_as_bytes)
        logger.info(f"M4A audio file retrieved for article ID {article_id}.")
        return BytesIO(audio_content)
    except Exception as e:
        logger.error(f"Error retrieving M4A audio file for article ID {article_id}: {e}")
        return None
    

async def update_audio_file(article_id: str, new_audio_content: Union[BytesIO, bytes]) -> bool:
    """
    Update the M4A audio file for a specific article in Cloud Storage.
    
    :param article_id: The ID of the article
    :param new_audio_content: BytesIO or bytes object containing the new M4A audio data
    :return: True if successful, False otherwise
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.m4a')
        
        # Convert bytes to BytesIO if necessary
        if isinstance(new_audio_content, bytes):
            new_audio_content = BytesIO(new_audio_content)
        
        new_audio_content.seek(0)
        await asyncio.to_thread(blob.upload_from_file, new_audio_content, content_type='audio/mp4')
        
        # Update the article document in Firestore
        doc_ref = db.collection('articles').document(str(article_id))
        await doc_ref.update({
            'audio_updated_at': firestore.SERVER_TIMESTAMP
        })
        logger.info(f"M4A audio file updated for article ID {article_id}.")
        return True
    except Exception as e:
        logger.error(f"Error updating M4A audio file for article ID {article_id}: {e}")
        return False

async def delete_audio_file(article_id: str) -> bool:
    """
    Delete the M4A audio file associated with a specific article from Cloud Storage.
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.m4a')
        await asyncio.to_thread(blob.delete)
        
        # Update the article document in Firestore
        doc_ref = db.collection('articles').document(str(article_id))
        await doc_ref.update({
            'audio_file_path': firestore.DELETE_FIELD,
            'audio_updated_at': firestore.DELETE_FIELD
        })
        logger.info(f"M4A audio file deleted for article ID {article_id}.")
        return True
    except Exception as e:
        logger.error(f"Error deleting M4A audio file for article ID {article_id}: {e}")
        return False

async def get_audio_files_info() -> List[Dict]:
    """
    Retrieve information about all audio files in the database.
    """
    try:
        # First, get all articles
        articles = await db.collection('articles').get()
        audio_files_info = []
        for doc in articles:
            data = doc.to_dict()
            # Only include articles that have an audio_file_path
            if 'audio_file_path' in data and data['audio_file_path'] is not None:
                audio_files_info.append({
                    'id': doc.id,
                    'article_id': doc.id,
                    'article_title': data.get('title', 'Unknown'),
                    'audio_file_path': data['audio_file_path'],
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('audio_updated_at')
                })
        logger.info(f"Retrieved information for {len(audio_files_info)} audio files.")
        return audio_files_info
    except Exception as e:
        logger.error(f"Error retrieving audio files information: {e}")
        return []