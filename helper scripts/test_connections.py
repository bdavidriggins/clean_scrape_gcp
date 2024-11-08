# test_gcp_direct.py

import json
import os
from google.cloud import firestore
from google.cloud import storage
from google.oauth2 import service_account

# Load environment variables
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
FIRESTORE_DATABASE = os.environ.get('FIRESTORE_DATABASE', '(default)')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
CREDENTIALS_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')


json_path = os.path.join(os.getcwd(), 'service-account-key.json')
with open(json_path, 'r') as file:
    service_account_info = json.load(file)
    credentials = service_account.Credentials.from_service_account_info(service_account_info)



def test_firestore_connection():
    print(f"Testing Firestore connection for project: {PROJECT_ID}, database: {FIRESTORE_DATABASE}")
    try:
        # Initialize Firestore client with explicit credentials
        db = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DATABASE, credentials=credentials)
        
        # Attempt to write to Firestore
        doc_ref = db.collection('test_collection').document('test_document')
        doc_ref.set({'test': 'successful'})
        
        # Attempt to read from Firestore
        doc = doc_ref.get()
        if doc.exists:
            print(f"Successfully connected to Firestore. Read data: {doc.to_dict()}")
        else:
            print("Connected to Firestore, but couldn't read test document.")
        
        # Clean up
        doc_ref.delete()
    except Exception as e:
        print(f"Error connecting to Firestore: {e}")

def test_cloud_storage_connection():
    print(f"Testing Cloud Storage connection for project: {PROJECT_ID}, bucket: {GCS_BUCKET_NAME}")
    try:
        # Initialize Storage client with explicit credentials
        storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
        
        # Get the bucket
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        # Attempt to write to Cloud Storage
        blob = bucket.blob('test_file.txt')
        blob.upload_from_string('Test content')
        
        # Attempt to read from Cloud Storage
        content = blob.download_as_text()
        print(f"Successfully connected to Cloud Storage. Read content: {content}")
        
        # Clean up
        blob.delete()
    except Exception as e:
        print(f"Error connecting to Cloud Storage: {e}")

if __name__ == "__main__":
    try:
        
        print(f"Using service account: {credentials.service_account_email}")
        
        test_firestore_connection()
        print("\n")
        test_cloud_storage_connection()
    except Exception as e:
        print(f"Error: {e}")