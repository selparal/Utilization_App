import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "aws-0-us-west-2.pooler.supabase.com"
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres.zvzqoiknhxcsblfyjwdx"
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")
SUPABASE_PORT = "5432"

def run_query(sql, params=None):
    conn = psycopg2.connect(
        host=SUPABASE_URL,
        database=SUPABASE_DB,
        user=SUPABASE_USER,
        password=SUPABASE_PASSWORD,
        port=SUPABASE_PORT,
        sslmode="require"
    )
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df
