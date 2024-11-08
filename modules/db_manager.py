# /home/bdavidriggins/Projects/clean_scrape_gcp/modules/db_manager.py

"""
Database Module
This module handles all database interactions related to articles within the application.
It provides functions to initialize the database, retrieve, create, update, and delete articles.
Designed to work with a Flask application using Google Cloud Firestore as the database backend
and Google Cloud Storage for audio file storage.
"""

from google.cloud import firestore
from google.cloud import storage
from modules.common_logger import setup_logger
from typing import Optional, List, Dict, Union
import datetime
import os
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore, storage
from google.cloud import pubsub_v1


# Firestore setup
if os.getenv('FIRESTORE_EMULATOR_HOST'):
    db = firestore.Client(
        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
        credentials=AnonymousCredentials(),
    )
else:
    db = firestore.Client()

# # Cloud Storage setup
# if os.getenv('USE_MOCK_STORAGE') == 'true':
#     from mock_storage import storage_client, bucket
# else:
from google.cloud import storage
storage_client = storage.Client()
bucket = storage_client.bucket(os.environ.get('GCS_BUCKET_NAME'))


# Pub/Sub setup
if os.getenv('PUBSUB_EMULATOR_HOST'):
    publisher = pubsub_v1.PublisherClient(
        credentials=AnonymousCredentials(),
    )
    subscriber = pubsub_v1.SubscriberClient(
        credentials=AnonymousCredentials(),
    )
else:
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()



# Initialize the logger for database operations
logger = setup_logger("database")

# Initialize Firestore client
db = firestore.Client()

# Initialize Cloud Storage client
storage_client = storage.Client()
bucket_name = os.environ.get('GCS_BUCKET_NAME', 'your-default-bucket-name')
bucket = storage_client.bucket(bucket_name)



def get_all_articles():
    """
    Retrieve all articles from the database.
    """
    try:
        articles = db.collection('articles').order_by('id', direction=firestore.Query.DESCENDING).get()
        logger.debug(f"Retrieved {len(articles)} articles from the database.")
        return [doc.to_dict() for doc in articles]
    except Exception as e:
        logger.error(f"Error retrieving articles: {str(e)}")
        return []

def get_article_by_id(article_id):
    """
    Retrieve a specific article by its ID.
    """
    try:
        doc_ref = db.collection('articles').document(str(article_id))
        doc = doc_ref.get()
        if doc.exists:
            logger.debug(f"Article found with ID {article_id}.")
            return doc.to_dict()
        logger.warning(f"No article found with ID {article_id}.")
        return None
    except Exception as e:
        logger.error(f"Error retrieving article {article_id}: {str(e)}")
        return None

def save_article(content, title="", author="", date="", description="", url=None, source_type="url"):
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
        doc_ref.set(article_data)
        logger.info(f"Article saved successfully: {title or 'N/A'} (Source: {source_type})")
        return True
    except Exception as e:
        logger.error(f"Error saving article: {str(e)}")
        return False

def get_last_article_id() -> Optional[str]:
    """
    Retrieve the ID of the last inserted article.
    """
    try:
        articles = db.collection('articles').order_by('created_at', direction=firestore.Query.DESCENDING).limit(1).get()
        for doc in articles:
            logger.info(f"Retrieved last article ID: {doc.id}")
            return doc.id
        logger.warning("No articles found in the database")
        return None
    except Exception as e:
        logger.error(f"Database error when retrieving last article ID: {e}")
        return None

def update_article_by_id(article_id, content, title=None, author=None, description=None):
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

        doc_ref.update(update_data)
        logger.info(f"Article {article_id} updated successfully.")
        return True
    except Exception as e:
        logger.error(f"Error updating article {article_id}: {str(e)}")
        return False

def delete_article_by_id(article_id):
    """
    Delete an article from the database by its ID, along with its associated audio file.
    """
    try:
        # Delete the article from Firestore
        db.collection('articles').document(str(article_id)).delete()

        # Delete associated audio file from Cloud Storage
        blob = bucket.blob(f'audio_files/{article_id}.mp3')
        blob.delete()

        logger.info(f"Article {article_id} and its associated audio file deleted successfully.")
        return True
    except Exception as e:
        logger.error(f"Error deleting article {article_id}: {str(e)}")
        return False

def create_audio_file(article_id: str, audio_content: bytes) -> bool:
    """
    Save a new audio file associated with an article in Cloud Storage.
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.mp3')
        blob.upload_from_string(audio_content, content_type='audio/mpeg')

        # Update the article document in Firestore with the audio file reference
        doc_ref = db.collection('articles').document(str(article_id))
        doc_ref.update({
            'audio_file_path': f'audio_files/{article_id}.mp3',
            'audio_updated_at': firestore.SERVER_TIMESTAMP
        })

        logger.info(f"Audio file created for article ID {article_id}.")
        return True
    except Exception as e:
        logger.error(f"Error creating audio file for article ID {article_id}: {e}")
        return False

def get_audio_file_by_article_id(article_id: str) -> Optional[bytes]:
    """
    Retrieve the audio file associated with a specific article from Cloud Storage.
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.mp3')
        audio_content = blob.download_as_bytes()
        logger.info(f"Audio file retrieved for article ID {article_id}.")
        return audio_content
    except Exception as e:
        logger.error(f"Error retrieving audio file for article ID {article_id}: {e}")
        return None

def update_audio_file(article_id: str, new_audio_content: bytes) -> bool:
    """
    Update the audio file for a specific article in Cloud Storage.
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.mp3')
        blob.upload_from_string(new_audio_content, content_type='audio/mpeg')

        # Update the article document in Firestore
        doc_ref = db.collection('articles').document(str(article_id))
        doc_ref.update({
            'audio_updated_at': firestore.SERVER_TIMESTAMP
        })

        logger.info(f"Audio file updated for article ID {article_id}.")
        return True
    except Exception as e:
        logger.error(f"Error updating audio file for article ID {article_id}: {e}")
        return False

def delete_audio_file(article_id: str) -> bool:
    """
    Delete the audio file associated with a specific article from Cloud Storage.
    """
    try:
        blob = bucket.blob(f'audio_files/{article_id}.mp3')
        blob.delete()

        # Update the article document in Firestore
        doc_ref = db.collection('articles').document(str(article_id))
        doc_ref.update({
            'audio_file_path': firestore.DELETE_FIELD,
            'audio_updated_at': firestore.DELETE_FIELD
        })

        logger.info(f"Audio file deleted for article ID {article_id}.")
        return True
    except Exception as e:
        logger.error(f"Error deleting audio file for article ID {article_id}: {e}")
        return False

def get_audio_files_info() -> list:
    """
    Retrieve information about all audio files in the database.
    """
    try:
        articles = db.collection('articles').where('audio_file_path', '!=', None).get()
        audio_files_info = []
        for doc in articles:
            data = doc.to_dict()
            audio_files_info.append({
                'id': doc.id,
                'article_id': doc.id,
                'article_title': data.get('title', 'Unknown'),
                'created_at': data.get('created_at'),
                'updated_at': data.get('audio_updated_at')
            })
        logger.info(f"Retrieved information for {len(audio_files_info)} audio files.")
        return audio_files_info
    except Exception as e:
        logger.error(f"Error retrieving audio files information: {e}")
        return []