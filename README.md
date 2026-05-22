# Onelab Reconciliation Project

This project contains two Python web apps:
- FastAPI backend API in main.py
- Streamlit dashboard frontend in dashboard.py


## Local Run

Install dependencies:

pip install -r requirements.txt

Run API:

uvicorn main:app --reload --port 8000

Run dashboard:

streamlit run dashboard.py
