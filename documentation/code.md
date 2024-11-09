# Initialize git repositories
git init

# virtual environment
python -m venv clean_scrape_gcp
source clean_scrape_gcp/bin/activate

# Setup Local Environemnt
pip install

# Create Branch
git checkout -b feature-branch
git add app.py
git commit -m "Add about page route"
git checkout main
git merge feature-branch
git branch -d feature-branch


# Add github project
git remote add origin https://github.com/bdavidriggins/clean_scrape_gcp.git
git push -u origin maaster



# Push to github
git add .
git commit -m "Trigger deployment to App Engine"
git push origin master



# Use Google Cloud emulators:
Google provides emulators for several services that you can run locally: 

a) Firestore Emulator: 

    Install the Firebase CLI: 
    npm install -g firebase-tools
    
    Start the emulator: 
    firebase emulators:start --only firestore --project=local-test-project

b) Pub/Sub Emulator: 

    Install the Google Cloud SDK
    Start the emulator: 
    gcloud beta emulators pubsub start




set GOOGLE_APPLICATION_CREDENTIALS="/home/bdavidriggins/Projects/clean_scrape_gcp/service-account-key.json"


# # FFMpeg
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz
tar -xf ffmpeg-release-i686-static.tar.xz --strip-components=1 --wildcards '*/ffmpeg' -C .
chmod +x ffmpeg  # Ensure the binary is executable
