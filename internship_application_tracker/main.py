# type: ignore

import os
import dotenv
import requests
import re
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials

dotenv.load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='./job_application_tracker.log', filemode='a')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# Constants
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = "Job Application Tracker"
FOUND_SOURCE_DEFAULT = "Direct Application"
COLUMNS = [
    "blank",
    "company",
    "size",
    "location",
    "foundSource",
    "appLink",
    "role",
    "requirements",
    "recruiter",
    "connection1",
    "connection2",
    "documents",
    "dateApplied",
    "status",
    "comments",
]
EXCLUDED_LOCATIONS = ["canada", "toronto", "montreal", "ontario", "london", "--------"]

def authenticate_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_CUSTOM"), scope) # type: ignore
    client = gspread.authorize(creds)  # type: ignore
    logging.info("Google Spreadsheet authenticated.")
    return client

def fetch_job_postings(url: str) -> list[list[str]]:
    response = requests.get(url)
    lines = response.text.split("\n")
    job_postings: list[list[str]] = []
    read_table = False

    for line in lines:
        if "TABLE_START" in line:
            read_table = True
        elif "TABLE_END" in line:
            read_table = False
        elif read_table and line.startswith("|") and line.endswith("|"):
            columns = line.strip("|").split("|")
            columns = [col.strip() for col in columns]
            if len(columns) > 1 and "🔒" not in columns:
                job_postings.append(columns)
    logging.info(f"Fetched job postings from {url}")
    return job_postings

def parse_job_data(job: list[str], config: dict) -> dict:
    job_info = {}
    for key, index in config["columnMapping"]["readColumns"].items():
        data = job[index]
        regex = config["columnMapping"]["regex"].get(key, None)
        if regex:
            match = re.search(regex, data)
            job_info[key] = match.group(1) if match else data
        else:
            job_info[key] = data
    logging.info(f"Parsed job data for {job_info.get('company')}")
    return job_info

def is_excluded_location(location):
    excluded = any(excluded.lower() in location.lower() for excluded in EXCLUDED_LOCATIONS)
    if excluded:
        logging.info(f"Excluded location found: {location}")
    return excluded

def passes_keyword_filter(job_info, keyword_filter):
    if keyword_filter["enabled"]:
        match = any(
            keyword.lower() in job_info["role"].lower()
            for keyword in keyword_filter["keywords"]
        )
        if not match:
            logging.info(f"Keyword filter failed for role: {job_info['role']}")
        return match
    return True

def update_job_postings(config):
    client = authenticate_gspread()
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    existing_data = sheet.get_all_values()
    existing_links = [row[5] for row in existing_data if len(row) > 5]

    job_postings = fetch_job_postings(config["githubUrl"])
    next_row = len(existing_data) + 1
    new_rows = []

    for job in job_postings:
        job_info = parse_job_data(job, config)
        new_link = job_info["appLink"] not in existing_links
        valid_location = not is_excluded_location(job_info["location"])
        keyword_match = passes_keyword_filter(job_info, config["keywordFilter"])

        if new_link and valid_location and keyword_match:
            row = ["" for _ in range(15)]
            row[1] = job_info["company"]
            row[3] = job_info["location"]
            row[4] = FOUND_SOURCE_DEFAULT
            row[5] = job_info["appLink"]
            row[6] = job_info["role"]
            new_rows.append(row)

    if new_rows:
        range_to_update = f"A{next_row}:O{next_row + len(new_rows) - 1}"
        sheet.update(new_rows, range_to_update, value_input_option="USER_ENTERED") # type: ignore
        logging.info(f"Updated Google Spreadsheet with {len(new_rows)} new rows.")


configs = [
    {
        "githubUrl": "https://raw.githubusercontent.com/SimplifyJobs/Summer2024-Internships/dev/README-Off-Season.md",
        "columnMapping": {
            "readColumns": {"company": 0, "location": 2, "appLink": 4, "role": 1},
            "regex": {"company": r"\[([^\]]+)\]", "appLink": r'href="([^"]+)"'},
        },
        "keywordFilter": {
            "enabled": False,
            "keywords": [""],
        },
    },
    {
        "githubUrl": "https://raw.githubusercontent.com/Ouckah/Summer2025-Internships/main/README.md",
        "columnMapping": {
            "readColumns": {"company": 0, "location": 2, "appLink": 3, "role": 1},
            "regex": {"company": r"([^|\n]+)", "appLink": r'href="([^"]+)"'},
        },
        "keywordFilter": {
            "enabled": False,
            "keywords": [""],
        },
    },
    {
        "githubUrl": "https://raw.githubusercontent.com/SimplifyJobs/Summer2024-Internships/dev/README.md",
        "columnMapping": {
            "readColumns": {"company": 0, "location": 2, "appLink": 3, "role": 1},
            "regex": {"company": r"\[([^\]]+)\]", "appLink": r'href="([^"]+)"'},
        },
        "keywordFilter": {"enabled": True, "keywords": ["2025", "fall"]},
    },
]


def main():
    for config in configs:
        update_job_postings(config)
    logging.info("Job posting update completed.")

if __name__ == "__main__":
    main()