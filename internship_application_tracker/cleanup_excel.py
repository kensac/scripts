import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class JobURLChecker:
    """
    A modular class for checking job URLs to determine if they are expired.
    
    You can customize:
      - verify_content: Whether to look inside page content for keywords.
      - retries: How many times to retry a request in case of transient errors.
      - max_workers: Number of threads for concurrent URL checking.
      - delay: Optional delay between requests (useful to avoid rate limiting).
    """

    def __init__(
        self,
        verify_content: bool = False,
        retries: int = 0,
        max_workers: int = 10,
        delay: float = 0.0,
    ):
        self.verify_content = verify_content
        self.retries = retries
        self.max_workers = max_workers
        self.delay = delay
        self.session = requests.Session()
        # If desired, you could mount a custom HTTPAdapter here to control retries, backoff, etc.

    def check_url(self, url: str) -> Dict[str, Any]:
        """
        Checks if the given URL appears to be expired or invalid.
        First tries a HEAD request for speed, then (if needed) a GET request.
        Optionally examines page content for keywords that indicate expiration.
        """
        url = url.strip()
        if not url:
            return {
                "url": "",
                "status": None,
                "expired": True,
                "reason": "Empty or invalid URL",
            }

        result: Dict[str, Any] = {"url": url, "status": None, "expired": False, "reason": ""}

        # --- First try: HEAD request ---
        try:
            head_response = self.session.head(url, timeout=5)
            result["status"] = head_response.status_code

            if head_response.status_code == 404:
                result["expired"] = True
                result["reason"] = "404 Not Found (HEAD)"
                return result

            if 400 <= head_response.status_code < 600:
                result["expired"] = True
                result["reason"] = f"Error {head_response.status_code} (HEAD)"
                return result

        except requests.exceptions.RequestException as exc:
            logging.debug(f"HEAD request failed for {url}: {exc}")

        # --- Second try: GET request ---
        try:
            response = self.session.get(url, timeout=10)
            result["status"] = response.status_code

            # Handle 429 errors if necessary
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 60
                logging.warning(f"429 received for {url}. Waiting for {wait_time} seconds.")
                time.sleep(wait_time)

            if response.status_code == 404:
                result["expired"] = True
                result["reason"] = "404 Not Found (GET)"
            elif 400 <= response.status_code < 600 and response.status_code != 429:
                result["expired"] = True
                result["reason"] = f"HTTP {response.status_code} (GET)"
            else:
                if self.verify_content:
                    keyword_list = [
                        "job not found",
                        "position has been filled",
                        "no longer accepting applications",
                        "job expired",
                        "sorry, this job has expired",
                        "the page you are looking for doesn't exist.",
                    ]
                    page_text_lower = response.text.lower()
                    if any(keyword in page_text_lower for keyword in keyword_list):
                        keyword_found = next(
                            keyword for keyword in keyword_list if keyword in page_text_lower
                        )
                        result["expired"] = True
                        result["reason"] = f"Page content indicates expired job: {keyword_found}"

                    # Provider-specific checks
                    if "workday" in url.lower():
                        soup = BeautifulSoup(response.text, "html.parser")
                        meta_tag = soup.find("meta", {"name": "description", "property": "og:description"})
                        if not meta_tag or not meta_tag.get("content", "").strip():
                            result["expired"] = True
                            result["reason"] = "Workday page missing meta og:description content"
                    if "greenhouse" in url.lower():
                        if "?error=true" in response.url:
                            result["expired"] = True
                            result["reason"] = "Greenhouse page indicates expired job"
                        elif url != response.url:
                            result["expired"] = True
                            result["reason"] = "Greenhouse page redirected"
                    if "jobvite" in url.lower():
                        if "?error=404" in response.url:
                            result["expired"] = True
                            result["reason"] = "Jobvite page indicates expired job"

        except requests.exceptions.ReadTimeout:
            result["expired"] = False
            result["reason"] = "Read Timeout (uncertain status)"
        except requests.exceptions.RequestException as exc:
            result["expired"] = True
            result["reason"] = f"Request Error: {exc}"

        return result

    def _single_url_task(self, url: str) -> Dict[str, Any]:
        """
        Handles a single URL, retrying if necessary.
        """
        attempts = 0
        last_result: Optional[Dict[str, Any]] = None

        while attempts <= self.retries:
            if self.delay:
                time.sleep(self.delay)
            result = self.check_url(url)
            if result.get("status") is not None:
                return result
            last_result = result
            attempts += 1

        return last_result or {
            "url": url,
            "status": None,
            "expired": True,
            "reason": "Max retries exceeded",
        }

    def process_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Processes a list of URLs concurrently while preserving the order of the input.
        Prints periodic progress updates including an estimated time remaining.
        """
        total_urls = len(urls)
        results: List[Optional[Dict[str, Any]]] = [None] * total_urls  # Preallocate list for ordered results.
        completed_count = 0
        start_time = time.time()
        last_print_time = start_time
        print_interval = 5  # seconds between progress prints

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map each future to its input index.
            future_to_index = {
                executor.submit(self._single_url_task, url): index
                for index, url in enumerate(urls)
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as exc:
                    url = urls[index]
                    logging.error(f"{url} generated an exception: {exc}")
                    results[index] = {
                        "url": url,
                        "status": None,
                        "expired": True,
                        "reason": f"Unhandled exception: {exc}",
                    }
                completed_count += 1
                current_time = time.time()
                if current_time - last_print_time >= print_interval:
                    elapsed = current_time - start_time
                    average_time = elapsed / completed_count if completed_count else 0
                    remaining_count = total_urls - completed_count
                    estimated_remaining = average_time * remaining_count
                    logging.info(
                        f"Progress: {completed_count}/{total_urls} completed. "
                        f"Estimated time remaining: {estimated_remaining:.2f} seconds."
                    )
                    last_print_time = current_time

        total_elapsed = time.time() - start_time
        logging.info(f"Completed processing {total_urls} URLs in {total_elapsed:.2f} seconds.")
        # Now all results are in the same order as the input.
        return results  # type: ignore

    def save_results_to_csv(self, results: List[Dict[str, Any]], filepath: str) -> None:
        """
        Saves results to a CSV file with a header row.
        The output contains URL, HTTP status, expired flag, reason, and sheet text.
        """
        output_lines: List[List[str]] = []
        for r in results:
            url: str = r.get("url", "")
            status: int = r.get("status", 0)
            expired: bool = r.get("expired", False)
            reason: str = r.get("reason", "")
            sheet_text: str = "No Longer Interested" if expired else ""
            row: List[str] = [url, str(status), str(expired), reason, sheet_text]
            output_lines.append(row)

        # Insert header row.
        output_lines.insert(0, ["URL", "Status", "Expired", "Reason", "Sheet Text"])

        with open(filepath, "w", encoding="utf-8") as f:
            for row in output_lines:
                f.write(", ".join(row) + "\n")
        logging.info(f"Results written to {filepath}")

    def run(self, urls: List[str], output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Runs the URL checks on the given list of URLs and optionally writes the results
        to a CSV file. Returns the list of result dictionaries.
        """
        results = self.process_urls(urls)
        if output_file:
            self.save_results_to_csv(results, output_file)
        return results


# ----------------------------
# Example usage (without command-line args)
# ----------------------------

def main():
    # Read URLs from a file (one URL per line)
    url_file = "urls.txt"
    with open(url_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Create an instance of the checker.
    checker = JobURLChecker(
        verify_content=True,  # parse the page for expiration keywords
        retries=1,            # retry once on transient failures
        max_workers=5,        # use 5 threads concurrently
        delay=0.5             # add a half-second delay between requests (helps avoid 429 errors)
    )

    # Run the URL checks and save the results to a CSV file.
    results = checker.run(urls, output_file="output.csv")

    # For demonstration, write the sheet text ("No Longer Interested" for expired jobs) to an output file.
    with open("output.txt", "w", encoding="utf-8") as f:
        for r in results:
            sheet_text = "No Longer Interested" if r.get("expired", False) else ""
            f.write(sheet_text + "\n")


if __name__ == "__main__":
    main()
