import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io

st.set_page_config(page_title="My Little BFM", page_icon="💰", layout="wide")

# CSS
st.markdown("""
<style>
.main-header {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;}
.metric-card {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin: 0.5rem 0;}
.bubble {background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 1.5rem; margin: 1rem 0; border: 1px solid rgba(255,255,255,0.3);}
.status-card {border-radius: 15px; padding: 1rem; text-align: center; margin: 0.5rem 0; color: white;}
.pm-analysis-card {background: linear-gradient(135deg, #8e44ad, #9b59b6); color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0; border: 2px solid #fff;}
.urgent-expiry {background: linear-gradient(135deg, #e74c3c, #c0392b) !important; animation: pulse 2s infinite;}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
  100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🚀 My Little BFM</h1><p>Budget & Financial Management System</p></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("📊 Upload VLA Excel", type=['xlsx', 'xls'])
    
    st.subheader("👥 Personnel")
    branch_size = st.number_input("Branch Size", min_value=1, value=17)
    hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.01, value=141.36, step=0.01)
    hours_per_week = st.number_input("Hours/Week", min_value=1, max_value=80, value=40)
    overhead_rate = st.number_input("Overhead (%)", min_value=0, max_value=100, value=0)
    report_date = st.date_input("Report Date", value=date.today())
    
    st.subheader("📅 Fiscal Year")
    fiscal_year = st.selectbox("Select Fiscal Year", [2024, 2025, 2026, 2027], index=1)
    
    st.subheader("🎯 Project")
    bl_codes = ['BL12200', 'BL10000', 'BL12000', 'BL12100', 'BL12300', 'BL16200', 'BL31100', 'BL41000']
    selected_bl = st.selectbox("BL Code", bl_codes)
    
    st.subheader("👨‍💼 Benedicks Analysis")
    enable_pm_analysis = st.checkbox("Enable Benedicks Portfolio Analysis", value=False)

def get_federal_holidays(fiscal_year):
    holidays = []
    if fiscal_year == 2025:
        holidays = [datetime(2024, 10, 14), datetime(2024, 11, 11), datetime(2024, 11, 28), 
                    datetime(2024, 11, 29), datetime(2024, 12, 25), datetime(2025, 1, 1),
                    datetime(2025, 1, 20), datetime(2025, 2, 17), datetime(2025, 5, 26),
                    datetime(2025, 6, 19), datetime(2025, 7, 4), datetime(2025, 9, 1)]
    return holidays

def count_working_days(start, end, fiscal_year):
    holidays = get_federal_holidays(fiscal_year)
    working_days = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            working_days += 1
        current += pd.Timedelta(days=1)
    return working_days

def get_appropriation_expiry_date(appn, fiscal_year):
    if 'OMN' in appn.upper():
        return datetime(fiscal_year, 9, 30)
    elif 'OPN' in appn.upper():
        return datetime(fiscal_year, 11, 30)
    elif 'SCN' in appn.upper():
        return datetime(fiscal_year, 12, 30)
    else:
        return datetime(fiscal_year, 9, 30)

def is_expiring_soon(report_date, expiry_date, months=2):
    warning_date = report_date + timedelta(days=months * 30)
    return expiry_date <= warning_date

def analyze_personal_funding_portfolio(file):
    """
    Analyze all funding associated with your PM name across different BL codes
    - BL16200: Your personal branch funding
    - Non-BL12200/Non-BL16200: Money given to other branches
    - BL12200: Your managed branch (excluded from analysis)
    """
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        
        # Filter for your PM entries (PM column is index 3)
        your_pm_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        your_data = df[your_pm_mask]
        
        if your_data.empty:
            return None, "No entries found for your PM name", []
        
        # Categorize by BL codes
        bl16200_mask = your_data.iloc[:, 7].astype(str).str.contains('BL16200', na=False)
        bl12200_mask = your_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        
        # Your personal funding (BL16200)
        bl16200_data = your_data[bl16200_mask]
        
        # Funding you've given to other branches (not BL12200, not BL162
