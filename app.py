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
.status-card {border-radius: 15px; padding: 1rem; text-align: center; margin: 0.5rem 0; color: white; min-height: 220px; display: flex; flex-direction: column; justify-content: center;}
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

def is_expiring_soon(report_dt, expiry_dt, months=2):
    return expiry_dt <= report_dt + timedelta(days=months * 30.5)

# ROBUST FUNCTION: Now searches for columns by name instead of position
def get_top_cos_for_bl(file, target_bl, sheet_name):
    if not file: return []
    try:
        df = pd.read_excel(file, sheet_name=sheet_name, header=1)
        df.columns = df.columns.str.strip() # Clean up column names

        # Define expected column names
        work_ctr_col = 'Work Ctr'
        balance_col = 'Avail Proj Auth'
        appn_col = 'APPN'
        co_col = 'Chargeable Object'

        # Check if required columns exist
        required_cols = [work_ctr_col, balance_col, appn_col, co_col]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Missing required columns in sheet '{sheet_name}'. Expected: {required_cols}")
            return []

        bl_data = df[df[work_ctr_col].astype(str).str.contains(target_bl, na=False)]
        if bl_data.empty: return []
        
        chargeable_objects = []
        for _, row in bl_data.iterrows():
            try:
                balance = float(str(row[balance_col]).replace('$', '').replace(',', '').strip())
                if balance > 0:
                    chargeable_objects.append({
                        "CO_Number": str(row[co_col]), "APPN": str(row[appn_col]), "Balance": balance
                    })
            except (ValueError, TypeError): continue
        return sorted(chargeable_objects, key=lambda x: x['Balance'], reverse=True)[:5]
    except Exception as e:
        st.error(f"Error processing sheet '{sheet_name}': {e}")
        return []

# ROBUST FUNCTION: Now searches for columns by name
def extract_benedicks_data_for_ai(file, sheet_name):
    if not file: return []
    try:
        df = pd.read_excel(file, sheet_name=sheet_name, header=1)
        df.columns = df.columns.str.strip()

        # Define expected column names
        pm_col = 'PM'
        balance_col = 'Avail Proj Auth'
        co_col = 'Chargeable Object'
        bl_code_col = 'Work Ctr'
        appn_col = 'APPN'
        desc_col = 'Project Description'

        required_cols = [pm_col, balance_col, co_col, bl_code_col, appn_col, desc_col]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Missing required columns for AI analysis in sheet '{sheet_name}'. Expected: {required_cols}")
            return []

        mask = df[pm_col].astype(str).str.lower().str.contains('benedicks', na=False)
        benedicks_data = df[mask]
        if benedicks_data.empty: return []
        
        projects = []
        for _, row in benedicks_data.iterrows():
            try:
                balance = float(str(row[balance_col]).replace('$', '').replace(',', '').strip())
                if balance > 0:
                    projects.append({
                        "CO": str(row[co_col]), "BL_Code": str(row[bl_code_col]),
                        "APPN": str(row[appn_col]), "Balance": balance, "Description": str(row[desc_col])
                    })
            except (ValueError, TypeError): continue
        return sorted(projects, key=lambda x: x['Balance'], reverse=True)[:30]
    except Exception as e:
        st.error(f"Error extracting Benedicks data from sheet '{sheet_name}': {e}")
        return []

def call_google_ai_api(user_message, context, api_key):
    system_prompt = f"""You are a BFM AI Assistant. Answer questions based ONLY on the provided context. The context is: {json.dumps(context, indent=2)}"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {"contents": [{"parts": [{"text": f"{system_prompt}\n\nUser Question: {user_message}"}]}]}
        response = requests.post(url, headers=headers, json=data, timeout=45)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e: return f"Error: {e}"

# --- UI Layout ---
st.markdown('<div class="main-header"><h1>🚀 My Little BFM</h1><p>Budget & Financial Management System</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("📊 Upload VLA Excel", type=['xlsx', 'xls'])
    
    sheet_name = None
    if uploaded_file:
        try:
            xls = pd.ExcelFile(uploaded_file)
            sheet_options = xls.sheet_names
            sheet_name = st.selectbox("Select Sheet to Analyze", sheet_options, index=0)
        except Exception as e:
            st.error(f"Could not read Excel sheets. Error: {e}")

    st.subheader("👥 Personnel")
    branch_size = st.number_input("Branch Size", min_value=1, value=17)
    hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.01, value=141.36, step=0.01)
    st.subheader("🎯 Project")
    bl_codes = ['BL12200', 'BL10000', 'BL12000', 'BL12100', 'BL12300', 'BL16200', 'BL31100', 'BL41000']
    selected_bl = st.selectbox("BL Code for Top 5 COs", bl_codes)
    st.subheader("📅 Dates & Fiscal Year")
    report_date = st.date_input("Report Date", value=date.today())
    fiscal_year = st.selectbox("Select Fiscal Year", [2024, 2025, 2026, 2027], index=1)
    st.subheader("🤖 AI Assistant")
    enable_ai_chat = st.checkbox("Enable BFM AI Assistant", value=True)

# Initialize Session State
for key in ['chat_history', 'analysis_context', 'top_cos', 'appropriations_data']:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ['chat_history', 'top_cos'] else {} if key == 'analysis_context' else None

# Main Page UI
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

if st.button("🚀 Calculate Analysis & Update AI", type="primary", use_container_width=True):
    if uploaded_file and not sheet_name:
        st.error("File uploaded, but could not read sheets. Please ensure it's a valid Excel file and re-upload.")
    else:
        report_datetime = datetime.combine(report_date, datetime.min.time())
        monthly_personnel_cost = hourly_rate * 40 * 4.333 * branch_size
        
        appropriations = {
            'OMN': {'balance': omn_balance, 'expiry': get_appropriation_expiry_date('OMN', fiscal_year)},
            'OPN': {'balance': opn_balance, 'expiry': get_appropriation_expiry_date('OPN', fiscal_year)},
            'SCN': {'balance': scn_balance, 'expiry': get_appropriation_expiry_date('SCN', fiscal_year)}
        }
        for key, val in appropriations.items():
            val['days_left'] = (val['expiry'] - report_datetime).days
            val['work_days_left'] = count_working_days(report_datetime, val['expiry'])
            val['is_urgent'] = is_expiring_soon(report_datetime, val['expiry'])
        
        st.session_state.appropriations_data = appropriations
        st.session_state.top_cos = get_top_cos_for_bl(uploaded_file, selected_bl, sheet_name)
        benedicks_details = extract_benedicks_data_for_ai(uploaded_file, sheet_name)
        
        st.session_state.analysis_context = {
            "financial_summary": {"total_balance": omn_balance + opn_balance + scn_balance, "monthly_personnel_cost": monthly_personnel_cost},
            "appropriations": {k: {**v, 'expiry': v['expiry'].isoformat()} for k, v in appropriations.items()},
            "benedicks_portfolio_details": benedicks_details 
        }
        st.success("Analysis Complete!")

# --- Display Results Area ---
st.markdown("### 📊 Financial Health Overview")
total_balance = omn_balance + opn_balance + scn_balance
monthly_personnel_cost = hourly_rate * 40 * 4.333 * branch_size
kpi_cols = st.columns(3)
kpi_cols[0].metric("💰 Total Balance", f"${total_balance:,.0f}")
kpi_cols[1].metric("⏳ Total Branch Months of Burn", f"{(total_balance / monthly_personnel_cost) if monthly_personnel_cost > 0 else 0:.1f} months")
kpi_cols[2].metric("👩‍💻 Monthly Cost", f"${monthly_personnel_cost:,.0f}")
st.markdown("---")

disp_col1, disp_col2 = st.columns(2)
with disp_col1:
    st.markdown("### Appropriations Status")
    if st.session_state.appropriations_data:
        colors = {'OMN': '#c0392b', 'OPN': '#e67e22', 'SCN': '#27ae60'}
        for name, data in st.session_state.appropriations_data.items():
            st.markdown(f'<div class="status-card {"urgent-expiry" if data["is_urgent"] else ""}" style="background: linear-gradient(135deg, {colors[name]}, #2c3e50); margin-bottom: 1rem;">'
                        f'<h3>{name}</h3><h4>${data["balance"]:,.0f}</h4>'
                        f'<p>Expires: {data["expiry"].strftime("%b %d, %Y")}</p>'
                        f'<p>({data["days_left"]} days / {data["work_days_left"]} work days)</p></div>', unsafe_allow_html=True)
    else:
        st.info("Click 'Calculate Analysis' to see detailed expiry information.")

with disp_col2:
    st.markdown(f"### 🎯 Top 5 COs for {selected_bl}")
    if st.session_state.top_cos:
        report_datetime = datetime.combine(report_date, datetime.min.time())
        for co in st.session_state.top_cos:
            expiry = get_appropriation_expiry_date(co['APPN'], fiscal_year)
            st.markdown(f"""
            <div style="border-left: 5px solid {'#e74c3c' if is_expiring_soon(report_datetime, expiry) else '#555'}; padding: 0.5rem 1rem; margin-bottom: 0.5rem; background: #f8f9fa; border-radius: 5px;">
                <strong>{co['CO_Number']} ({co['APPN']})</strong><br>
                Balance: <strong>${co['Balance']:,.0f}</strong> | Expires: {expiry.strftime('%b %d, %Y')}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Upload a file and click 'Calculate Analysis' to see the Top 5 Chargeable Objects.")

# --- Chatbot UI ---
if enable_ai_chat:
    st.markdown("---")
    st.markdown("### 🤖 BFM AI Assistant")
    if not GOOGLE_API_KEY.startswith("AIza"):
        st.error("A valid Google AI API Key was not found in the script.")
    else:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]): st.markdown(message["content"])
        if prompt := st.chat_input("Ask about your financial data..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    context = st.session_state.analysis_context
                    if not context:
                        response = "Please click 'Calculate Analysis' first to load data for the AI."
                    else:
                        response = call_google_ai_api(prompt, context, GOOGLE_API_KEY)
                    st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
