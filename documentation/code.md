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



