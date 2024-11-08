import json
import os
from google.cloud import firestore
from google.cloud import storage
from google.oauth2 import service_account
from google.auth.transport import requests
import google.auth

# Load service account key
json_path = os.path.join(os.getcwd(), 'service-account-key.json')
with open(json_path, 'r') as file:
    service_account_info = json.load(file)

# Create credentials
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Get project ID from credentials
PROJECT_ID = credentials.project_id

# Set other variables
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')  # replace with your actual bucket name
DATABASE_NAME = os.getenv('FIRESTORE_DATABASE', 'clean-scrape-articles')


# Clear any local emulator settings
os.environ.pop('FIRESTORE_EMULATOR_HOST', None)
os.environ.pop('GOOGLE_CLOUD_FIRESTORE_EMULATOR_HOST', None)

print(f"Project ID from credentials: {PROJECT_ID}")
print(f"Service account email: {credentials.service_account_email}")
print(f"Credentials type: {type(credentials).__name__}")

def test_firestore_connection():
    print(f"Testing Firestore connection for project: {PROJECT_ID}")
    try:
        # Initialize Firestore client with explicit credentials
        db = firestore.Client(
            project=PROJECT_ID,
            credentials=credentials,
            client_options={
                'api_endpoint': 'firestore.googleapis.com:443'
            },
            database=DATABASE_NAME
        )
        
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
        raise  # Re-raise the exception to see the full stack trace

def test_cloud_storage_connection():
    print(f"Testing Cloud Storage connection for project: {PROJECT_ID}, bucket: {GCS_BUCKET_NAME}")
    try:
        # Initialize Storage client with explicit credentials
        storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
        
        # Check if the bucket exists
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        if not bucket.exists():
            print(f"Bucket {GCS_BUCKET_NAME} does not exist.")
            return
        
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
        raise  # Re-raise the exception to see the full stack trace

if __name__ == "__main__":
    try:
        test_firestore_connection()
        print("\n")
        test_cloud_storage_connection()
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print("Full exception details:")
        traceback.print_exc()