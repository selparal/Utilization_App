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

    /* Global font */
    html, body, [class*="css"]  {
        font-family: Arial, sans-serif;
        color: #4D4D4D;
    }

    /* Title styling */
    .main-title {
        font-family: Georgia, serif;
        font-weight: bold;
        font-size: 42px;
        color: #405A8A;
        padding: 20px 0px 10px 0px;
    }

    /* Section headers */
    h2, h3 {
        color: #405A8A !important;
        font-family: Georgia, serif;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #779CCD;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Dataframe header styling */
    .dataframe thead th {
        background-color: #8AB391 !important;
        color: white !important;
        font-weight: bold !important;
    }

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Title
# ---------------------------------------------------------
st.markdown('<div class="main-title">PIQ Employee Project Hours Dashboard</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
sql = """
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

df = run_query(sql)
df["work_date"] = pd.to_datetime(df["work_date"])

# ---------------------------------------------------------
# Rename columns for user-friendly display
# ---------------------------------------------------------
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
# Sidebar Filters
# ---------------------------------------------------------
st.sidebar.header("Filters")

# Build dropdown lists BEFORE filtering
all_employees = ["All"] + sorted(df["Employee"].unique())
all_projects = ["All"] + sorted(df["Project"].unique())
all_clients = ["All"] + sorted(df["Client"].unique())
all_years = ["All"] + sorted(df["Work Date"].dt.year.unique(), reverse=True)

# These will ALWAYS show the selected value
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
# Display Results
# ---------------------------------------------------------
st.subheader("Filtered Time Entries")
st.dataframe(filtered, use_container_width=True)

# ---------------------------------------------------------
# Summary Metrics
# ---------------------------------------------------------

# ---------------------------------------------------------
# Daily Summary Table
# ---------------------------------------------------------


# ---------------------------------------------------------
# Weekly Summary (Pivot Table)
# ---------------------------------------------------------
st.subheader("Weekly Summary (Pivoted)")

# Compute Monday of each week
filtered["Week Start"] = filtered["Work Date"] - pd.to_timedelta(
    filtered["Work Date"].dt.weekday, unit="D"
)

# Apply year filter based on Week Start
if selected_year != "All":
    filtered = filtered[filtered["Week Start"].dt.year == selected_year]

# Weekly aggregation
weekly = (
    filtered.groupby(["Employee", "Week Start"], as_index=False)
    .agg({
        "Hours": "sum",
        "Billable Hours": "sum"
    })
)

# Week label
weekly["Week Label"] = weekly["Week Start"].dt.strftime("Week of %b %d, %Y")

# Sort by actual date
weekly = weekly.sort_values("Week Start")
sorted_cols = weekly["Week Label"].unique()

# Pivot: Hours
hours_pivot = weekly.pivot_table(
    index="Employee",
    columns="Week Label",
    values="Hours",
    aggfunc="sum",
    fill_value=0
)[sorted_cols]

# Pivot: Billable Hours
billable_pivot = weekly.pivot_table(
    index="Employee",
    columns="Week Label",
    values="Billable Hours",
    aggfunc="sum",
    fill_value=0
)[sorted_cols]

# ---------------------------------------------------------
# Convert Hours → Utilization %
# ---------------------------------------------------------
WEEKLY_CAPACITY = 40

util_pivot = (hours_pivot / WEEKLY_CAPACITY * 100).round(1)
billable_util_pivot = (billable_pivot / WEEKLY_CAPACITY * 100).round(1)
util_pivot = util_pivot.astype(str) + "%"
billable_util_pivot = billable_util_pivot.astype(str) + "%"


st.write("### Weekly Client Utilization % by Employee")
st.dataframe(util_pivot, use_container_width=True)

st.write("### Weekly Billable Utilization % by Employee")
st.dataframe(billable_util_pivot, use_container_width=True)


# ---------------------------------------------------------
# Optional Chart
# ---------------------------------------------------------
st.subheader("Hours Over Time")

