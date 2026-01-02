Utilization App
The Utilization App is an end‑to‑end workflow for tracking employee utilization based on Timesheets.com  data. It:

pulls daily, employee‑level hours from the Timesheets public API

writes normalized records into a Supabase Postgres database

surfaces weekly utilization metrics through a Streamlit web app

This repo contains both the ETL job (run on a schedule via GitHub Actions) and the interactive dashboard used by the business.

Architecture overview
High‑level flow:

Timesheets API → ETL (Python)

A scheduled job (etl/dailyHoursProj.py) calls the Timesheets public API.

It retrieves project‑level daily hours for each employee.

Records are cleaned, normalized, and transformed into an “employee hours” dataset.

ETL → Supabase Postgres

The ETL writes/upserts rows into a Supabase Postgres table (employee_hours).

Existing records are updated based on record_id to avoid duplicates.

Supabase → Streamlit app

The Streamlit app (e.g. app/homePage.py) queries employee_hours.

It aggregates data into weekly utilization (hours / 40) per employee / team / time period.

Users can filter by date range, employee, project/customer, etc.

GitHub Actions → automation

A workflow (.github/workflows/dailyHours.yml) runs dailyHoursProj.py daily.

The job uses API and DB credentials injected via GitHub Secrets.

Repository structure
Adjust the file names/paths if your repo differs.

text
Utilization_App/
├─ app/
│  ├─ homePage.py         # Streamlit entry point
│  ├─ utils/
│  │  ├─ db.py            # DB connection/query utilities
│  │  └─ ...
├─ etl/
│  ├─ dailyHoursProj.py   # Timesheets → Supabase ETL job
│  └─ ...
├─ .github/
│  └─ workflows/
│     └─ dailyHours.yml   # GitHub Actions workflow to run ETL daily
├─ requirements.txt
├─ README.md
└─ ...
Data model
Source: Timesheets.com
The ETL pulls from:

Customer items API:
https://secure.timesheets.com/api/public/v1/items/customer

Project items API:
https://secure.timesheets.com/api/public/v1/items/project

Project customizable report API:
https://secure.timesheets.com/api/public/v1/report/project/customizable

Authentication is done via headers:

python
headers = {
    "accept": "application/json",
    "apikey": API_KEY,                 # TIMESHEETS_API_KEY
    "x-ts-authorization": API_TOKEN,   # TIMESHEETS_API_TOKEN
}
The ETL filters out internal/non‑billable customers and projects depending on the use case, e.g.:

excludes customers with name "Internal" or "Choose Customer"

optionally excludes projects with name "Client Non-billable Hours"

Target: Supabase Postgres
The ETL writes into an employee_hours table with columns like:

user_id

employee

customer_id

customer_name

project_id

project_name

hours

billable_hours

work_date (timestamp)

billable_flag

record_id (unique per Timesheets record, used for upserts)

Upsert logic (simplified):

sql
INSERT INTO employee_hours (...)
VALUES (...)
ON CONFLICT (record_id) DO UPDATE SET
  user_id        = EXCLUDED.user_id,
  employee       = EXCLUDED.employee,
  customer_id    = EXCLUDED.customer_id,
  customer_name  = EXCLUDED.customer_name,
  project_id     = EXCLUDED.project_id,
  project_name   = EXCLUDED.project_name,
  hours          = EXCLUDED.hours,
  billable_hours = EXCLUDED.billable_hours,
  work_date      = EXCLUDED.work_date,
  billable_flag  = EXCLUDED.billable_flag;
You can add the actual DDL as a section if you want (CREATE TABLE employee_hours (...)).

Local development
1. Clone the repo
bash
git clone https://github.com/<your-username>/Utilization_App.git
cd Utilization_App
2. Create and activate a virtual environment
bash
python -m venv venv
# Windows (PowerShell)
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
3. Install dependencies
bash
pip install --upgrade pip
pip install -r requirements.txt
4. Environment variables
The project relies on environment variables for:

Timesheets API authentication

Supabase Postgres password

Locally, you can use a .env file in the repo root (and python-dotenv) or system/user env vars.

Example .env:

ini
# Timesheets API
TIMESHEETS_API_KEY=your_timesheets_api_key_here
TIMESHEETS_API_TOKEN=your_timesheets_api_token_here

# Supabase
SUPABASE_PASSWORD=your_supabase_db_password_here
In dailyHoursProj.py, these are read via:

python
API_KEY = os.getenv("TIMESHEETS_API_KEY")
API_TOKEN = os.getenv("TIMESHEETS_API_TOKEN")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")
If you’re using load_dotenv(), mention where it’s called.

5. Running the ETL locally
From the etl directory (or repo root, depending on your imports):

bash
# From repo root
python etl/dailyHoursProj.py
The script will:

Fetch customer and project metadata.

Identify billable customers/projects.

Loop over a date range (last N days).

Call the Timesheets report endpoint per day.

Insert/upsert rows into employee_hours.

You’ll see log output like:

text
Fetching 01/02/2026...
Inserted 25 employee project rows for 01/02/2026.
Streamlit app
Running the app locally
From repo root (or app/ if that’s how you’ve structured imports):

bash
streamlit run app/homePage.py
This will:

start a local server (default at http://localhost:8501)

open your browser with the utilization dashboard

What the app shows
Customize this to match your actual UI, but generally:

Filters: date range, employee, customer, project, billable/all hours

KPIs: total hours, total billable hours, utilization % (billable / 40 per week), maybe by person/team

Tables/Charts:

weekly utilization by employee

project mix (which clients/engagements are driving hours)

time series view of billable vs non‑billable

You can embed screenshots here, for example:

markdown
![Utilization dashboard screenshot](./docs/images/utilization_dashboard.png)
GitHub Actions: daily ETL
The repo includes a workflow at .github/workflows/dailyHours.yml that runs the ETL on a schedule.

Workflow summary
Triggers:

daily at a specified UTC time (mapped to a US time zone)

manually via the Actions tab (workflow_dispatch)

Runner: ubuntu-latest

Steps:

Check out the repo

Set up Python

Install dependencies from requirements.txt

Export secrets into env vars

Run etl/dailyHoursProj.py

Example workflow (simplified):

yaml
name: Daily Hours Sync

on:
  schedule:
    - cron: "0 2 * * *"   # 2:00 AM UTC (8 PM CST)
  workflow_dispatch:

jobs:
  run-daily-hours:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run dailyHoursProj.py
        env:
          TIMESHEETS_API_KEY: ${{ secrets.TIMESHEETS_API_KEY }}
          TIMESHEETS_API_TOKEN: ${{ secrets.TIMESHEETS_API_TOKEN }}
          SUPABASE_PASSWORD: ${{ secrets.SUPABASE_PASSWORD }}
        run: |
          python etl/dailyHoursProj.py
Required GitHub Secrets
Set these at:

Repo → Settings → Secrets and variables → Actions

TIMESHEETS_API_KEY

TIMESHEETS_API_TOKEN

SUPABASE_PASSWORD

If you move more DB credentials/env into secrets, list them here too.

Error handling and rate limiting
The ETL includes basic error handling and rate‑limit safety:

Rate limiting:

safe_post() retries on rate‑limit responses and sleeps between attempts.

HTTP errors:

Non‑200 responses from Timesheets are logged with the full response body.

Empty data:

If a date returns no rows, the script prints "No data found for <date>." and continues.

You can expand this section if you add logging to a separate table, Slack alerts, etc.

Development notes and conventions
Python version: currently targeting Python 3.11 (matching the GitHub Actions runner).

Dependency management:

requirements.txt is generated from the venv using pip freeze > requirements.txt.

Avoid OS‑specific dependencies (pywin32, etc.) so CI on Linux works.

Environment strategy:

Local: .env file or user environment variables

CI: GitHub Actions secrets → env: block → os.getenv() in Python
