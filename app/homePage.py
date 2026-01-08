import streamlit as st
import pandas as pd
from utils.db import run_query
import datetime
import plotly.graph_objects as go

current_year = 2025
import streamlit as st
from streamlit_msal import Msal



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
# Build Period Start + Period Label + Aggregate (FIXED)
# ---------------------------------------------------------

# Merge hire dates once
filtered = filtered.merge(
    emp_df[["User ID", "hire_date"]],
    on="User ID",
    how="left"
)

# Remove pre-hire work rows
filtered = filtered[filtered["Work Date"] >= filtered["hire_date"]]

if view_mode == "Weekly":

    # ------------------------
    # WEEKLY (unchanged logic)
    # ------------------------
    filtered["Period Start"] = (
        filtered["Work Date"]
        - pd.to_timedelta(filtered["Work Date"].dt.weekday, unit="D")
    )

    if selected_year != "All":
        filtered = filtered[filtered["Period Start"].dt.year == selected_year]

    period_df = (
        filtered.groupby(
            ["User ID", "Employee", "Period Start"],
            as_index=False
        )
        .agg({"Hours": "sum", "Billable Hours": "sum"})
    )

    period_df["Period Label"] = period_df["Period Start"].dt.strftime(
    "Week of %b %d, %Y"
)

    period_df = period_df.merge(
    emp_df[["User ID", "hire_date", "jobtitle"]],
    on="User ID",
    how="left"
)



else:

    # ------------------------
    # MONTHLY (FIXED)
    # ------------------------

    # Assign month start to raw rows
    filtered["Period Start"] = filtered["Work Date"].values.astype("datetime64[M]")

    if selected_year != "All":
        filtered = filtered[filtered["Period Start"].dt.year == selected_year]

    # Aggregate actual worked hours per month
    monthly_hours = (
        filtered.groupby(
            ["User ID", "Employee", "Period Start"],
            as_index=False
        )
        .agg({"Hours": "sum", "Billable Hours": "sum"})
    )

    # Build FULL month range per employee starting at hire month
    all_periods = []

    for _, row in emp_df.iterrows():
        uid = row["User ID"]
        hire = row["hire_date"]

        emp_rows = monthly_hours[monthly_hours["User ID"] == uid]
        if emp_rows.empty:
            continue

        start = emp_rows["Period Start"].min()
        end = emp_rows["Period Start"].max()


        months = pd.date_range(start, end, freq="MS")
        for m in months:
            all_periods.append({
                "User ID": uid,
                "Employee": emp_rows["Employee"].iloc[0],
                "Period Start": m
            })

    all_periods_df = pd.DataFrame(all_periods)

    # Merge hours into full month grid
    period_df = all_periods_df.merge(
        monthly_hours,
        on=["User ID", "Employee", "Period Start"],
        how="left"
    )

    period_df["Hours"] = period_df["Hours"].fillna(0)
    period_df["Billable Hours"] = period_df["Billable Hours"].fillna(0)

    period_df["Period Label"] = period_df["Period Start"].dt.strftime("%b %Y")

    # ✅ ADD THIS
    period_df = period_df.merge(
        emp_df[["User ID", "hire_date", "jobtitle"]],
        on="User ID",
        how="left"
    )




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

    is_avg_row = str(row.name).lower().startswith("employee average")

    for col, val in row.items():

        # Apply formatting to YTD column AND bottom average row
        if col == "YTD" or is_avg_row:
            if isinstance(val, str) and val.endswith("%"):
                num = float(val.rstrip("%"))

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
# Mask pre-hire periods (FIXED for partial months)
# ---------------------------------------------------------

hire_dates = period_df.groupby("Employee")["hire_date"].first()
hire_dates = hire_dates.reindex(util_pct.index)

for i, col in enumerate(util_pct.columns):

    if view_mode == "Weekly":
        period_end = period_starts[i] + pd.Timedelta(days=6)
    else:  # Monthly
        period_end = period_starts[i] + pd.offsets.MonthEnd(0)

    mask = hire_dates > period_end

    util_pct.loc[mask, col] = np.nan
    billable_util_pct.loc[mask, col] = np.nan


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

st.markdown(
    """
    <hr style="border: 1px solid #779CCD; margin-top: 30px; margin-bottom: 30px;">
    """,
    unsafe_allow_html=True
)

### PTO Planner Starts Here ###
# ---------------------------------------------------------
# PTO Planner (Based on YTD Utilization %)
# ---------------------------------------------------------

# Clean YTD utilization
ytd_util_df = (
    ytd_util_emp
    .reset_index()
    .rename(columns={0: "YTD Utilization"})
)

# Employee job titles
emp_job_df = (
    period_df[["Employee", "jobtitle"]]
    .drop_duplicates()
)

# Merge utilization + job title + capacity
pto_df = (
    emp_job_df
    .merge(ytd_util_df, on="Employee", how="left")
    .merge(capacity_emp.reset_index().rename(columns={"Workdays": "YTD Capacity"}), 
           on="Employee", how="left")
)
# ---------------------------------------------------------
# PTO policy logic (defines targets & PTO allocation)
# ---------------------------------------------------------
def pto_policy(job_title):
    jt = job_title.lower()
    if jt in ["consultant", "associate consultant", "senior consultant"]:
        return 90.0, 0.10   # 90% util target, 10% PTO
    else:
        return 85.0, 0.15   # 85% util target, 15% PTO

pto_df[["Util Target %", "PTO %"]] = pto_df["jobtitle"].apply(
    lambda x: pd.Series(pto_policy(x))
)

# ---------------------------------------------------------
# Correct PTO calculation (earned vs deficit)
# ---------------------------------------------------------
# ---------------------------------------------------------
# PTO calculation with penalties for underperformance
# ---------------------------------------------------------

# Raw utilization delta (can be positive or negative)
pto_df["Util Delta %"] = (
    (pto_df["YTD Utilization"] - pto_df["Util Target %"]) / 100
)

# Earned PTO (only positive deltas)
pto_df["Earned PTO Hours"] = (
    (pto_df["Util Delta %"].clip(lower=0)) * pto_df["YTD Capacity"]
)

# PTO deficit (only negative deltas)
pto_df["PTO Deficit Hours"] = (
    (pto_df["Util Delta %"].clip(upper=0)) * pto_df["YTD Capacity"]
)

# PTO cap (max earned)
pto_df["Max PTO Hours"] = (
    pto_df["YTD Capacity"] * pto_df["PTO %"]
)

# Final PTO:
#   - Positive PTO is capped
#   - Negative PTO is allowed fully
pto_df["PTO Hours"] = (
    pto_df.apply(
        lambda row: min(row["Earned PTO Hours"], row["Max PTO Hours"])
        if row["Earned PTO Hours"] > 0
        else row["PTO Deficit Hours"],
        axis=1
    )
).round(1)




# ---------------------------------------------------------
# Employee selector
# ---------------------------------------------------------
selected_employee = st.selectbox(
    "Select Employee",
    sorted(pto_df["Employee"].unique())
)

emp_row = pto_df[pto_df["Employee"] == selected_employee].iloc[0]
# Planned PTO input
planned_pto = st.number_input(
    "Planned PTO Hours (optional)",
    min_value=0.0,
    step=1.0,
    format="%.1f"
)

# ---------------------------------------------
# Recompute utilization including planned PTO
# ---------------------------------------------

# Convert YTD utilization % back to actual hours worked
actual_hours = (emp_row["YTD Utilization"] / 100) * emp_row["YTD Capacity"]

# Subtract planned PTO from actual hours
adjusted_hours = max(actual_hours - planned_pto, 0)

# Adjusted utilization %
adjusted_util = (adjusted_hours / emp_row["YTD Capacity"]) * 100

# Util delta vs target
util_delta = (adjusted_util - emp_row["Util Target %"]) / 100

# Earned PTO (positive only)
earned_pto = max(util_delta, 0) * emp_row["YTD Capacity"]

# PTO deficit (negative only)
pto_deficit = min(util_delta, 0) * emp_row["YTD Capacity"]

# PTO cap
max_pto = emp_row["YTD Capacity"] * emp_row["PTO %"]

# Final PTO (cap positive, allow negative)
final_pto = min(earned_pto, max_pto) if earned_pto > 0 else pto_deficit
final_pto = round(final_pto, 1)


# ---------------------------------------------------------
# Display PTO summary
# ---------------------------------------------------------
st.write(f"### PTO Summary for {selected_employee}")

col1, col2, col3 = st.columns(3)

col1.metric("Job Title", emp_row["jobtitle"])

col2.metric(
    "Adjusted Utilization",
    f"{adjusted_util:.1f}%"
)

col3.metric(
    "PTO Hours (YTD)",
    f"{final_pto} hrs"
)

if final_pto < 0:
    st.error("⚠️ Utilization below target — PTO deficit")
elif final_pto > 0:
    st.success("✔ PTO earned above target")
else:
    st.info("On target")



st.caption(
    f"PTO Policy: {emp_row['Util Target %']}% utilization target → "
    f"{int(emp_row['PTO %'] * 100)}% PTO allocation"
)
