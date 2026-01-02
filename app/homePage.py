import streamlit as st
import pandas as pd
from utils.db import run_query

# ---------------------------------------------------------
# Page Config
# ---------------------------------------------------------
st.set_page_config(page_title="Employee Project Hours", layout="wide")

# ---------------------------------------------------------
# Custom CSS Styling
# ---------------------------------------------------------
st.markdown("""
<style>
    html, body, [class*="css"]  {
        font-family: Arial, sans-serif;
        color: #4D4D4D;
    }
    .main-title {
        font-family: Georgia, serif;
        font-weight: bold;
        font-size: 42px;
        color: #405A8A;
        padding: 20px 0px 10px 0px;
    }
    h2, h3 {
        color: #405A8A !important;
        font-family: Georgia, serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #779CCD;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Title
# ---------------------------------------------------------
st.markdown('<div class="main-title">PIQ Employee Project Hours Dashboard</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Load employee_hours data
# ---------------------------------------------------------
sql_hours = """
SELECT
    user_id,
    employee,
    customer_name,
    project_name,
    hours,
    billable_hours,
    work_date
FROM employee_hours
ORDER BY work_date DESC;
"""

df = run_query(sql_hours)
df["work_date"] = pd.to_datetime(df["work_date"])

df = df.rename(columns={
    "user_id": "User ID",
    "employee": "Employee",
    "customer_name": "Client",
    "project_name": "Project",
    "hours": "Hours",
    "billable_hours": "Billable Hours",
    "work_date": "Work Date"
})

# ---------------------------------------------------------
# Load hire dates
# ---------------------------------------------------------
sql_emp = """
SELECT
    userid,
    hire_date
FROM employees;
"""

emp_df = run_query(sql_emp)
emp_df["hire_date"] = pd.to_datetime(emp_df["hire_date"])
emp_df = emp_df.rename(columns={"userid": "User ID"})

# ---------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------
st.sidebar.header("Filters")

all_employees = ["All"] + sorted(df["Employee"].unique())
all_projects = ["All"] + sorted(df["Project"].unique())
all_clients = ["All"] + sorted(df["Client"].unique())
all_years = ["All"] + sorted(df["Work Date"].dt.year.unique(), reverse=True)

selected_employee = st.sidebar.selectbox("Employee", all_employees)
selected_project = st.sidebar.selectbox("Project", all_projects)
selected_client = st.sidebar.selectbox("Client", all_clients)
selected_year = st.sidebar.selectbox("Year", all_years)

date_range = st.sidebar.date_input(
    "Date Range",
    value=(df["Work Date"].min(), df["Work Date"].max())
)

# ---------------------------------------------------------
# Apply Filters
# ---------------------------------------------------------
filtered = df.copy()

if selected_employee != "All":
    filtered = filtered[filtered["Employee"] == selected_employee]

if selected_project != "All":
    filtered = filtered[filtered["Project"] == selected_project]

if selected_client != "All":
    filtered = filtered[filtered["Client"] == selected_client]

if selected_year != "All":
    filtered = filtered[filtered["Work Date"].dt.year == selected_year]

start_date, end_date = date_range
filtered = filtered[
    (filtered["Work Date"] >= pd.to_datetime(start_date)) &
    (filtered["Work Date"] <= pd.to_datetime(end_date))
]

# ---------------------------------------------------------
# Display Raw Filtered Data
# ---------------------------------------------------------
st.subheader("Filtered Time Entries")
st.dataframe(filtered, use_container_width=True)

# ---------------------------------------------------------
# Weekly Summary
# ---------------------------------------------------------
st.subheader("Weekly Summary (Pivoted)")

# Compute Monday of each week
filtered["Week Start"] = filtered["Work Date"] - pd.to_timedelta(
    filtered["Work Date"].dt.weekday, unit="D"
)

# Apply year filter again (based on Week Start)
if selected_year != "All":
    filtered = filtered[filtered["Week Start"].dt.year == selected_year]

# Weekly aggregation
weekly = (
    filtered.groupby(["User ID", "Employee", "Week Start"], as_index=False)
    .agg({"Hours": "sum", "Billable Hours": "sum"})
)

# Merge hire dates
weekly = weekly.merge(emp_df, on="User ID", how="left")
# Remove employees with no hire date
weekly = weekly[~weekly["hire_date"].isna()]


# Week label
weekly["Week Label"] = weekly["Week Start"].dt.strftime("Week of %b %d, %Y")
weekly = weekly.sort_values("Week Start")
sorted_cols = weekly["Week Label"].unique()

# Pivot tables
hours_pivot = weekly.pivot_table(
    index="Employee",
    columns="Week Label",
    values="Hours",
    aggfunc="sum",
    fill_value=0
)[sorted_cols]

billable_pivot = weekly.pivot_table(
    index="Employee",
    columns="Week Label",
    values="Billable Hours",
    aggfunc="sum",
    fill_value=0
)[sorted_cols]

# Convert to utilization %
WEEKLY_CAPACITY = 40
util_pct = (hours_pivot / WEEKLY_CAPACITY * 100).round(1)
billable_util_pct = (billable_pivot / WEEKLY_CAPACITY * 100).round(1)

# ---------------------------------------------------------
# Mask pre-hire weeks
# ---------------------------------------------------------
hire_dates = weekly.groupby("Employee")["hire_date"].first()
hire_dates = hire_dates.reindex(util_pct.index)

week_starts = pd.to_datetime(
    [col.replace("Week of ", "") for col in util_pct.columns]
)

for i, col in enumerate(util_pct.columns):
    util_pct.loc[hire_dates > week_starts[i], col] = float("nan")
    billable_util_pct.loc[hire_dates > week_starts[i], col] = float("nan")

# ---------------------------------------------------------
# Weekly Averages
# ---------------------------------------------------------
avg_util = util_pct.mean(skipna=True).round(1)
avg_billable_util = billable_util_pct.mean(skipna=True).round(1)

util_pct_with_avg = pd.concat([util_pct, avg_util.to_frame().T])
billable_util_pct_with_avg = pd.concat([billable_util_pct, avg_billable_util.to_frame().T])

util_pct_with_avg.index = list(util_pct.index) + ["Average"]
billable_util_pct_with_avg.index = list(billable_util_pct.index) + ["Average"]

# Format NaN as "–"
util_pivot = util_pct_with_avg.applymap(lambda x: "–" if pd.isna(x) else f"{x}%")
billable_util_pivot = billable_util_pct_with_avg.applymap(lambda x: "–" if pd.isna(x) else f"{x}%")

# Display
st.write("### Weekly Client Utilization % by Employee")
st.dataframe(util_pivot, use_container_width=True)

st.write("### Weekly Billable Utilization % by Employee")
st.dataframe(billable_util_pivot, use_container_width=True)

# ---------------------------------------------------------
# PIQ Employee YTD Utilization
# ---------------------------------------------------------
st.subheader("PIQ Employee YTD Utilization")

piq = filtered[filtered["Employee"].str.contains("PIQ", case=False)]

ytd = (
    piq.groupby("Employee", as_index=False)
    .agg({"Hours": "sum", "Billable Hours": "sum"})
)

ytd["Client Utilization %"] = (ytd["Hours"] / (WEEKLY_CAPACITY * 52) * 100).round(1)
ytd["Billable Utilization %"] = (ytd["Billable Hours"] / (WEEKLY_CAPACITY * 52) * 100).round(1)

ytd["Client Utilization %"] = ytd["Client Utilization %"].astype(str) + "%"
ytd["Billable Utilization %"] = ytd["Billable Utilization %"].astype(str) + "%"

st.dataframe(
    ytd[["Employee", "Client Utilization %", "Billable Utilization %"]],
    use_container_width=True
)
