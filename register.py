from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from tenacity import retry, stop_after_attempt, wait_fixed
import os
import requests
import json
import argparse
import logging
import traceback

# Use environment variables for credentials
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
EMAIL = os.environ["ALERT_EMAIL"]

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_config():
    # Parse command-line arguments and load configuration from JSON file
    parser = argparse.ArgumentParser(description='Check course availability at McGill')
    parser.add_argument('--config', default='config.json', help='Path to the configuration file')
    args = parser.parse_args()

    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        logging.error(f"Config file not found: {args.config}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error reading config file: {args.config}")
        return None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def load_webpage(driver, url):
    # Load webpage with retry mechanism in case of failure
    driver.get(url)
    logging.info("Webpage {url} loaded successfully.")

def send_email(recipient, subject, body):
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": "Seat Alert <onboarding@resend.dev>",
                "to": [recipient],
                "subject": f"{subject}",
                "html": f"{body}"
            }
        )
        response.raise_for_status(f"Email sent successfully to {recipient}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send email to {recipient}: {e}")
        return False

def scroll_to_element(driver, element):
    # Scroll to the specified element to ensure it's in view
    actions = ActionChains(driver)
    actions.move_to_element(element).perform()

def get_course_availability(driver, course, target_crns=None):
    # Check availability for a specific course
    try:
        logging.info(f"Searching for course: {course}")
        wait = WebDriverWait(driver, 20)
        course_box = wait.until(
            EC.presence_of_element_located((By.XPATH, f"//div[contains(@class, 'course_box') and contains(., '{course}')]"))
        )
        logging.info(f"Found course box for: {course}")
        scroll_to_element(driver, course_box)
        
        sections = course_box.find_elements(By.XPATH, ".//div[contains(@class, 'selection_row')]")
        logging.info(f"sections {sections}")
        logging.info(f"Found {len(sections)} sections for course: {course}")
        
        available_sections = []
        
        for section in sections:
            try:
                if "Lec" in section.text:
                    # Extract CRN and check for open seats or waitlist availability
                    crn = section.find_element(By.XPATH, ".//span[@class='crn_value']").text
                    logging.info(f"crns {crn}")

                    # filter crns
                    if target_crns and crn not in target_crns:
                        continue
                    
                    seats_element = section.find_element(By.XPATH, ".//span[contains(@class, 'leftnclear') and contains(., 'Seats:')]")
                    if "Full" not in seats_element.text:
                        available_sections.append((crn, "Open seats"))
                        continue
                    
                    waitlist_element = section.find_element(By.XPATH, ".//span[contains(@class, 'legend_waitlist')]")
                    if "None" not in waitlist_element.text:
                        available_sections.append((crn, "Waitlist"))
            except NoSuchElementException as e:
                logging.warning(f"Error processing section in {course}: {str(e)}")
        
        return available_sections
    except TimeoutException:
        pass
        logging.error(f"Timeout while searching for course: {course}")
    except Exception as e:
        pass
        logging.error(f"Error checking availability for {course}: {str(e)}")
    return []

def setup_driver():
    # Configure and initialize Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=800,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def perform_web_task():
    logging.info("Starting web task...")
    
    # Load configuration
    config = get_config()
    if not config:
        return

    raw_courses = config.get('courses', [])
    courses = normalize_courses(raw_courses)
    term = config.get('term', '202701')  # Default to winter 2027 if not specified

    if not courses:
        logging.info("No courses to check. Exiting.")
        return

    logging.info(f"Checking availability for courses: {courses}")
    
    driver = setup_driver()
    
    try:
        # Check availability for each course
        logging.info("Checking course availability...")

        # Retrieve webpage with all courses
        url = build_url(courses, term)
        load_webpage(driver, url)

        # Extract availability
        available_courses = {}
        for course in courses:
            code = course["code"]
            target_crns = course["crns"]

            available_sections = get_course_availability(driver, code, target_crns)

            if available_sections:
                available_courses[code] = available_sections
                logging.info(f"Course {course} is available:")

                for crn, availability_type in available_sections:
                    logging.info(f"  CRN: {crn}, Availability: {availability_type}")
            else:
                logging.info(f"Course {course} is not available")

        # Send notification if any courses are available
        if available_courses:
            num_sections = sum(len(sections) for sections in available_courses.values())
            email_subject = "{} Course Section Available"
            email_body = """
                <h2>Course Availability Alert</h2>
                <p>The following sections are available:</p>
                <ul>
            """
            for code, sections in available_courses.items():
                email_body += f"<li><strong>{code}<li><strong>"
                for crn, availability_type in sections:
                    email_body += f"<li>  • CRN: {crn}: {availability_type}</li>"
                email_body += "</ul></li>"
            email_body += "</ul>"
            send_email(EMAIL, email_subject, email_body)
        else:
            logging.info("No courses are currently available.")

        logging.info("All courses have been checked for availability.")
    except Exception as e:
        logging.error(f"An error occurred during web task: {str(e)}")
        logging.debug("Traceback:\n%s", traceback.format_exc())
    finally:
        driver.quit()

def build_url(courses, term):
    base = (
        f"https://vsb.mcgill.ca/criteria.jsp?"
        f"access=0&lang=en&tip=1&page=criteria&scratch=0&advice=0&legend=1"
        f"&term={term}&sort=none&filters=iiiiiiiiii"
        "&bbs=&ds=&cams=DISTANCE_DOWNTOWN_MACDONALD_OFF-CAMPUS"
        "&locs=any&isrts=any&ses=any&pl=&pac=1"
    )

    for i, course in enumerate(courses):
        base+=f"&course_{i}_0={course['code']}"

    return base

def normalize_courses(raw_courses):
    normalized = []

    for course in raw_courses:
        if isinstance(course, str):
            normalized.append({"code": course, "crns": None})

        elif isinstance(course, dict):
            normalized.append({
                "code": course.get("code"),
                "crns": course.get("crns")
            })
    
    return normalized

if __name__ == "__main__":
    perform_web_task()
