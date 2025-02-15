import csv
import subprocess

csv_file_path = '/Users/heltai/dealii-X/dealii-X/doc/project/participants.csv'
repo = 'dealii-X/dealii-X'


def create_label(name, description):
    command = [
        'gh', 'api', '--method', 'POST',
        '-H', 'Accept: application/vnd.github.v3+json',
        f'/repos/{repo}/labels',
        '-f', f'name={name}',
        '-f', f'description={description}'
    ]
    subprocess.run(command, check=True)


with open(csv_file_path, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        name = row['Participant Short Name']
        description = row['Participant Name']
        create_label(name, description)
