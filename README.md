
# Utilization App

The **Utilization App** is an end‑to‑end workflow for transforming Timesheets.com activity into actionable utilization insights. It includes:

- A **daily ETL pipeline** that extracts employee project hours from the Timesheets API and loads them into Supabase Postgres  
- A **Streamlit dashboard** that visualizes weekly utilization, billable hours, and project/customer mix  
- A **GitHub Actions workflow** that automates the ETL on a daily schedule  

This repository contains all components required to run the system locally or in CI.

---

##  Architecture Overview

### High‑level flow

1. **Timesheets API → ETL (Python)**  
   - Fetches customers, projects, and detailed employee time records  
   - Cleans and normalizes the data  
   - Computes billable vs non‑billable hours  

2. **ETL → Supabase Postgres**  
   - Inserts or updates rows in the `employee_hours` table  
   - Uses `record_id` as a natural key to avoid duplicates  

3. **Supabase → Streamlit App**  
   - Queries the database  
   - Aggregates hours into weekly utilization metrics  
   - Provides filters and interactive views  

4. **GitHub Actions → Automation**  
   - Runs the ETL daily  
   - Injects API keys and DB credentials via GitHub Secrets  

---

##  Repository Structure

```
Utilization_App/
├─ app/
│  ├─ homePage.py          # Streamlit dashboard entry point
│  ├─ utils/
│  │  ├─ db.py             # Database connection/query helpers
│  │  └─ ...
├─ etl/
│  ├─ dailyHoursProj.py    # Timesheets → Supabase ETL script
│  └─ ...
├─ .github/
│  └─ workflows/
│     └─ dailyHours.yml    # GitHub Actions workflow
├─ requirements.txt
├─ README.md
└─ ...
```

---

##  Data Model

### Timesheets.com (Source)

APIs used:

- **Customers**  
  `GET https://secure.timesheets.com/api/public/v1/items/customer`

- **Projects**  
  `GET https://secure.timesheets.com/api/public/v1/items/project`

- **Customizable Project Report**  
  `POST https://secure.timesheets.com/api/public/v1/report/project/customizable`

Authentication headers:

```python
headers = {
    "accept": "application/json",
    "apikey": API_KEY,
    "x-ts-authorization": API_TOKEN,
}
```

Filtering logic:

- Excludes customers named `"Internal"` or `"Choose Customer"`
- Optionally excludes `"Client Non-billable Hours"` projects

### Supabase Postgres (Target)

The ETL writes into `employee_hours` with fields such as:

- `user_id`
- `employee`
- `customer_id`
- `customer_name`
- `project_id`
- `project_name`
- `hours`
- `billable_hours`
- `work_date`
- `billable_flag`
- `record_id` (unique)

Upsert logic:

```sql
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
```

---

##  Local Development

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/Utilization_App.git
cd Utilization_App
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment variables

Create a `.env` file:

```ini
TIMESHEETS_API_KEY=your_key_here
TIMESHEETS_API_TOKEN=your_token_here
SUPABASE_PASSWORD=your_supabase_password_here
```

The ETL reads them via:

```python
os.getenv("TIMESHEETS_API_KEY")
os.getenv("TIMESHEETS_API_TOKEN")
os.getenv("SUPABASE_PASSWORD")
```

### 5. Run the ETL locally

```bash
python etl/dailyHoursProj.py
```

### 6. Run the Streamlit dashboard

```bash
streamlit run app/homePage.py
```

---

##  Streamlit Dashboard

The dashboard provides:

- Weekly utilization % (hours / 40)  
- Billable vs non‑billable breakdown  
- Filters for:
  - Employee  
  - Customer  
  - Project  
  - Date range  
- Tables and charts summarizing hours and utilization trends  


---

##  GitHub Actions: Automated Daily ETL

The workflow at `.github/workflows/dailyHours.yml`:

- Runs daily at 8 PM CST (2 AM UTC)
- Installs dependencies
- Injects secrets
- Executes the ETL script

### Required GitHub Secrets

Add these under:

**Repo → Settings → Secrets and variables → Actions**

- `TIMESHEETS_API_KEY`
- `TIMESHEETS_API_TOKEN`
- `SUPABASE_PASSWORD`

### Workflow excerpt

```yaml
env:
  TIMESHEETS_API_KEY: ${{ secrets.TIMESHEETS_API_KEY }}
  TIMESHEETS_API_TOKEN: ${{ secrets.TIMESHEETS_API_TOKEN }}
  SUPABASE_PASSWORD: ${{ secrets.SUPABASE_PASSWORD }}
```

---

##  Error Handling & Rate Limiting

- Retries Timesheets API calls when rate‑limited  
- Logs non‑200 responses  
- Skips days with no data  
- Upserts records to avoid duplicates  

---


