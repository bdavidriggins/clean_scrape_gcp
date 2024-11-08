# Application Architecture
1. Application Hosting:

    Google App Engine (GAE): Deploy your Flask application on App Engine's Standard Environment. GAE automatically manages infrastructure, scaling your application based on traffic, which can be more cost-effective than managing virtual machines. The Standard Environment offers a free tier with daily quotas, suitable for low to moderate traffic.

2. Data Storage:

    Cloud Firestore: Use Firestore in Native mode for storing article content and metadata. It's a NoSQL document database that scales automatically and integrates seamlessly with GAE. Firestore provides a free tier with generous limits, making it cost-effective for your needs.

    Cloud Storage: Store audio files generated from text-to-speech conversion in Cloud Storage. It offers durable and scalable object storage with a free tier that includes 5 GB of standard storage per month.

3. Web Scraping and Text-to-Speech Processing:

    Cloud Functions: Implement web scraping and text-to-speech processing as serverless functions using Cloud Functions. This approach allows you to execute code in response to events without managing servers. Cloud Functions have a free tier with 2 million invocations per month, which can be cost-effective for your processing tasks.

4. Task Orchestration:

    Cloud Pub/Sub: Use Pub/Sub to decouple components and manage communication between your web application and processing functions. For example, when a new article is scraped, publish a message to a Pub/Sub topic that triggers the text-to-speech processing function. Pub/Sub offers a free tier with 10 GB of data per month.

5. Authentication and Security:

    Identity and Access Management (IAM): Utilize IAM to manage permissions and ensure secure access to your resources. Assign appropriate roles to your services and follow the principle of least privilege.

1. Custom Domain:

    Mapping Your Domain: GAE allows you to map your application to a custom domain. After verifying domain ownership, you can add the domain to your App Engine application.
    Google Cloud

    DNS Configuration: Update your domain's DNS records to point to GAE. This typically involves setting CNAME or A records as specified by GAE during the setup process.

2. HTTPS Setup:

    Managed SSL Certificates: GAE provides managed SSL/TLS certificates at no additional cost. Once your custom domain is mapped, GAE automatically provisions and renews these certificates, enabling HTTPS for your application.
    Google Cloud

    Custom SSL Certificates: If you prefer to use your own SSL certificates, GAE supports uploading and managing them through the Google Cloud Console.

3. Static IP Address:

Reserve a Static External IP Address:
    In the Google Cloud Console, navigate to the "VPC network" section and reserve a new static external IP address.

Set Up a Global External HTTP(S) Load Balancer:
    Create a load balancer that directs traffic to your GAE application.
    Assign the reserved static IP address to the load balancer's frontend configuration.

Update DNS Records:
    Point your custom domain's DNS records to the static IP address associated with the load balancer.


# Implementation Steps:

    Develop Your Flask Application: Ensure your application is ready for deployment on App Engine. This may involve configuring your app.yaml file and ensuring compatibility with the App Engine environment.

    Set Up Firestore and Cloud Storage: Create a Firestore database and Cloud Storage bucket through the GCP Console. Update your application code to interact with these services using the appropriate client libraries.

    Implement Cloud Functions: Write functions for web scraping and text-to-speech processing. Deploy these functions using the gcloud command-line tool or the GCP Console.

    Configure Pub/Sub: Create Pub/Sub topics and subscriptions to manage communication between your application and Cloud Functions. Ensure your functions are set to trigger upon receiving messages from the appropriate topics.

    Deploy Your Application: Use the gcloud app deploy command to deploy your Flask application to App Engine. Monitor the deployment process and test your application to ensure it's functioning as expected.


# Deployment
    Automation: Utilize GitHub Actions to automate deployment processes. For instance, upon pushing changes to the main branch, GitHub Actions can trigger workflows that deploy your Flask application to Google App Engine (GAE).

    Google Cloud Deploy Action: Leverage the google-github-actions/deploy-appengine action to streamline deployments to GAE. This action simplifies the deployment process by handling authentication and deployment commands.


# Local Development Environment Setup:

    Python and Flask Installation:
        Ensure Python is installed on your laptop.
        Install Flask using pip:

    pip install Flask

    Google Cloud SDK Installation:

        Download and install the Google Cloud SDK to interact with GCP services from your local machine.

    App Engine SDK for Python:

        The Google Cloud SDK includes the App Engine extensions necessary for local development.

    Emulators for GCP Services:

        Use emulators to simulate GCP services locally:
            Datastore Emulator: For simulating Firestore in Datastore mode.
            Pub/Sub Emulator: For simulating Pub/Sub services.
        These emulators allow you to test interactions with GCP services without incurring costs.


# Monitoring and Logging:

    Implement monitoring using Google Cloud Monitoring to track application performance.
    Set up logging with Google Cloud Logging to collect and analyze logs for troubleshooting.




## Google GCP Commands
#!/bin/bash

# ===================================================================
# Script: setup_app_engine.sh
# Description: Sets up Google App Engine for the 'resewrch-agent' project,
#              assigns necessary IAM roles, deploys a minimal version,
#              and cleans up unintended deployments.
# ===================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# -------------------------------
# 1. Set the Active Google Cloud Project
# -------------------------------
echo "Setting active project to 'resewrch-agent'..."
gcloud config set project resewrch-agent
# Sets the active Google Cloud project to 'resewrch-agent' for all subsequent gcloud commands.

# -------------------------------
# 2. Align the Quota Project with the Active Project
# -------------------------------
echo "Setting quota project to 'resewrch-agent'..."
gcloud auth application-default set-quota-project resewrch-agent
# Configures the quota project to 'resewrch-agent' to ensure API usage is billed and tracked against this project.

# -------------------------------
# 3. Authenticate with the Service Account
# -------------------------------
SERVICE_ACCOUNT_KEY="service-account-key.json"  # Path to your service account key file.

if [[ ! -f "$SERVICE_ACCOUNT_KEY" ]]; then
    echo "Service account key file '$SERVICE_ACCOUNT_KEY' not found. Please provide the correct path."
    exit 1
fi

echo "Authenticating with service account..."
gcloud auth activate-service-account --key-file="$SERVICE_ACCOUNT_KEY"
# Authenticates gcloud with the service account using the specified JSON key file.

# -------------------------------
# 4. Enable Required Google Cloud APIs
# -------------------------------
echo "Enabling required Google Cloud APIs..."
gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com storage.googleapis.com cloudresourcemanager.googleapis.com
# Enables the App Engine Admin API, Cloud Build API, Cloud Storage API, and Cloud Resource Manager API.

# -------------------------------
# 5. Assign IAM Roles to the Service Account
# -------------------------------
SERVICE_ACCOUNT_EMAIL="research-agent-sa@resewrch-agent.iam.gserviceaccount.com"

echo "Assigning IAM roles to the service account '$SERVICE_ACCOUNT_EMAIL'..."

# 5.1. Assign App Engine Deployer Role
gcloud projects add-iam-policy-binding resewrch-agent \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/appengine.deployer"
# Grants the App Engine Deployer role to the service account.

# 5.2. Assign Cloud Build Editor Role
gcloud projects add-iam-policy-binding resewrch-agent \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudbuild.builds.editor"
# Grants the Cloud Build Editor role to the service account.

# 5.3. Assign Storage Admin Role
gcloud projects add-iam-policy-binding resewrch-agent \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.admin"
# Grants the Storage Admin role to the service account.

# 5.4. Assign Viewer Role (Optional)
gcloud projects add-iam-policy-binding resewrch-agent \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/viewer"
# Grants the Viewer role to the service account (optional but recommended for broader access).

echo "IAM roles assigned successfully."

# -------------------------------
# 6. Initialize App Engine
# -------------------------------
echo "Initializing App Engine in the 'us-central' region..."
gcloud app create --region=us-central
# Initializes App Engine in the 'us-central' region for the 'resewrch-agent' project.

# -------------------------------
# 7. Deploy a Minimal Version to Replace Unintended Files
# -------------------------------
# Ensure you have a minimal 'app.yaml' in your project directory.
# Example minimal 'app.yaml':
# runtime: python39
# handlers:
#   - url: /.*
#     script: auto

MINIMAL_VERSION="minimal-version"

echo "Deploying a minimal version '$MINIMAL_VERSION' to App Engine..."
gcloud app deploy app.yaml --version="$MINIMAL_VERSION" --quiet
# Deploys a minimal version of the application using 'app.yaml' with the version ID 'minimal-version', suppressing interactive prompts.

echo "Minimal version deployed successfully."

# -------------------------------
# 8. List All Deployed App Engine Versions
# -------------------------------
echo "Listing all deployed App Engine versions..."
gcloud app versions list
# Lists all deployed versions of the App Engine application, displaying service name, version ID, traffic split, deployment time, and serving status.

# -------------------------------
# 9. Delete Unwanted Deployed Versions
# -------------------------------
UNWANTED_VERSION="20241107t193539"

echo "Deleting unwanted App Engine version '$UNWANTED_VERSION'..."
gcloud app versions delete "$UNWANTED_VERSION" --quiet
# Deletes the specific App Engine version '20241107t193539' to remove unintended deployed files, suppressing interactive prompts.

echo "Unwanted version deleted successfully."

# -------------------------------
# 10. Verify Cloud Storage Bucket Access
# -------------------------------
STORAGE_BUCKET="staging.***.appspot.com"

echo "Verifying access to Cloud Storage bucket '$STORAGE_BUCKET'..."
gsutil ls "gs://$STORAGE_BUCKET/"
# Lists the contents of the Cloud Storage bucket to verify that the service account has the necessary access permissions.

# -------------------------------
# 11. (Optional) Disable App Engine and Related APIs
# -------------------------------
# Uncomment the following lines if you wish to disable App Engine and related services.

# echo "Disabling App Engine and related APIs..."
# gcloud services disable appengine.googleapis.com cloudbuild.googleapis.com storage.googleapis.com cloudresourcemanager.googleapis.com
# # Disables the App Engine Admin API, Cloud Build API, Cloud Storage API, and Cloud Resource Manager API.

# echo "App Engine and related APIs disabled successfully."

# -------------------------------
# 12. (Optional) Delete the Entire Google Cloud Project
# -------------------------------
# **Caution:** This action is irreversible and will delete all resources within the project.

# Uncomment the following lines if you intend to delete the entire project.

# echo "Deleting the entire Google Cloud project 'resewrch-agent'..."
# gcloud projects delete resewrch-agent --quiet
# # Deletes the entire Google Cloud project 'resewrch-agent', removing all associated resources and data irreversibly.

# echo "Google Cloud project 'resewrch-agent' deleted successfully."

# -------------------------------
# 13. (Optional) Implement Workload Identity Federation for Enhanced Security
# -------------------------------
# Uncomment and configure the following lines to set up Workload Identity Federation.

# echo "Creating Workload Identity Pool 'github-pool'..."
# gcloud iam workload-identity-pools create "github-pool" \
#   --project="resewrch-agent" \
#   --location="global" \
#   --display-name="GitHub Pool"
# # Creates a Workload Identity Pool named 'github-pool' in the 'resewrch-agent' project for federated identity management.

# echo "Creating OIDC Provider 'github-provider' within 'github-pool'..."
# gcloud iam workload-identity-pools providers create-oidc "github-provider" \
#   --project="resewrch-agent" \
#   --location="global" \
#   --workload-identity-pool="github-pool" \
#   --display-name="GitHub Provider" \
#   --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
#   --issuer-uri="https://token.actions.githubusercontent.com"
# # Creates an OpenID Connect (OIDC) provider named 'github-provider' within the 'github-pool' to enable GitHub Actions to authenticate with Google Cloud without using long-lived service account keys.

# echo "Workload Identity Federation setup completed successfully."

# -------------------------------
# 14. (Optional) Regenerate Service Account Key
# -------------------------------
# Uncomment the following lines if you need to regenerate the service account key.

# echo "Regenerating service account key for '$SERVICE_ACCOUNT_EMAIL'..."
# gcloud iam service-accounts keys create key.json \
#   --iam-account="$SERVICE_ACCOUNT_EMAIL"
# # Generates a new JSON key for the service account and saves it as 'key.json'.

# echo "New service account key created successfully."

# -------------------------------
# 15. (Optional) Remove Existing Service Account Keys
# -------------------------------
# Uncomment the following lines to delete an existing service account key.

# EXISTING_KEY_ID="your-key-id-here"

# echo "Deleting existing service account key '$EXISTING_KEY_ID'..."
# gcloud iam service-accounts keys delete "$EXISTING_KEY_ID" \
#   --iam-account="$SERVICE_ACCOUNT_EMAIL" \
#   --quiet
# # Deletes the specified service account key to enhance security.

# echo "Existing service account key deleted successfully."

# -------------------------------
# 16. (Optional) Remove Unwanted Files from Git Repository
# -------------------------------
# Uncomment and modify the following lines to remove unwanted files from the Git repository.

# FILE_TO_REMOVE="filename"

# echo "Removing '$FILE_TO_REMOVE' from Git tracking..."
# git rm --cached "$FILE_TO_REMOVE"
# git commit -m "Remove '$FILE_TO_REMOVE' from repository"
# git push origin master
# # Removes 'filename' from the Git repository's index without deleting it from the local file system.

# echo "File '$FILE_TO_REMOVE' removed from Git repository successfully."

# -------------------------------
# 17. (Optional) Clean Git History Using BFG Repo-Cleaner
# -------------------------------
# **Caution:** Rewriting Git history can have significant implications, especially for collaborative projects.

# Uncomment and modify the following lines to clean sensitive files from Git history.

# echo "Cleaning Git history to remove 'secret_key.txt'..."
# java -jar bfg.jar --delete-files secret_key.txt
# git reflog expire --expire=now --all && git gc --prune=now --aggressive
# git push --force
# # Uses BFG Repo-Cleaner to remove all instances of 'secret_key.txt' from the Git history, followed by garbage collection and a forced push.

# echo "Git history cleaned successfully."

# -------------------------------
# 18. (Optional) Browse the Deployed App Engine Application
# -------------------------------
# Uncomment the following lines to retrieve the URL of the deployed application.

# echo "Retrieving the URL of the deployed App Engine application..."
# APP_URL=$(gcloud app browse --no-launch-browser)
# echo "App Engine is serving at: $APP_URL"
# # Retrieves and displays the URL of the deployed App Engine application without opening it in a web browser.

# -------------------------------
# 19. (Optional) Validate Current gcloud Configuration
# -------------------------------
# Uncomment the following lines to display the current gcloud configuration.

# echo "Displaying current gcloud configuration..."
# gcloud config list
# # Displays the current configuration settings for gcloud, including the active project and account details.

# -------------------------------
# 20. (Optional) Enable Command Tracing for Debugging
# -------------------------------
# Uncomment the following lines if you want to enable command tracing during deployment for detailed logs.

# echo "Deploying to App Engine with enhanced logging..."
# set -x  # Enable command tracing
# gcloud app deploy --quiet --verbosity=debug
# set +x  # Disable command tracing
# # Deploys the application to App Engine with suppressed prompts and enhanced debug-level logging for detailed deployment insights.

# -------------------------------
# End of Script
# -------------------------------

echo "App Engine setup and deployment script executed successfully."








#Setup GCP Emulators

Certainly! Here's a comprehensive setup documentation for your local development environment, mimicking the Google Cloud setup for your Flask application with Firestore, Cloud Storage, and Cloud Functions:

# Local Development Setup Documentation

## Prerequisites

1. Python 3.7 or higher
2. Node.js and npm
3. Google Cloud SDK
4. Firebase CLI

## Step 1: Environment Setup

1. Create a new directory for your project:
   ```
   mkdir my_gcp_flask_project
   cd my_gcp_flask_project
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install required Python packages:
   ```
   pip install flask google-cloud-firestore google-cloud-storage google-cloud-pubsub
   ```

## Step 2: Google Cloud Project Setup

1. Create a new Google Cloud Project (or use an existing one)
2. Enable Firestore, Cloud Storage, and Pub/Sub APIs in your Google Cloud Console

## Step 3: Local Emulator Setup

1. Install Firebase CLI:
   ```
   npm install -g firebase-tools
   ```

2. Log in to Firebase:
   ```
   firebase login
   ```

3. Initialize Firebase in your project:
   ```
   firebase init
   ```
   Select Firestore and emulators when prompted.

4. Install the Pub/Sub emulator:
   ```
   gcloud components install pubsub-emulator
   gcloud components update
   ```

## Step 4: Configuration

1. Create a `.env` file in your project root:
   ```
   GOOGLE_CLOUD_PROJECT=your-project-id
   FIRESTORE_EMULATOR_HOST=localhost:8080
   PUBSUB_EMULATOR_HOST=localhost:8085
   GCS_BUCKET_NAME=your-bucket-name
   USE_MOCK_STORAGE=true
   ```

2. Create a `config.py` file to load these environment variables.

## Step 5: Application Code

1. Create `main_app.py` for your Flask application:
   ```python
   from flask import Flask, request
   from google.cloud import pubsub_v1
   import os
   import json

   app = Flask(__name__)

   # Pub/Sub setup
   publisher = pubsub_v1.PublisherClient()
   topic_path = publisher.topic_path(os.getenv('GOOGLE_CLOUD_PROJECT'), 'articles-topic')

   @app.route('/create_article', methods=['POST'])
   def create_article():
       # Your article creation logic here
       article_id = "generated-id"  # Replace with actual ID generation
       
       # Publish message to Pub/Sub
       message = json.dumps({'article_id': article_id}).encode('utf-8')
       future = publisher.publish(topic_path, message)
       
       return {'status': 'success', 'message': f'Article created and processing initiated. Message ID: {future.result()}'}

   if __name__ == '__main__':
       app.run(debug=True)
   ```

2. Create `local_function.py` as shown in the previous response.

3. Create `db_manager.py` for database operations (as shown in previous responses).

## Step 6: Running the Application

1. Start the Firestore emulator:
   ```
   firebase emulators:start --only firestore
   ```

2. In a new terminal, start the Pub/Sub emulator:
   ```
   gcloud beta emulators pubsub start
   ```

3. In another terminal, set environment variables and run your Flask app:
   ```
   source .env  # On Windows, use: set -a; . .env; set +a
   python main_app.py
   ```

4. In a fourth terminal, run your local Cloud Function emulator:
   ```
   source .env  # On Windows, use: set -a; . .env; set +a
   python local_function.py
   ```

## Step 7: Testing

1. Use tools like Postman or curl to send requests to your Flask app:
   ```
   curl -X POST http://localhost:5000/create_article -H "Content-Type: application/json" -d '{"title":"Test Article","content":"This is a test."}'
   ```

2. Check the logs in your `local_function.py` terminal to see if the message was processed.

3. Verify data in the Firestore emulator using the Firebase Console.

## Step 8: Cleanup

When you're done developing:

1. Stop all running processes (Flask app, local_function.py, emulators)
2. Deactivate your virtual environment:
   ```
   deactivate
   ```

## Additional Notes

- Replace mock implementations with real ones when deploying to Google Cloud.
- Always test in a staging environment before deploying to production.
- Keep your `.env` file and any credential files out of version control.

This setup allows you to develop and test your Google Cloud-based Flask application locally, using emulators and mocks to simulate the cloud environment. Remember to adjust configurations and implementations as necessary when moving to the actual Google Cloud environment.