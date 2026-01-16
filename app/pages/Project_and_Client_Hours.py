import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.db import run_query
from styling import apply_styles
import numpy as np

current_year = 2025
st.markdown(
    """
    <style>
        /* Hide Streamlit's built-in sidebar completely */
        section[data-testid="stSidebar"] {
            display: none;
        }

        /* Remove the main page padding so content uses full width */
        div[data-testid="stAppViewContainer"] {
            padding-left: 0rem;
            padding-right: 0rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)


st.markdown("""
<style>
/* Make dataframe column headers and cells narrower */
[data-testid="stDataFrame"] div[role="table"] th {
    padding: 2px 6px !important;   /* narrow headers */
    font-size: 12px !important;
}

[data-testid="stDataFrame"] div[role="table"] td {
    padding: 2px 6px !important;   /* narrow cells */
    font-size: 12px !important;
}

/* Reduce minimum column width */
[data-testid="stDataFrame"] div[role="columnheader"] {
    min-width: 60px !important;
}
[data-testid="stDataFrame"] div[role="cell"] {
    min-width: 60px !important;
}
</style>
<style>
/* Right-align column headers */
[data-testid="stDataFrame"] div[role="columnheader"] {
    justify-content: flex-end !important;
    text-align: right !important;
}

/* Right-align numeric cells */
[data-testid="stDataFrame"] div[role="cell"] {
    justify-content: flex-end !important;
    text-align: right !important;
}
</style>

""", unsafe_allow_html=True)



# ---------------------------------------------------------
# Page Config & Styling
# ---------------------------------------------------------
st.set_page_config(page_title="Client & Project Hours", layout="wide")
apply_styles()
st.page_link("Home.py", label="⬅ Back to Home")

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
# Top Filters
# ---------------------------------------------------------
st.markdown("### Filters")
col1, col2, col3, col4 = st.columns(4)

all_employees = ["All"] + sorted(df["Employee"].unique())
all_projects = ["All"] + sorted(df["Project"].unique())
all_clients = ["All"] + sorted(df["Client"].unique())
all_years = ["All"] + sorted(df["Work Date"].dt.year.unique(), reverse=True)

min_date = df["Work Date"].min().date()
max_date = df["Work Date"].max().date()

def reset_filters():
    st.session_state.update({
        "employee": "All",
        "project": "All",
        "client": "All",
        "year": "All",
        "date_range": (min_date, max_date),
    })

with col1:
    selected_employee = st.selectbox("Employee", all_employees, index=0, key="employee")
with col2:
    selected_project = st.selectbox("Project", all_projects, index=0, key="project")
with col3:
    selected_client = st.selectbox("Client", all_clients, index=0, key="client")
with col4:
    default_year_index = all_years.index(current_year) if current_year in all_years else 0
    selected_year = st.selectbox("Year", all_years, index=default_year_index)

date_range = st.date_input("Date Range", value=(min_date, max_date), key="date_range")
st.button("Reset Filters", on_click=reset_filters)

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
# Aggregate by Week
# ---------------------------------------------------------
filtered["Week Start"] = filtered["Work Date"] - pd.to_timedelta(filtered["Work Date"].dt.weekday, unit="D")
weekly_agg = (
    filtered.groupby(["Employee", "Client", "Project", "Week Start"], as_index=False)
    .agg({"Hours": "sum", "Billable Hours": "sum"})
)
weekly_agg["Week Label"] = weekly_agg["Week Start"].dt.strftime("%b %d")
# ---------------------------------------------------------
# Sort weeks chronologically
# ---------------------------------------------------------

week_order = sorted(
    weekly_agg["Week Label"].unique(),
    key=lambda x: pd.to_datetime(x + " " + str(filtered['Work Date'].dt.year.min()))
)

# ---------------------------------------------------------
# Pivot for Hours
# ---------------------------------------------------------
hours_pivot = weekly_agg.pivot_table(
    index=["Employee", "Client", "Project"],
    columns="Week Label",
    values="Hours",
    aggfunc="sum",
    fill_value=0
)[week_order]  # reorder columns chronologically
hours_pivot.reset_index(inplace=True)

# ---------------------------------------------------------
# Pivot for Billable Hours
# ---------------------------------------------------------
billable_pivot = weekly_agg.pivot_table(
    index=["Employee", "Client", "Project"],
    columns="Week Label",
    values="Billable Hours",
    aggfunc="sum",
    fill_value=0
)[week_order]
billable_pivot.reset_index(inplace=True)

# ---------------------------------------------------------
# Add Total Hours column (sum of all week columns)
# ---------------------------------------------------------

# ---------------------------------------------------------
# Identify week columns ONCE (before adding Total Hours)
# ---------------------------------------------------------
week_cols = [c for c in hours_pivot.columns if c not in ["Employee", "Client", "Project"]]

# ---------------------------------------------------------
# HOURS pivot
# ---------------------------------------------------------
hours_pivot["Total Hours"] = hours_pivot[week_cols].sum(axis=1)
hours_pivot = hours_pivot[["Employee", "Client", "Project", "Total Hours"] + week_cols]

# ---------------------------------------------------------
# BILLABLE pivot
# ---------------------------------------------------------
billable_pivot["Total Billable Hours"] = billable_pivot[week_cols].sum(axis=1)
billable_pivot = billable_pivot[["Employee", "Client", "Project", "Total Billable Hours"] + week_cols]


# ---------------------------------------------------------
# Freeze columns (Employee, Client, Project, Total Hours)
# ---------------------------------------------------------
frozen_config = {
    "Employee": st.column_config.TextColumn("Employee", pinned="left", width="small"),
    "Client": st.column_config.TextColumn("Client", pinned="left", width="small"),
    "Project": st.column_config.TextColumn("Project", pinned="left", width="small"),
    "Total Hours": st.column_config.NumberColumn("Total Hours", pinned="left", width="small"),
}

# ---------------------------------------------------------
# Display Tables (wider)
# ---------------------------------------------------------

# ==============================
# HOURS TABLE + TOTALS
# ==============================
st.subheader("Weekly Hours by Employee / Client / Project")

st.dataframe(
    hours_pivot,
    use_container_width=True,
    height=600,
    column_config=frozen_config  # Pins Employee/Client/Project/Total Hours
)

# ---- Total Hours under the table
total_hours_all = (
    hours_pivot["Total Hours"].sum()
    if "Total Hours" in hours_pivot.columns else float("nan")
)

st.markdown(f"**Total Hours (all rows): {total_hours_all:,.1f}**")

st.divider()

# ==============================
# BILLABLE TABLE + TOTALS
# ==============================
st.subheader("Weekly Billable Hours by Employee / Client / Project")

billable_frozen_config = {
    "Employee": st.column_config.TextColumn("Employee", pinned="left", width="small"),
    "Client": st.column_config.TextColumn("Client", pinned="left", width="small"),
    "Project": st.column_config.TextColumn("Project", pinned="left", width="small"),
    "Total Billable Hours": st.column_config.NumberColumn("Total Billable Hours", pinned="left", width="small"),
}

st.dataframe(
    billable_pivot,
    use_container_width=True,
    height=600,
    column_config=billable_frozen_config
)

# ---- Total Billable Hours under the table
total_billable_all = (
    billable_pivot["Total Billable Hours"].sum()
    if "Total Billable Hours" in billable_pivot.columns else float("nan")
)

st.markdown(f"**Total Billable Hours (all rows): {total_billable_all:,.1f}**")
