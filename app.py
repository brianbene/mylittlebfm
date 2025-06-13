import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import json
import requests

# --- Page Configuration ---
st.set_page_config(page_title="My Little BFM", page_icon="🚀", layout="wide")

# --- CSS Styling ---
st.markdown("""
<style>
.main-header {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;}
.metric-card {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin: 0.5rem 0;}
.bubble {background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 1.5rem; margin: 1rem 0; border: 1px solid rgba(255,255,255,0.3);}
.status-card {border-radius: 15px; padding: 1rem; text-align: center; margin: 0.5rem 0; color: white;}
.pm-analysis-card {background: linear-gradient(135deg, #8e44ad, #9b59b6); color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0; border: 2px solid #fff;}
.urgent-expiry {background: linear-gradient(135deg, #e74c3c, #c0392b) !important; animation: pulse 2s infinite;}
.hours-analysis-card { background: linear-gradient(135deg, #2c3e50, #466368); color: white; padding: 1.5rem; border-radius: 15px; margin-bottom: 1.5rem; text-align: center; }
.status-breakdown-card { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.3); border-radius: 10px; padding: 1rem; margin-top: 0.5rem; }
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
  100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🚀 My Little BFM</h1><p>Budget & Financial Management System</p></div>', unsafe_allow_html=True)

# --- Sidebar Configuration ---
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
    bl_codes = ['BL12200', 'BL16200', 'BL10000', 'BL12000', 'BL12100', 'BL12300', 'BL31100', 'BL41000']
    selected_bl = st.selectbox("BL Code for Main Analysis", bl_codes)
    
    st.subheader("👨‍💼 Analysis Options")
    enable_pm_analysis = st.checkbox("Enable Benedicks Portfolio Analysis", value=False, help="Analyze Benedicks-managed projects outside of your main BL code.")
    enable_personal_funding = st.checkbox("Enable Personal Funding Analysis", value=False, help="Analyze ALL your funding across different departments (excluding BL12200 and BL16200).")
    
    st.subheader("🤖 AI Assistant")
    enable_ai_chat = st.checkbox("Enable BFM AI Assistant", value=True)
    
    # --- WARNING: Hardcoding API keys is a security risk. ---
    GOOGLE_API_KEY = "AIzaSyBynjotD4bpji6ThOtpO14tstc-qF2cFp4"

# --- Helper & Analysis Functions ---
def get_federal_holidays(year):
    holidays_by_year = {
        2024: [datetime(2024, 10, 14), datetime(2024, 11, 11), datetime(2024, 11, 28)],
        2025: [datetime(2025, 1, 1), datetime(2025, 1, 20), datetime(2025, 2, 17), datetime(2025, 5, 26), 
               datetime(2025, 6, 19), datetime(2025, 7, 4), datetime(2025, 9, 1), datetime(2024, 10, 14), 
               datetime(2024, 11, 11), datetime(2024, 11, 28), datetime(2024, 12, 25)]
    }
    return holidays_by_year.get(year, [])

def count_working_days(start, end, year):
    holidays = get_federal_holidays(year)
    working_days = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current.date() not in [h.date() for h in holidays]:
            working_days += 1
        current += timedelta(days=1)
    return working_days

def get_appropriation_expiry_date(appn, fiscal_year):
    if 'OMN' in appn.upper(): return datetime(fiscal_year, 9, 30)
    elif 'OPN' in appn.upper(): return datetime(fiscal_year + 2, 9, 30)
    elif 'SCN' in appn.upper(): return datetime(fiscal_year + 4, 9, 30)
    else: return datetime(fiscal_year, 9, 30)

def is_expiring_soon(report_date, expiry_date, months=2):
    return expiry_date <= report_date + timedelta(days=months * 30.5)

def parse_balance(value):
    try:
        str_val = str(value).replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
        return float(str_val)
    except (ValueError, TypeError):
        return 0.0

def extract_vla_data(file, target_bl):
    try:
        df = pd.read_excel(file, sheet_name=0, header=2)
        # CORRECTED: Billing Element is column I (index 8)
        bl_data = df[df.iloc[:, 8].astype(str).str.contains(target_bl, na=False)]
        
        if bl_data.empty: return None, f"No data found for {target_bl}", []
        
        def create_appn_structure():
            return {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'statuses': {'HOLD': 0.0, 'REL': 0.0, 'CRTD': 0.0}}
        
        result = {'omn': create_appn_structure(), 'opn': create_appn_structure(), 'scn': create_appn_structure()}
        
        for _, row in bl_data.iterrows():
            appn = str(row.iloc[2]).upper()
            type_code = str(row.iloc[1]).upper().strip()
            balance = parse_balance(row.iloc[16])
            status = str(row.iloc[27]).upper().strip()
            
            appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
            if appn_key in result:
                result[appn_key]['balance'] += balance
                if type_code == 'L': result[appn_key]['L'] += balance
                elif type_code == 'M': result[appn_key]['M'] += balance
                elif type_code == 'T': result[appn_key]['T'] += balance
                
                if status in result[appn_key]['statuses']:
                    result[appn_key]['statuses'][status] += balance
                    
        return result, f"✅ Extracted data for {target_bl}", []
    except Exception as e:
        return None, f"❌ Error extracting VLA data: {str(e)}", []

# --- AI Integration & Other Functions ---
def call_google_ai_api(user_message, context, api_key):
    # ... (rest of the functions are unchanged but included for completeness) ...
    if not api_key: return "The Google AI API key is not configured."
    
    def json_converter(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()

    try:
        api_context_json = json.dumps(context, indent=2, default=json_converter)
        system_prompt = f"""You are a Budget and Financial Management (BFM) AI Assistant. 
        Analyze this data and answer the user's question. Current analysis context: {api_context_json}.
        Keep responses concise and actionable."""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = { "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser: {user_message}"}]}] }

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.RequestException as e:
        return f"API Error: {e}"
    except (KeyError, IndexError):
        return "Received an unexpected response from the AI."
    except Exception as e:
        return f"An unexpected error occurred during API call: {e}"

# --- Session State Initialization ---
for key in ['extracted_data', 'last_bl_code', 'benedicks_data', 'analysis_context', 'chat_history']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'chat_history' else []

# --- Main App Body ---
if uploaded_file:
    if st.session_state.last_bl_code != selected_bl or st.session_state.extracted_data is None:
        st.session_state.extracted_data, message, _ = extract_vla_data(uploaded_file, selected_bl)
        st.session_state.last_bl_code = selected_bl
        st.info(message)

# --- Data Input & Calculation Section ---
st.markdown(f"--- \n### 💰 Main Analysis for {selected_bl}")

def get_default_structure():
    return {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'statuses': {'HOLD': 0.0, 'REL': 0.0, 'CRTD': 0.0}}

defaults = {'omn': get_default_structure(), 'opn': get_default_structure(), 'scn': get_default_structure()}
data_source = st.session_state.get('extracted_data') or defaults

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
    omn_balance = st.number_input("OMN Balance ($)", value=float(data_source['omn']['balance']), key="omn_bal")
    omn_l = st.number_input("OMN Labor ($)", value=float(data_source['omn']['L']), key="omn_l")
    omn_m = st.number_input("OMN Material ($)", value=float(data_source['omn']['M']), key="omn_m")
    omn_t = st.number_input("OMN Travel ($)", value=float(data_source['omn']['T']), key="omn_t")
with col2:
    st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
    opn_balance = st.number_input("OPN Balance ($)", value=float(data_source['opn']['balance']), key="opn_bal")
    opn_l = st.number_input("OPN Labor ($)", value=float(data_source['opn']['L']), key="opn_l")
    opn_m = st.number_input("OPN Material ($)", value=float(data_source['opn']['M']), key="opn_m")
    opn_t = st.number_input("OPN Travel ($)", value=float(data_source['opn']['T']), key="opn_t")
with col3:
    st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
    scn_balance = st.number_input("SCN Balance ($)", value=float(data_source['scn']['balance']), key="scn_bal")
    scn_l = st.number_input("SCN Labor ($)", value=float(data_source['scn']['L']), key="scn_l")
    scn_m = st.number_input("SCN Material ($)", value=float(data_source['scn']['M']), key="scn_m")
    scn_t = st.number_input("SCN Travel ($)", value=float(data_source['scn']['T']), key="scn_t")

if st.button("🚀 Calculate Full Analysis", type="primary"):
    st.markdown("--- \n## 📊 Analysis Results")
    report_datetime = datetime.combine(report_date, datetime.min.time())
    monthly_personnel_cost = hourly_rate * hours_per_week * 4.3 * branch_size * (1 + overhead_rate / 100)
    total_balance = omn_balance + opn_balance + scn_balance

    st.markdown("### ⏳ Branch Hours Analysis (to End of Fiscal Year)")
    end_of_fy = datetime(fiscal_year, 9, 30)
    working_days_to_eofy = count_working_days(report_datetime, end_of_fy, fiscal_year)
    
    hours_needed = working_days_to_eofy * 8 * branch_size
    hours_available = total_balance / hourly_rate if hourly_rate > 0 else 0
    hours_delta = hours_available - hours_needed
    
    delta_color = "lightgreen" if hours_delta >= 0 else "lightcoral"
    delta_text = "Excess" if hours_delta >= 0 else "Deficit"

    st.markdown(f"""
    <div class="hours-analysis-card">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
            <div><h4>Hours Needed</h4><h3>{hours_needed:,.0f}</h3></div>
            <div><h4>Hours Available</h4><h3>{hours_available:,.0f}</h3></div>
            <div><h4 style="color:{delta_color};">Hours {delta_text}</h4><h3 style="color:{delta_color};">{abs(hours_delta):,.0f}</h3></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Funding Status Breakdown")
    status_col1, status_col2, status_col3 = st.columns(3)
    appn_status_data = {
        'OMN': data_source['omn']['statuses'],
        'OPN': data_source['opn']['statuses'],
        'SCN': data_source['scn']['statuses']
    }
    cols = [status_col1, status_col2, status_col3]
    for i, (appn, statuses) in enumerate(appn_status_data.items()):
        with cols[i]:
            st.markdown(f"<h5>{appn} Status</h5>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="status-breakdown-card">
                <p><strong>HOLD:</strong> ${statuses.get('HOLD', 0):,.2f}</p>
                <p><strong>REL:</strong> ${statuses.get('REL', 0):,.2f}</p>
                <p><strong>CRTD:</strong> ${statuses.get('CRTD', 0):,.2f}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="bubble"><h3>💡 Smart APPN Charging Strategy</h3></div>', unsafe_allow_html=True)
    # ... (rest of the app logic remains the same)

# ... (The rest of the script for AI Chat and Footer is unchanged)
if enable_ai_chat:
    st.markdown("--- \n### 🤖 BFM AI Assistant")
    if not GOOGLE_API_KEY:
        st.error("The Google AI API key is missing. The chat assistant is disabled.")
    else:
        for role, message in st.session_state.chat_history:
            with st.chat_message(role): st.markdown(message)
        
        if prompt := st.chat_input("Ask about your financial data..."):
            st.session_state.chat_history.append(("user", prompt))
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Thinking..."):
                    response = call_google_ai_api(prompt, st.session_state.analysis_context, GOOGLE_API_KEY)
                    st.markdown(response)
            
            st.session_state.chat_history.append(("assistant", response))

st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>🚀 My Little BFM • Enhanced with Smart APPN Charging & Portfolio Analysis</p></div>', unsafe_allow_html=True)
