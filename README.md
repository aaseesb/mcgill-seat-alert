# McGill Seat Alert

An automated tool to check course availability at McGill University and send notifications when courses become available.

> This project is a fork of the original [McGill Seat Alert](https://github.com/hanzili/mcgill-seat-alert) by [hanzili](https://github.com/hanzili), with modifications to support:
> - Optional filtering for specific CRNs
> - Updated for the current McGill VSB course selection page

## Description

This script automatically checks the availability of courses at McGill University.
It supports:
- Monitoring multiple courses in a single page load
- Optional filtering for specific CRNs per course
- Notifications when sections have open seats

This script automatically checks the availability of specified courses at McGill University using GitHub Actions. When a course becomes available, it sends a notification via Pushover.

### Automation via GitHub Actions
- The workflow runs automatically every 10 minutes to monitor course availability.
- This acts as a lightweight CI/CD process, letting you receive notifications without manually running the script.

## Setup

1. Fork this repository to your GitHub account.

2. Set up Pushover:
   - Create a Pushover account at https://pushover.net/
   - Create a new application in Pushover to get an API token
   - Note down your User Key and API Token

3. Set up GitHub Secrets:
   - Go to your forked repository on GitHub
   - Navigate to Settings > Secrets and variables > Actions
   - Add two new repository secrets:
     - `PUSHOVER_USER_KEY`: Your Pushover User Key
     - `PUSHOVER_API_TOKEN`: Your Pushover API Token

4. Configure courses:
   - Edit the `config.json` file in the repository:
     ```json
     {
         "courses": [
              { "code": "COURSE1", "crns": ["CRN1", "CRN2"] },
              { "code": "COURSE2" }
           ],
         "term": "YYYYMM"
     }
     ```
   - Replace `"COURSE1"`, `"COURSE2"` with the courses you want to check
   - CRNs are optional per course. If omitted, all sections of that course are monitored
   - Set the `"term"` to the desired semester (e.g., "202409" for Fall 2024, "202601" for Winter 2026)

5. Enable GitHub Actions:
   - Go to the "Actions" tab in your forked repository
   - You should see the "Check Course Availability" workflow
   - Enable the workflow if it's not already enabled

## Usage

Once set up, the GitHub Action will run automatically every 10 minutes to check course availability. You can also manually trigger the workflow:

1. Go to the "Actions" tab in your repository
2. Select the "Check Course Availability" workflow
3. Click "Run workflow"

You will receive a Pushover notification when any of your specified courses become available.

## Customization

- To change the check frequency, edit the cron schedule in `.github/workflows/course_check.yml`
- To modify the script behavior, edit `register.py`

## Disclaimer

This tool is for educational purposes only. The user is responsible for any consequences of using this script, including potential violations of McGill University's registration policies.
