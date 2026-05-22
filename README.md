# Onelab Reconciliation Project

This project contains two Python web apps:
- FastAPI backend API in main.py
- Streamlit dashboard frontend in dashboard.py

## Deploy On Render

The repository includes render.yaml for Blueprint deploy with two web services:
- onelab-reconciliation-api
- onelab-reconciliation-dashboard

### 1. Push this repo to GitHub

Render deploys from a Git repository, so make sure your latest code is pushed.

### 2. Create Blueprint on Render

1. Open Render.
2. Select New +.
3. Select Blueprint.
4. Connect your repository.
5. Render will detect render.yaml and create both services.

### 3. Set Dashboard API URL

After the API service is live:
1. Open the dashboard service in Render.
2. Go to Environment.
3. Set RECON_API_URL to your API public URL, for example:
	https://onelab-reconciliation-api.onrender.com
4. Save and redeploy the dashboard service.

### 4. Verify

- API health: GET /
- API docs: /docs
- Dashboard: service URL from Render

## Local Run

Install dependencies:

pip install -r requirements.txt

Run API:

uvicorn main:app --reload --port 8000

Run dashboard:

streamlit run dashboard.py
