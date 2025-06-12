import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import json
import requests

# --- Configuration & Constants ---
st.set_page_config(page_title="My Little BFM", page_icon="💰", layout="wide")
GOOGLE_API_KEY = "AIzaSyBynjotD4bpji6ThOtpO14tstc-qF2cFp4"

# --- CSS Styling ---
st.markdown("""
<style>
.main-header {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;}
.metric-card {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin: 0.5rem 0;}
.status-card {border-radius: 15px; padding: 1rem; text-align: center; margin: 0.5rem 0; color: white; min-height: 220px;}
.urgent-expiry {animation: pulse 1.5s infinite;}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
  100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
}
</style>
""", unsafe_allow_html=True)

# --- Core Functions ---
def get_federal_holidays(year):
    if year in [2024, 2025]:
        # Federal Holidays for FY2025 (Oct 2024 - Sep 2025)
        return [
            datetime(2024, 10, 14), datetime(2024, 11, 11), datetime(2024, 11, 28),
            datetime(2024, 12, 25), datetime(2025, 1, 1), datetime(2025, 1, 20),
            datetime(2025, 2, 17), datetime(2025, 5, 26), datetime(2025, 6, 19),
            datetime(2025, 7, 4), datetime(2025, 9, 1)
        ]
    return []

def count_working_days(start_date, end_date):
    if start_date.date() > end_date.date(): return 0
    holidays = set(get_federal_holidays(start_date.year) + get_federal_holidays(end_date.year))
    working_days = 0
    current_date = start_date.date()
    while current_date <= end_date.date():
        if current_date.weekday() < 5 and datetime(current_date.year, current_date.month, current_date.day) not in holidays:
            working_days += 1
        current_date += timedelta(days=1)
    return working_days

def get_appropriation_expiry_date(appn, fy):
    if 'OMN' in appn.upper(): return datetime(fy, 9, 30)
    elif 'OPN' in appn.upper(): return datetime(fy + 1, 9, 30)
    elif 'SCN' in appn.upper(): return datetime(fy + 2, 9, 30)
    else: return datetime(fy, 9, 30)

# FIXED: Added the missing function definition
def is_expiring_soon(report_dt, expiry_dt, months=2):
    return expiry_dt <= report_dt + timedelta(days=months * 30.5)

def call_google_ai_api(user_message, context, api_key):
    try:
        system_prompt = f"""You are a helpful Budget and Financial Management (BFM) AI Assistant. Analyze the provided financial context and the user's question to give clear, actionable advice. Today's date is {date.today().strftime('%B %d, %Y')}. The context is: {json.dumps(context, indent=2)}"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {"contents": [{"parts": [{"text": f"{system_prompt}\n\nUser Question: {user_message}"}]}]}
        response = requests.post(url, headers=headers, json=data, timeout=45)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.RequestException as e:
        return f"Network Error: Could not reach Google AI. Please check your connection. Details: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# --- Sidebar and Global Inputs ---
st.markdown('<div class="main-header"><h1>🚀 My Little BFM</h1><p>Budget & Financial Management System</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("📊 Upload VLA Excel (Optional)", type=['xlsx', 'xls'])
    st.subheader("👥 Personnel")
    branch_size = st.number_input("Branch Size", min_value=1, value=17)
    hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.01, value=141.36, step=0.01)
    st.subheader("📅 Dates & Fiscal Year")
    report_date = st.date_input("Report Date", value=date.today())
    fiscal_year = st.selectbox("Select Fiscal Year", [2024, 2025, 2026, 2027], index=1)
    st.subheader("🤖 AI Assistant")
    enable_ai_chat = st.checkbox("Enable BFM AI Assistant", value=True)

# --- Initialize Session State ---
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'analysis_context' not in st.session_state: st.session_state.analysis_context = {}

# --- Main Page UI ---
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
    omn_balance = st.number_input("OMN Balance ($)", value=44053.0, key="omn_b", label_visibility="collapsed")
with col2:
    st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
    opn_balance = st.number_input("OPN Balance ($)", value=1947299.0, key="opn_b", label_visibility="collapsed")
with col3:
    st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
    scn_balance = st.number_input("SCN Balance ($)", value=1148438.0, key="scn_b", label_visibility="collapsed")

if st.button("🚀 Calculate Analysis", type="primary", use_container_width=True):
    # --- Perform All Calculations on Button Click ---
    report_datetime = datetime.combine(report_date, datetime.min.time())
    monthly_personnel_cost = hourly_rate * 40 * 4.333 * branch_size
    total_balance = omn_balance + opn_balance + scn_balance

    appropriations = {
        'OMN': {'balance': omn_balance, 'lmt': {'L': omn_balance, 'M': 0, 'T': 0}, 'expiry': get_appropriation_expiry_date('OMN', fiscal_year)},
        'OPN': {'balance': opn_balance, 'lmt': {'L': opn_balance, 'M': 0, 'T': 0}, 'expiry': get_appropriation_expiry_date('OPN', fiscal_year)},
        'SCN': {'balance': scn_balance, 'lmt': {'L': scn_balance, 'M': 0, 'T': 0}, 'expiry': get_appropriation_expiry_date('SCN', fiscal_year)}
    }
    for key, val in appropriations.items():
        val['days_left'] = (val['expiry'] - report_datetime).days
        val['work_days_left'] = count_working_days(report_datetime, val['expiry'])
        val['is_urgent'] = is_expiring_soon(report_datetime, val['expiry'])

    # --- Update AI Context in Session State ---
    st.session_state.analysis_context = {
        "report_date": report_date.isoformat(), "total_balance": total_balance,
        "monthly_personnel_cost": monthly_personnel_cost,
        "appropriations": {k: {**v, 'expiry': v['expiry'].isoformat()} for k, v in appropriations.items()}
    }
    
    st.success("Analysis Complete & AI Context Updated!")
    
    # --- Display Results ---
    st.markdown("### 📊 Financial Health Overview")
    kpi_cols = st.columns(3)
    kpi_cols[0].metric("💰 Total Balance", f"${total_balance:,.0f}")
    months_of_burn = (total_balance / monthly_personnel_cost) if monthly_personnel_cost > 0 else 0
    kpi_cols[1].metric("⏳ Total Branch Months of Burn", f"{months_of_burn:.1f} months")
    kpi_cols[2].metric("👩‍💻 Monthly Cost", f"${monthly_personnel_cost:,.0f}")
    
    st.markdown("---")
    
    st.markdown("###  Appropriations Status")
    card_cols = st.columns(3)
    colors = {'OMN': '#c0392b', 'OPN': '#e67e22', 'SCN': '#27ae60'}
    for i, (name, data) in enumerate(appropriations.items()):
        with card_cols[i]:
            card_class = "urgent-expiry" if data['is_urgent'] else ""
            st.markdown(f'<div class="status-card {card_class}" style="background: linear-gradient(135deg, {colors[name]}, #2c3e50);">'\
                        f'<h3>{name}</h3><h4>${data["balance"]:,.0f}</h4>'\
                        f'<p>Expires: {data["expiry"].strftime("%b %d, %Y")}</p>'\
                        f'<p>({data["days_left"]} days / {data["work_days_left"]} work days)</p></div>', unsafe_allow_html=True)

# --- Chatbot UI ---
if enable_ai_chat:
    st.markdown("---")
    st.markdown("### 🤖 BFM AI Assistant")

    if not GOOGLE_API_KEY.startswith("AIza"):
        st.error("Invalid Google AI API Key. Please ensure the key is correct.")
    else:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("Ask about your financial data..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    context = st.session_state.analysis_context
                    if not context:
                        response = "I don't have any data. Please click 'Calculate Analysis' first."
                    else:
                        response = call_google_ai_api(prompt, context, GOOGLE_API_KEY)
                    st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})

st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>My Little BFM</p></div>', unsafe_allow_html=True)
