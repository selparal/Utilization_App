import streamlit as st
import pandas as pd
from utils.db import run_query
import datetime
import plotly.graph_objects as go

current_year = 2025


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
   
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Fix selectbox text visibility */
div[data-baseweb="select"] span {
    color: #4D4D4D !important;
}

/* Optional: change selectbox background */
div[data-baseweb="select"] > div {
    background-color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* 3D Reset Button */
div.stButton > button {
    background: linear-gradient(145deg, #5a82c8, #3f5f9c);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.5rem 1.2rem;
    font-weight: bold;
    box-shadow:
        0 4px 0 #2f4b7c,
        0 6px 10px rgba(0, 0, 0, 0.25);
    transition: all 0.1s ease-in-out;
}

/* Pressed effect */
div.stButton > button:active {
    transform: translateY(3px);
    box-shadow:
        0 1px 0 #2f4b7c,
        0 3px 6px rgba(0, 0, 0, 0.25);
}

/* Hover */
div.stButton > button:hover {
    filter: brightness(1.05);
    cursor: pointer;
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
    jobtitle,
    userstatus,
    fullname,
    hire_date
FROM employees;
"""

emp_df = run_query(sql_emp)
emp_df["hire_date"] = pd.to_datetime(emp_df["hire_date"])
emp_df = emp_df.rename(columns={"userid": "User ID"})

# ---------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------
# Sidebar Filters
st.sidebar.header("Filters")

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



selected_employee = st.sidebar.selectbox(
    "Employee",
    all_employees,
    index=0,
    key="employee"
)

selected_project = st.sidebar.selectbox(
    "Project",
    all_projects,
    index=0,
    key="project"
)

selected_client = st.sidebar.selectbox(
    "Client",
    all_clients,
    index=0,
    key="client"
)

# Build year list
all_years = ["All"] + sorted(df["Work Date"].dt.year.unique(), reverse=True)

# Default to current year if present, otherwise "All"
default_year_index = all_years.index(current_year) if current_year in all_years else 0

selected_year = st.sidebar.selectbox(
    "Year",
    all_years,
    index=default_year_index
)

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    key="date_range"
)
st.sidebar.button("Reset Filters", on_click=reset_filters)

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

min_date = df["Work Date"].min().date()
max_date = df["Work Date"].max().date()

start_date, end_date = date_range

# Only filter if user narrowed the range
if start_date != min_date or end_date != max_date:
    filtered = filtered[
        (filtered["Work Date"] >= pd.to_datetime(start_date)) &
        (filtered["Work Date"] <= pd.to_datetime(end_date))
    ]
# ---------------------------------------------------------
# Display Raw Filtered Data
# ---------------------------------------------------------
#st.subheader("Filtered Time Entries")
#st.dataframe(filtered, use_container_width=True)

view_mode = st.radio(
    "View Mode",
    ["Weekly", "Monthly"],
    horizontal=True
)


### START WORKING LOGIC ###

# ---------------------------------------------------------
# Weekly / Monthly Summary (Pivoted)
# ---------------------------------------------------------


# ---------------------------------------------------------
# Build Period Start + Period Label based on toggle
# ---------------------------------------------------------
if view_mode == "Weekly":
    # Weekly period start
    filtered["Period Start"] = filtered["Work Date"] - pd.to_timedelta(
        filtered["Work Date"].dt.weekday, unit="D"
    )
    filtered["Period Label"] = filtered["Period Start"].dt.strftime("Week of %b %d, %Y")

else:  # Monthly
    # IMPORTANT: Monthly must start from raw Work Date rows
    filtered["Period Start"] = filtered["Work Date"].values.astype("datetime64[M]")
    filtered["Period Label"] = filtered["Period Start"].dt.strftime("%b %Y")


# ---------------------------------------------------------
# Apply year filter based on Period Start
# ---------------------------------------------------------
if selected_year != "All":
    filtered = filtered[filtered["Period Start"].dt.year == selected_year]

# ---------------------------------------------------------
# Aggregate by period (correct for both weekly & monthly)
# ---------------------------------------------------------
period_df = (
    filtered.groupby(["User ID", "Employee", "Period Start"], as_index=False)
    .agg({"Hours": "sum", "Billable Hours": "sum"})
)

# Merge hire dates
period_df = period_df.merge(emp_df, on="User ID", how="left")
period_df = period_df[~period_df["hire_date"].isna()]

# ---------------------------------------------------------
# Add Period Label AFTER aggregation
# ---------------------------------------------------------
if view_mode == "Weekly":
    period_df["Period Label"] = period_df["Period Start"].dt.strftime("Week of %b %d, %Y")
else:
    period_df["Period Label"] = period_df["Period Start"].dt.strftime("%b %Y")

# ---------------------------------------------------------
# Pivot tables
# ---------------------------------------------------------

period_df = period_df.sort_values("Period Start")
sorted_cols = period_df["Period Label"].unique()

hours_pivot = period_df.pivot_table(
    index="Employee",
    columns="Period Label",
    values="Hours",
    aggfunc="sum",
    fill_value=0
)[sorted_cols]

billable_pivot = period_df.pivot_table(
    index="Employee",
    columns="Period Label",
    values="Billable Hours",
    aggfunc="sum",
    fill_value=0
)[sorted_cols]

# ---------------------------------------------------------
# Conditional Formatting
# ---------------------------------------------------------
def apply_conditional_formatting(row):
    formatted = []
    is_avg_row = (row.name[0] == "Average")

    for col, val in row.items():
        if col == "YTD" or is_avg_row:
            if isinstance(val, str) and val.endswith("%"):
                num = float(val[:-1])
                if num < 75:
                    color = 'rgba(255, 0, 0, 0.4)'
                elif num < 85:
                    color = 'rgba(255, 255, 0, 0.4)'
                else:
                    color = 'rgba(0, 128, 0, 0.4)'
                formatted.append(f'background-color: {color}')
            else:
                formatted.append('')
        else:
            formatted.append('')
    return formatted

# ---------------------------------------------------------
# Compute period capacity (weekly or monthly)
# ---------------------------------------------------------

# ---------------------------------------------------------
# Weekly / Monthly Capacity + Utilization (CORRECTED)
# ---------------------------------------------------------
import numpy as np

WEEKLY_CAPACITY = 40

# ---------------------------------------------------------
# Compute period capacity (weekly or monthly) — NO ROUNDING
# ---------------------------------------------------------
if view_mode == "Weekly":
    period_starts = pd.to_datetime(hours_pivot.columns.str.replace("Week of ", ""))
    period_ends = period_starts + pd.Timedelta(days=6)
else:  # Monthly
    period_starts = pd.to_datetime(hours_pivot.columns)
    period_ends = period_starts + pd.offsets.MonthEnd(0)

# Workdays per period
workdays = [
    np.busday_count(start.date(), (end + pd.Timedelta(days=1)).date())
    for start, end in zip(period_starts, period_ends)
]

period_capacity = pd.Series(
    [d / 5 * WEEKLY_CAPACITY for d in workdays],
    index=hours_pivot.columns
)

# ---------------------------------------------------------
# Compute utilization per period (percent)
# ---------------------------------------------------------
util_pct = (hours_pivot / period_capacity * 100)
billable_util_pct = (billable_pivot / period_capacity * 100)

# ---------------------------------------------------------
# Mask pre-hire periods
# ---------------------------------------------------------
hire_dates = period_df.groupby("Employee")["hire_date"].first()
hire_dates = hire_dates.reindex(util_pct.index)

for i, col in enumerate(util_pct.columns):
    util_pct.loc[hire_dates > period_starts[i], col] = np.nan
    billable_util_pct.loc[hire_dates > period_starts[i], col] = np.nan

# ---------------------------------------------------------
# Compute YTD capacity — SAME LOGIC AS PERIODS
# ---------------------------------------------------------
valid_periods = period_df[period_df["Period Start"] >= period_df["hire_date"]]

period_lengths = valid_periods[["Employee", "Period Start"]].drop_duplicates()

if view_mode == "Weekly":
    period_lengths["Period End"] = period_lengths["Period Start"] + pd.Timedelta(days=6)
else:
    period_lengths["Period End"] = period_lengths["Period Start"] + pd.offsets.MonthEnd(0)

period_lengths["Workdays"] = [
    np.busday_count(start.date(), (end + pd.Timedelta(days=1)).date())
    for start, end in zip(period_lengths["Period Start"], period_lengths["Period End"])
]

capacity_emp = (
    period_lengths.groupby("Employee")["Workdays"].sum()
    / 5 * WEEKLY_CAPACITY
)

# ---------------------------------------------------------
# Compute YTD utilization (old logic: mean of periods)
# ---------------------------------------------------------
ytd_util_emp = util_pct.mean(axis=1, skipna=True).round(1)
ytd_billable_util_emp = billable_util_pct.mean(axis=1, skipna=True).round(1)

# ---------------------------------------------------------
# Period averages (column-wise)
# ---------------------------------------------------------
avg_util = util_pct.mean(skipna=True)
avg_billable_util = billable_util_pct.mean(skipna=True)

util_pct_with_avg = pd.concat([util_pct, avg_util.to_frame().T])
billable_util_pct_with_avg = pd.concat([billable_util_pct, avg_billable_util.to_frame().T])

util_pct_with_avg.index = list(util_pct.index) + ["Employee Average"]
billable_util_pct_with_avg.index = list(billable_util_pct.index) + ["Employee Average"]

# ---------------------------------------------------------
# Add YTD column (old logic)
# ---------------------------------------------------------
util_pct_with_avg["YTD"] = list(ytd_util_emp) + [ytd_util_emp.mean()]
billable_util_pct_with_avg["YTD"] = list(ytd_billable_util_emp) + [ytd_billable_util_emp.mean()]

# ---------------------------------------------------------
# Freeze YTD by making it part of the index
# ---------------------------------------------------------
util_pct_with_avg = util_pct_with_avg.set_index("YTD", append=True)
billable_util_pct_with_avg = billable_util_pct_with_avg.set_index("YTD", append=True)

# ---------------------------------------------------------
# Final formatting (ROUND ONLY HERE)
# ---------------------------------------------------------
def fmt(x):
    if pd.isna(x):
        return "–"
    return f"{x:.1f}%"

util_pivot = util_pct_with_avg.applymap(fmt)
billable_util_pivot = billable_util_pct_with_avg.applymap(fmt)

# ---------------------------------------------------------
# Display
# ---------------------------------------------------------
st.write(f"### {view_mode} Client Utilization % by Employee")
styled_util = util_pivot.style.apply(apply_conditional_formatting, axis=1)
st.dataframe(styled_util, use_container_width=True)

st.write(f"### {view_mode} Billable Utilization % by Employee")
styled_billable = billable_util_pivot.style.apply(apply_conditional_formatting, axis=1)
st.dataframe(styled_billable, use_container_width=True)

### END WORKING LOGIC ###



### PTO Planner Starts Here ###
# ---------------------------------------------------------
# Employee Job Title + YTD Utilization %
# ---------------------------------------------------------

# YTD utilization as a clean dataframe
ytd_util_df = (
    ytd_util_emp
    .reset_index()
    .rename(columns={"Employee": "Employee", 0: "YTD Utilization"})
)

# Employee + job title (unique per employee)
emp_job_df = (
    period_df[["Employee", "jobtitle"]]
    .drop_duplicates()
)

# Merge safely
ytd_job_util = emp_job_df.merge(
    ytd_util_df,
    on="Employee",
    how="left"
)

# Format %
ytd_job_util["YTD Utilization %"] = ytd_job_util["YTD Utilization"].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else "–"
)

# Final display
ytd_job_util_display = (
    ytd_job_util
    .rename(columns={
        "Employee": "Employee Name",
        "jobtitle": "Job Title"
    })
    [["Employee Name", "Job Title", "YTD Utilization %"]]
    .sort_values("Employee Name")
)

# ---------------------------------------------------------
# Display
# ---------------------------------------------------------
st.write("### Employee YTD Utilization by Job Title")
st.dataframe(ytd_job_util_display, use_container_width=True)
