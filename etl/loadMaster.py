#!/usr/bin/env python3

import os
import sys
import requests
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
SUPABASE_URL = "aws-0-us-west-2.pooler.supabase.com"
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres.zvzqoiknhxcsblfyjwdx"
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")
SUPABASE_PORT = "5432"

API_KEY = os.getenv("TIMESHEETS_API_KEY")
API_TOKEN = os.getenv("TIMESHEETS_API_TOKEN")

if not API_KEY or not API_TOKEN:
    print("ERROR: Missing TIMESHEETS_API_KEY or TIMESHEETS_API_TOKEN")
    sys.exit(1)

HEADERS = {
    "accept": "application/json",
    "apikey": API_KEY,
    "x-ts-authorization": API_TOKEN
}

# --- DB connection ---
def get_connection():
    return psycopg2.connect(
        host=SUPABASE_URL,
        database=SUPABASE_DB,
        user=SUPABASE_USER,
        password=SUPABASE_PASSWORD,
        port=SUPABASE_PORT,
        sslmode="require"
    )

print("HOST:", SUPABASE_URL)
print("PASSWORD:", "SET" if SUPABASE_PASSWORD else "MISSING")

# --- Utility: get table columns from PostgreSQL ---
def get_table_columns(table):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
        """, (table,))
        cols = [row[0] for row in cur.fetchall()]
    conn.close()
    return cols

# --- Clean function (fixed) ---
def clean_df(df):
    # Replace empty strings with None, but DO NOT convert to numeric
    df = df.replace({"": None})
    return df

# --- Fetch functions ---
def fetch_users():
    url = "https://secure.timesheets.com/api/public/v1/users"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()["data"]["users"]["Data"]
    return pd.DataFrame(data)

def fetch_customers():
    url = "https://secure.timesheets.com/api/public/v1/items/customer"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()["data"]["items"]["Data"]
    return pd.DataFrame(data)

def fetch_projects():
    url = "https://secure.timesheets.com/api/public/v1/items/project"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()["data"]["items"]["Data"]
    return pd.DataFrame(data)

# --- Upsert function ---
def upsert_dynamic(df, table, pk):
    table_cols = get_table_columns(table)

    # Only keep columns that exist in the DB table
    df = df[[c for c in df.columns if c.lower() in [t.lower() for t in table_cols]]]

    # Convert dataframe columns to lowercase
    df.columns = [c.lower() for c in df.columns]

    cols = df.columns.tolist()
    col_list_sql = ", ".join(cols)
    update_sql = ", ".join([f"{c}=EXCLUDED.{c}" for c in cols if c != pk.lower()])

    insert_sql = f"""
        INSERT INTO {table} ({col_list_sql})
        VALUES %s
        ON CONFLICT ({pk})
        DO UPDATE SET
        {update_sql};
    """

    records = [tuple(row[c] for c in cols) for _, row in df.iterrows()]

    conn = get_connection()
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, records)
        conn.commit()
    conn.close()

    print(f"Upserted {len(df)} rows into {table}")

# --- Main ---
def main():
    print("Loading employees, customers, projects...")

    # --- Fetch ---
    users = fetch_users()
    customers = fetch_customers()
    projects = fetch_projects()

    # Convert READONLY for customers + projects
    if "READONLY" in customers.columns:
        customers["READONLY"] = customers["READONLY"].astype(bool)
    if "READONLY" in projects.columns:
        projects["READONLY"] = projects["READONLY"].astype(bool)

    # --- Clean (no numeric conversion) ---
    users = clean_df(users)
    customers = clean_df(customers)
    projects = clean_df(projects)

    # --- Lowercase column names ---
    users.columns = [c.lower() for c in users.columns]
    customers.columns = [c.lower() for c in customers.columns]
    projects.columns = [c.lower() for c in projects.columns]

    # --- Upsert into Supabase ---
    upsert_dynamic(users, "employees", "userid")
    upsert_dynamic(customers, "customers", "customerid")
    upsert_dynamic(projects, "projects", "projectid")

    print("✓ All master data synced successfully.")


if __name__ == "__main__":
    main()