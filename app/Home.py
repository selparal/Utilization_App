import streamlit as st
import pandas as pd
from utils.db import run_query
import datetime
import plotly.graph_objects as go

current_year = 2025
import streamlit as st
from streamlit_msal import Msal
from streamlit import column_config




st.set_page_config(page_title="Utilization App")



# ---------------------------------------------------------
# Page Config
# ---------------------------------------------------------
st.set_page_config(page_title="Employee Project Hours", layout="wide")

# ---------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------
import streamlit as st

st.set_page_config(layout="wide")

# ---------------------------------------------------------
#  CSS Styling
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
        "%b %d"
    )

    period_df = period_df.merge(
    emp_df[["User ID", "hire_date", "jobtitle"]],
    on="User ID",
    how="left"
)



else:  # Monthly

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

    # ✅ Month only, no year
    period_df["Period Label"] = period_df["Period Start"].dt.strftime("%b")

    # Merge jobtitle/hire_date
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

    period_starts = (
        period_df
        .drop_duplicates("Period Label")
        .sort_values("Period Start")["Period Start"]
        .tolist()

    )

    period_ends = [d + pd.Timedelta(days=6) for d in period_starts]


else:  # Monthly
    period_starts = period_df.drop_duplicates("Period Label").sort_values("Period Start")["Period Start"].tolist()
    period_ends = [d + pd.offsets.MonthEnd(0) for d in period_starts]

# Workdays per period
workdays = [
    np.busday_count(
        start.date(),
        (end + pd.Timedelta(days=1)).date()
    )
    for start, end in zip(period_starts, period_ends)
]

period_capacity = pd.Series(
    [d / 5 * WEEKLY_CAPACITY for d in workdays],
    index=hours_pivot.columns
)
# ---------------------------------------------------------
# Compute utilization per period
# ---------------------------------------------------------
util_pct = (hours_pivot / period_capacity * 100)
billable_util_pct = (billable_pivot / period_capacity * 100)

# ---------------------------------------------------------
# Mask pre-hire periods safely (avoiding duplicate index error)
# ---------------------------------------------------------

# Build a mapping of employee -> hire date
hire_date_map = emp_df.set_index("fullname")["hire_date"].to_dict()

# Loop through period columns to mask pre-hire periods
for i, col in enumerate(util_pct.columns):
    if view_mode == "Weekly":
        period_end = period_starts[i] + pd.Timedelta(days=6)
    else:
        period_end = period_starts[i] + pd.offsets.MonthEnd(0)

    # Mask employees whose hire date is after period_end
    for emp in util_pct.index:
        if hire_date_map.get(emp, pd.Timestamp.min) > period_end:
            util_pct.at[emp, col] = np.nan
            billable_util_pct.at[emp, col] = np.nan




# ---------------------------------------------------------
# FIXED YTD CALCULATION (Frozen, independent of Weekly/Monthly)
# YTD is computed Jan 1 -> cutoff, where cutoff = min(Dec 31, max data date in that year, today)
# ---------------------------------------------------------
import numpy as np

WEEKLY_CAPACITY = 40

if selected_year == "All":
    ytd_year = pd.Timestamp.now().year
else:
    ytd_year = selected_year

year_start = pd.Timestamp(f"{ytd_year}-01-01")
year_end   = pd.Timestamp(f"{ytd_year}-12-31")

# Determine a reasonable cutoff "to-date" for YTD:
#  - if you have entries for the year, use the max Work Date in that year
#  - otherwise use today (so you don't assume future capacity)
df_this_year = df[(df["Work Date"] >= year_start) & (df["Work Date"] <= year_end)]
if not df_this_year.empty:
    data_cutoff = df_this_year["Work Date"].max().normalize()
else:
    data_cutoff = pd.Timestamp.today().normalize()

ytd_cutoff = min(year_end, data_cutoff)

# We'll compute YTD from raw time entries (not period_df) to keep it view-mode invariant
# And we will include ALL employees (from emp_df) who could be in scope for the year,
# even if they have zero rows so far this year.
# Normalize key alignment: df uses "Employee" (full name), emp_df has "fullname".
emp_info = emp_df.rename(columns={"fullname": "Employee"})[["User ID", "Employee", "hire_date", "jobtitle"]].copy()

# Merge raw rows for the year
ytd_rows = df[
    (df["Work Date"] >= year_start) &
    (df["Work Date"] <= ytd_cutoff)
].merge(
    emp_info[["User ID", "hire_date"]],
    on="User ID",
    how="left"
)

# Remove pre-hire rows
ytd_rows = ytd_rows[ytd_rows["Work Date"] >= ytd_rows["hire_date"]]

# Build the full roster to evaluate YTD for (anyone hired on/before ytd_cutoff)
roster = emp_info[emp_info["hire_date"] <= ytd_cutoff][["User ID", "Employee", "hire_date", "jobtitle"]].drop_duplicates()

ytd_capacity = {}
ytd_util_actual = {}
ytd_billable_util_actual = {}

for _, r in roster.iterrows():
    emp_name = r["Employee"]
    hire     = pd.Timestamp(r["hire_date"])

    # Capacity window starts at later of Jan 1 or hire date, ends at ytd_cutoff
    start = max(hire, year_start)
    end   = ytd_cutoff

    if end < start:
        # No capacity yet (e.g., hired after cutoff)
        ytd_capacity[emp_name] = 0.0
        ytd_util_actual[emp_name] = np.nan
        ytd_billable_util_actual[emp_name] = np.nan
        continue

    # Capacity based on business days (Mon–Fri)
    num_workdays = np.busday_count(start.date(), (end + pd.Timedelta(days=1)).date())
    capacity = (num_workdays / 5) * WEEKLY_CAPACITY
    ytd_capacity[emp_name] = capacity

    # Actual/billable from raw rows
    emp_rows = ytd_rows[ytd_rows["Employee"] == emp_name]
    total_hours = emp_rows["Hours"].sum() if not emp_rows.empty else 0.0
    total_billable = emp_rows["Billable Hours"].sum() if not emp_rows.empty else 0.0

    # Utilization (guard for zero capacity)
    ytd_util_actual[emp_name] = (total_hours / capacity * 100) if capacity > 0 else np.nan
    ytd_billable_util_actual[emp_name] = (total_billable / capacity * 100) if capacity > 0 else np.nan

# ---------------------------------------------------------
# Inject frozen YTD next to Employee (robust, no KeyError)
# ---------------------------------------------------------

# 1) Build tables with the "Employee Average" row
avg_util = util_pct.mean(skipna=True)
avg_billable_util = billable_util_pct.mean(skipna=True)

util_pct_with_avg = pd.concat([util_pct, avg_util.to_frame().T])
billable_util_pct_with_avg = pd.concat([billable_util_pct, avg_billable_util.to_frame().T])

# 2) Explicitly label the average row and set index name to "Employee"
#    (prevents reset_index from creating a column called "index")
util_pct_with_avg.index = list(util_pct.index) + ["Employee Average"]
billable_util_pct_with_avg.index = list(billable_util_pct.index) + ["Employee Average"]

util_pct_with_avg = util_pct_with_avg.rename_axis("Employee")
billable_util_pct_with_avg = billable_util_pct_with_avg.rename_axis("Employee")

# 3) Build YTD columns aligned by Employee (NaN for the avg row)
util_ytd_col = []
billable_ytd_col = []

for emp_name in util_pct_with_avg.index:
    if str(emp_name).lower() == "employee average":
        util_ytd_col.append(np.nan)
        billable_ytd_col.append(np.nan)
    else:
        util_ytd_col.append(round(ytd_util_actual.get(emp_name, np.nan), 2))
        billable_ytd_col.append(round(ytd_billable_util_actual.get(emp_name, np.nan), 2))

# 4) Insert YTD as first column (still indexed by Employee at this point)
util_pct_with_avg.insert(0, "YTD", util_ytd_col)
billable_util_pct_with_avg.insert(0, "YTD", billable_ytd_col)

# 5) Bring "Employee" out of the index to build a MultiIndex ["Employee","YTD"]
#    Use .reset_index() now that the index is properly named "Employee"
util_pct_with_avg = util_pct_with_avg.reset_index()           # columns now include "Employee" and "YTD"
billable_util_pct_with_avg = billable_util_pct_with_avg.reset_index()

# 6) Set the MultiIndex so Employee + YTD stay frozen on the left in Streamlit
util_pct_with_avg = util_pct_with_avg.set_index(["Employee", "YTD"])
billable_util_pct_with_avg = billable_util_pct_with_avg.set_index(["Employee", "YTD"])

# 7) Formatting AFTER index is set
def fmt(x):
    if pd.isna(x):
        return "–"
    return f"{x:.1f}%"

util_pivot = util_pct_with_avg.applymap(fmt)
billable_util_pivot = billable_util_pct_with_avg.applymap(fmt)

ytd_vals = pd.to_numeric(util_pct_with_avg.index.get_level_values("YTD"), errors='coerce')
overall_util_ytd = np.nanmean(ytd_vals)  # ignore NaNs

ytd_vals_billable = pd.to_numeric(billable_util_pct_with_avg.index.get_level_values("YTD"), errors='coerce')
overall_billable_ytd = np.nanmean(ytd_vals_billable)


st.write(f"### {view_mode} Client Utilization % by Employee")
st.dataframe(
    util_pivot.style.set_properties(**{
        "text-align": "right"
    }),
    use_container_width=True
)
st.markdown(f"**Overall Employee Average YTD: {overall_util_ytd:.1f}%**")
st.write(f"### {view_mode} Billable Utilization % by Employee")
st.dataframe(
    billable_util_pivot.style.set_properties(**{
        "text-align": "right"
    }),
    use_container_width=True
)
st.markdown(f"**Overall Employee Average Billable YTD: {overall_billable_ytd:.1f}%**")






# ---------------------------------------------------------
# PTO Planner (Based on fixed YTD Utilization %)
# ---------------------------------------------------------

# Build PTO DataFrame
emp_job_df = period_df[["Employee", "jobtitle"]].drop_duplicates()

pto_df = (
    emp_job_df
    .copy()
)

# Only include employees eligible for PTO planning
def pto_eligibility(job_title):
    jt = job_title.lower()
    if jt in ["consultant", "associate consultant", "senior consultant"]:
        return 90.0, 0.10   # 90% target, 10% PTO
    elif jt in ["director"]:
        return 85.0, 0.15   # 85% target, 15% PTO
    else:
        return None, None   # Exclude others

# Apply policy
pto_df[["Util Target %", "PTO %"]] = pto_df["jobtitle"].apply(
    lambda x: pd.Series(pto_eligibility(x))
)

# Filter out employees with None targets
pto_df = pto_df[pto_df["Util Target %"].notna()].copy()

# Add YTD Utilization and Capacity from previously computed values
pto_df["YTD Utilization"] = pto_df["Employee"].map(ytd_util_actual)
pto_df["YTD Capacity"] = pto_df["Employee"].map(ytd_capacity)

# ---------------------------------------------------------
# PTO calculation
# ---------------------------------------------------------

# Raw utilization delta (can be positive or negative)
pto_df["Util Delta %"] = (pto_df["YTD Utilization"] - pto_df["Util Target %"]) / 100

# Earned PTO (positive only)
pto_df["Earned PTO Hours"] = (pto_df["Util Delta %"].clip(lower=0)) * pto_df["YTD Capacity"]

# PTO deficit (negative only)
pto_df["PTO Deficit Hours"] = (pto_df["Util Delta %"].clip(upper=0)) * pto_df["YTD Capacity"]

# PTO cap (max earned)
pto_df["Max PTO Hours"] = pto_df["YTD Capacity"] * pto_df["PTO %"]

# Final PTO (cap positive, allow negative)
pto_df["PTO Hours"] = pto_df.apply(
    lambda row: min(row["Earned PTO Hours"], row["Max PTO Hours"])
    if row["Earned PTO Hours"] > 0
    else row["PTO Deficit Hours"],
    axis=1
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

# Adjusted utilization including planned PTO
actual_hours = (emp_row["YTD Utilization"] / 100) * emp_row["YTD Capacity"]
adjusted_hours = max(actual_hours - planned_pto, 0)
adjusted_util = (adjusted_hours / emp_row["YTD Capacity"]) * 100

# Util delta vs target
util_delta = (adjusted_util - emp_row["Util Target %"]) / 100

# Adjust PTO
earned_pto = max(util_delta, 0) * emp_row["YTD Capacity"]
pto_deficit = min(util_delta, 0) * emp_row["YTD Capacity"]
max_pto = emp_row["YTD Capacity"] * emp_row["PTO %"]
final_pto = min(earned_pto, max_pto) if earned_pto > 0 else pto_deficit
final_pto = round(final_pto, 1)

# ---------------------------------------------------------
# Display PTO summary
# ---------------------------------------------------------
st.write(f"### PTO Summary for {selected_employee}")

col1, col2, col3 = st.columns(3)
col1.metric("Job Title", emp_row["jobtitle"])
col2.metric("Adjusted Utilization", f"{adjusted_util:.1f}%")
col3.metric("PTO Hours (YTD)", f"{final_pto} hrs")

if final_pto < 0:
    st.error("⚠️ Utilization below target — PTO deficit")
elif final_pto > 0:
    st.success("✔ PTO earned above target")
else:
    st.info("On target")

st.caption(
    f"PTO Policy: {emp_row['Util Target %']}% utilization target → "
    f"{int(emp_row['PTO %']*100)}% PTO allocation"
)
