import csv
import subprocess
from datetime import datetime, timedelta
import os

csv_file_path = '/Users/heltai/dealii-X/dealii-X/doc/project/deliverables.csv'
repo = 'dealii-X/dealii-X'
project_start_date = datetime(2024, 10, 1)

# Ensure the script does not open "less"
os.environ['PAGER'] = ''


def create_milestone(title, description, due_on):
    command = [
        'gh', 'api', '--method', 'POST',
        '-H', 'Accept: application/vnd.github.v3+json',
        f'/repos/{repo}/milestones',
        '-f', f'title={title}',
        '-f', 'state=open',
        '-f', f'description={description}',
        '-f', f'due_on={due_on}'
    ]
    subprocess.run(command, check=True)


def calculate_due_date(months):
    return project_start_date + timedelta(days=months*30)


with open(csv_file_path, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        title = row['Number'] + ": " + row['Deliverable name']
        description = row['Short description']
        months = int(row['Delivery date'].replace('M', ''))
        due_date = calculate_due_date(months).isoformat() + 'Z'
        create_milestone(title, description, due_date)
