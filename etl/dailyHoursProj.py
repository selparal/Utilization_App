import os
import time
from time import sleep
from datetime import datetime, timedelta

import requests
import pandas as pd
import psycopg2

# ---------------------------------------------------------
# Timesheets API config
# ---------------------------------------------------------
API_KEY = os.getenv("TIMESHEETS_API_KEY")
API_TOKEN = os.getenv("TIMESHEETS_TOKEN")

headers = {
    "accept": "application/json",
    "apikey": API_KEY,
    "x-ts-authorization": API_TOKEN,
}

# ---------------------------------------------------------
# Supabase DB config
# ---------------------------------------------------------
SUPABASE_URL = "aws-0-us-west-2.pooler.supabase.com"
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres.zvzqoiknhxcsblfyjwdx"
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")
SUPABASE_PORT = "5432"

# ---------------------------------------------------------
# Fetch billable customer IDs (exclude Internal)
# ---------------------------------------------------------
def get_billable_customer_ids(headers):
    url = "https://secure.timesheets.com/api/public/v1/items/customer"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("Error fetching customers:", resp.text)
        return []

    data = resp.json()
    customers = [
        {"CustomerName": item["CUSTOMERNAME"], "CustomerID": item["CUSTOMERID"]}
        for item in data["data"]["items"]["Data"]
    ]

    exclude_names = {"Internal", "Choose Customer"}
    return [c["CustomerID"] for c in customers if c["CustomerName"] not in exclude_names]

# ---------------------------------------------------------
# Extract employee-level project hours
# ---------------------------------------------------------
def extract_employee_project_hours(raw_json):
    rows = []

    for employee_block in raw_json:
        user_id = employee_block.get("UserID", "")
        first = employee_block.get("FirstName", "")
        last = employee_block.get("LastName", "")
        full_name = employee_block.get("FullName", f"{first} {last}")

        records = employee_block.get("Records", {}).get("Data", [])

        for entry in records:
            project_name = entry.get("PROJECTNAME", "")
            hours = float(entry.get("HOURS", 0))

            # Billable logic
            billable_hours = hours if project_name != "Client Non-billable Hours" else 0

            rows.append({
                "user_id": entry.get("USERID", user_id),
                "employee": entry.get("FULLNAME", full_name),

                "customer_id": entry.get("CUSTOMERID", ""),
                "customer_name": entry.get("CUSTOMERNAME", ""),

                "project_id": entry.get("PROJECTID", ""),
                "project_name": project_name,

                "hours": hours,
                "billable_hours": billable_hours,

                "work_date": entry.get("WORKDATE", ""),
                "billable_flag": entry.get("BILLABLE", ""),
                "record_id": entry.get("RECORDID", ""),
            })

    return pd.DataFrame(rows)

# ---------------------------------------------------------
# Filter projects
# ---------------------------------------------------------
def filter_projects(headers, corb):
    proj_url = "https://secure.timesheets.com/api/public/v1/items/project"
    proj_response = requests.get(proj_url, headers=headers)
    if proj_response.status_code != 200:
        print("Error fetching projects:", proj_response.text)
        return None

    proj_json = proj_response.json()
    proj_data = [
        {"ProjectName": item["PROJECTNAME"], "ProjectID": item["PROJECTID"]}
        for item in proj_json["data"]["items"]["Data"]
    ]

    if corb == "b":
        proj_ids = [
            entry["ProjectID"]
            for entry in proj_data
            if entry["ProjectName"] != "Client Non-billable Hours"
        ]
    else:
        proj_ids = [entry["ProjectID"] for entry in proj_data]

    return ", ".join(proj_ids)

# ---------------------------------------------------------
# Rate-limit safe POST helper
# ---------------------------------------------------------
def safe_post(url, headers, body, retries=3, delay=60):
    for attempt in range(retries):
        r = requests.post(url, headers=headers, json=body)
        if r.status_code == 200:
            return r
        elif "rate limited" in r.text.lower():
            print("Rate limited, sleeping...")
            time.sleep(delay)
        else:
            print("Error:", r.status_code, r.text)
            return None
    return None

# ---------------------------------------------------------
# Fetch employee-level time report
# ---------------------------------------------------------
def fetch_time_report(headers, customer_list, startdate, enddate, proj_list):
    rep_url = "https://secure.timesheets.com/api/public/v1/report/project/customizable"
    body = {
        "AllCustomers": "0",
        "CustomerList": customer_list,
        "StartDate": startdate,
        "EndDate": enddate,
        "AllProjects": "0",
        "ProjectList": proj_list,
        "AllUsers": "1",
        "ReportType": "Detailed",
        "GroupType": "User",
        "Billable": "RECORD_BILLABLE,RECORD_UNBILLABLE",
        "Signed": "RECORD_UNSIGNED,RECORD_SIGNED",
        "Approved": "RECORD_UNAPPROVED,RECORD_APPROVED",
        "RecordStatus": "PROJECTRECORDSTATUS_ACTIVE,PROJECTRECORDSTATUS_ARCHIVED,PROJECTRECORDSTATUS_ALL",
        "AllAccountCodes": "1",
    }

    r = safe_post(rep_url, headers, body)
    if not r:
        return pd.DataFrame()

    report_data = r.json().get("report", {}).get("ReportData", [])
    if not report_data:
        return pd.DataFrame()

    df = extract_employee_project_hours(report_data)
    return df

# ---------------------------------------------------------
# Insert into Supabase
# ---------------------------------------------------------
def insert_employee_hours(df):
    if df.empty:
        return

    conn = psycopg2.connect(
        host=SUPABASE_URL,
        database=SUPABASE_DB,
        user=SUPABASE_USER,
        password=SUPABASE_PASSWORD,
        port=SUPABASE_PORT,
        sslmode="require"
    )
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO employee_hours (
            user_id, employee,
            customer_id, customer_name,
            project_id, project_name,
            hours, billable_hours,
            work_date, billable_flag, record_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (record_id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            employee = EXCLUDED.employee,
            customer_id = EXCLUDED.customer_id,
            customer_name = EXCLUDED.customer_name,
            project_id = EXCLUDED.project_id,
            project_name = EXCLUDED.project_name,
            hours = EXCLUDED.hours,
            billable_hours = EXCLUDED.billable_hours,
            work_date = EXCLUDED.work_date,
            billable_flag = EXCLUDED.billable_flag;
    """

    for _, row in df.iterrows():
        work_date = datetime.strptime(row["work_date"], "%B, %d %Y %H:%M:%S")

        cur.execute(
            insert_sql,
            (
                row["user_id"],
                row["employee"],
                row["customer_id"],
                row["customer_name"],
                row["project_id"],
                row["project_name"],
                row["hours"],
                row["billable_hours"],
                work_date,
                row["billable_flag"],
                row["record_id"],
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    billable_customer_ids = get_billable_customer_ids(headers)
    customer_list = ", ".join(billable_customer_ids)

    project_list = filter_projects(headers, "c")

    for i in range(0,8): #750, 840
        day = (datetime.today() - timedelta(days=i)).strftime("%m/%d/%Y")
        print(f"\nFetching {day}...")

        df = fetch_time_report(headers, customer_list, day, day, project_list)
        sleep(7)

        if df.empty:
            print(f"No data found for {day}.")
            continue

        print(df)

        insert_employee_hours(df)

        print(f"Inserted {len(df)} employee project rows for {day}.")
        sleep(20)

if __name__ == "__main__":
    main()
