from google.cloud import logging
from google.cloud.logging_v2 import Client
import datetime

# Initialize the logging client
client = Client()

# Set up your filter (modify as needed)
# For example, to fetch ERROR logs from a specific resource:
filter_str = '''
timestamp >= "{start_time}"
AND logName = "projects/{project_id}/logs/{log_id}"
AND severity >= ERROR
'''.format(
    start_time=(datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat("T") + "Z",
    project_id='resewrch-agent'
)

# Fetch the entries
entries = client.list_entries(filter_=filter_str, order_by=logging.DESCENDING)

# Open a file to write logs
with open('logs.txt', 'w') as log_file:
    count = 0
    for entry in entries:
        log_file.write(f"{entry.payload}\n")
        count += 1
        if count >= 1000:
            break

print(f"Saved {count} log entries to logs.txt")
