import logging
from logging.handlers import RotatingFileHandler
import os
from typing import List
import dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials  # type: ignore
import requests

dotenv.load_dotenv()

LOG_MODE = logging.ERROR

# Constants
LOG_FILE = "./pittcsc_simplify.log"
MAX_FILE_SIZE = 128 * 1024 * 1024  # Max size in bytes (128 MB)
BACKUP_COUNT = 5  # Number of backup files to keep

# Formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# File handler setup with rotation
file_handler = RotatingFileHandler(
    LOG_FILE,
    mode="a",
    maxBytes=MAX_FILE_SIZE,
    backupCount=BACKUP_COUNT,
    encoding=None,
    delay=False,
)
file_handler.setFormatter(formatter)
file_handler.setLevel(LOG_MODE)

# Console handler setup
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(LOG_MODE)

# Logger setup
logger = logging.getLogger("")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Constants
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = "Job Application Tracker"
EXCLUDED_LOCATIONS = [
    "canada",
    "toronto",
    "montreal",
    "ontario",
    "london",
    "--------",
]
FOUND_SOURCE_DEFAULT = "Direct Application"

INCLUDED_TERMS = [
    "Spring 2025",
    "Summer 2025", # this is included because some jobs are mistakenly tagged as Summer 2025
    "Fall 2025",
    "Winter 2025",
    "Spring 2026",
    "Summer 2026",
    "Fall 2026",
    "Winter 2026",
    "Spring 2027",
    "Summer 2027",
    "Fall 2027",
    "Winter 2027",
    "Spring 2028",
    "Summer 2028",
    "Fall 2028",
    "Winter 2028",
]


# Authentication
def authenticate_gspread() -> gspread.Client:  # type: ignore
    """
    Authenticate with the Google Sheets API using OAuth2 credentials.
    Returns:
        gspread.Client: Authenticated Google Sheets client.
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(  # type: ignore
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS_CUSTOM"), scope  # type: ignore
    )
    client = gspread.authorize(creds)  # type: ignore
    logging.info("Google Spreadsheet authenticated.")
    return client


# Fetch job postings from URL
def fetch_job_postings(url: str) -> List[List[str]]:
    """
    Fetch job postings from a given URL.
    Args:
        url (str): The URL to fetch job postings from.
    Returns:
        List[List[str]]: List of job postings.
    """
    response = requests.get(url, timeout=10)
    data = response.json()

    job_postings = [
        [
            job["company_name"],
            " ".join(job["locations"]),
            job["title"],
            job["url"]
            .replace("?utm_source=Simplify&ref=Simplify", "")
            .replace("&utm_source=Simplify&ref=Simplify", ""),
            job["terms"],
            job["active"],
            job["date_posted"]
        ]
        for job in data
    ]

    print(len(job_postings))
    return job_postings


# Check if location is excluded
def exclude_location(location: str) -> bool:
    """
    Check if a location should be excluded based on predefined exclusions.
    Args:
        location (str): The location to check.
    Returns:
        bool: True if the location should be excluded, False otherwise.
    """
    return any(
        excluded_location in location.lower()
        for excluded_location in EXCLUDED_LOCATIONS
    )


def check_terms(terms: list[str]) -> bool:
    """
    Check if a job posting should be excluded based on predefined terms.
    Args:
        terms (list[str]): The terms to check.
    Returns:
        bool: True if the terms should be excluded, False otherwise.
    """
    return any(included_term in terms for included_term in INCLUDED_TERMS)


# Process and update job postings
def process_job_postings(sheet: gspread.Worksheet, jobs: List[List[str]]) -> List[List[str]]:  # type: ignore
    """
    Process and update job postings in the Google Sheet.
    Args:
        sheet (gspread.Worksheet): The Google Sheet to update.
        jobs (List[List[str]]): The list of job postings to process.
    """
    existing_jobs = sheet.get_all_values()
    existing_app_links = [job[5] for job in existing_jobs]  # type: ignore

    jobs_to_add = []

    excluded_counter = {}

    for job in jobs:
        company, location, role, appLink, terms, active , date_posted = job # type: ignore
        if not active:
            excluded_counter["inactive"] = excluded_counter.get("inactive", 0) +1
            logging.info(
                f"Excluded job posting from {company} in {location} for inactivity."
            )
            continue
        if exclude_location(location):
            excluded_counter["location"] = excluded_counter.get("location", 0) +1
            logging.info(
                f"Excluded job posting from {company} in {location} for location."
            )
            continue
        if not check_terms(terms):
            excluded_counter["terms"] = excluded_counter.get("terms", 0) +1
            logging.info(
                f"Excluded job posting from {company} in {location} for terms."
            )
            continue
        if terms == "Summer 2024":
            # temporary fix for jobs so we will ignore jobs posted before 
            if int(date_posted) < 1710797957:
                excluded_counter["date_posted"] = excluded_counter.get("date_posted", 0) +1
                logging.info(
                    f"Excluded job posting from {company} in {location} for date posted."
                )
                continue
        if appLink in existing_app_links:
            excluded_counter["duplicate"] = excluded_counter.get("duplicate", 0) +1
            logging.info(
                f"Excluded job posting from {company} in {location} for duplicate."
            )
            continue
        
        excluded_counter["added"] = excluded_counter.get("added", 0) +1
        logging.info(f"Adding new job posting from {company} in {location}.")
        # Update the sheet with the new job posting
        jobs_to_add.append(job)
    
    print(excluded_counter)
    return jobs_to_add


def write_to_sheet(sheet: gspread.Worksheet, jobs: List[List[str]]) -> None:
    """
    Write job postings to the Google Sheet.
    Args:
        sheet (gspread.Worksheet): The Google Sheet to write to.
        jobs (List[List[str]]): The list of job postings to write.
    """
    existing_data = sheet.get_all_values()
    next_row = len(existing_data) + 1
    new_jobs = []

    for job in jobs:
        row = ["" for _ in range(15)]
        # format of row in sheet is ["", company, "", location,FOUND_SOURCE_DEFAULT, appLink, role, terms]
        row[1] = job[0]
        row[3] = job[1]
        row[4] = FOUND_SOURCE_DEFAULT
        row[5] = job[3]
        row[6] = job[2]
        row[7] = " ".join(job[4])
        new_jobs.append(row)

    if new_jobs:
        range_to_update = f"A{next_row}:O{next_row + len(new_jobs) - 1}"  # type: ignore
        sheet.update(
            new_jobs, range_to_update, value_input_option="USER_ENTERED"  # type: ignore
        )  # type: ignore
        logging.info(
            f"Updated Google Spreadsheet with {len(new_jobs)} new rows."
        )  # type: ignore


# Main function
def main():
    """
    Main function to orchestrate the job application tracker.
    """
    client = authenticate_gspread()
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    jobs = fetch_job_postings(
        "https://raw.githubusercontent.com/SimplifyJobs/Summer2025-Internships/dev/.github/scripts/listings.json"
    )
    jobs_to_add = process_job_postings(sheet, jobs)
    write_to_sheet(sheet, jobs_to_add)


if __name__ == "__main__":
    main()
