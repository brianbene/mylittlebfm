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

def get_top_cos_for_bl(file, target_bl, sheet_name):
    if not file: return []
    try:
        df = pd.read_excel(file, sheet_name=sheet_name, header=1)
        df.columns = [str(c).strip() for c in df.columns]
        required_cols = ['Work Ctr', 'Avail Proj Auth', 'APPN', 'Chargeable Object']
        if not all(col in df.columns for col in required_cols): return []
        
        bl_data = df[df['Work Ctr'].astype(str).str.contains(target_bl, na=False)]
        if bl_data.empty: return []
        
        chargeable_objects = []
        for _, row in bl_data.iterrows():
            try:
                balance = float(str(row['Avail Proj Auth']).replace('$', '').replace(',', '').strip())
                if balance > 0:
                    chargeable_objects.append({"CO_Number": str(row['Chargeable Object']), "APPN": str(row['APPN']), "Balance": balance})
            except (ValueError, TypeError): continue
        return sorted(chargeable_objects, key=lambda x: x['Balance'], reverse=True)[:5]
    except Exception: return []

def extract_benedicks_data_for_ai(file, sheet_name):
    if not file: return []
    try:
        df = pd.read_excel(file, sheet_name=sheet_name, header=1)
        df.columns = [str(c).strip() for c in df.columns]
        required_cols = ['PM', 'Avail Proj Auth', 'Chargeable Object', 'Work Ctr', 'APPN', 'Project Description']
        if not all(col in df.columns for col in required_cols): return []
        
        mask = df['PM'].astype(str).str.lower().str.contains('benedicks', na=False)
        benedicks_data = df[mask]
        if benedicks_data.empty: return []
        
        projects = []
        for _, row in benedicks_data.iterrows():
            try:
                balance = float(str(row['Avail Proj Auth']).replace('$', '').replace(',', '').strip())
                if balance > 0:
                    projects.append({
                        "CO": str(row['Chargeable Object']), "BL_Code": str(row['Work Ctr']),
                        "APPN": str(row['APPN']), "Balance": balance, "Description": str(row['Project Description'])
                    })
            except (ValueError, TypeError): continue
        return sorted(projects, key=lambda x: x['Balance'], reverse=True)[:30]
    except Exception: return []

def call_google_ai_api(user_message, context, api_key):
    # MODIFIED: New, smarter system prompt
    system_prompt = f"""You are a BFM AI Assistant. Your goal is to provide context-aware answers based on the provided data.
    Today's date is {date.today().strftime('%B %d, %Y')}.

    Here is the data context you must use:
    {json.dumps(context, indent=2)}

    **Your Instructions:**
    1.  **Prioritize UI Context:** The context contains a `selected_bl_for_ui` and `top_5_cos_for_selected_bl`. This is what the user is currently seeing on their screen. If they ask a general question like "what are the top COs?", you MUST primarily answer using this data.
    2.  **Differentiate Data:** The context also contains `benedicks_portfolio_details`, which is a broader list of all projects managed by "Benedicks". Only use this list if the user specifically asks about the "entire portfolio", "all projects", or a BL code *not* currently selected in the UI.
    3.  **Example response to 'What are the top COs?':** "Based on your selection of {context.get('selected_bl_for_ui')}, the top 5 Chargeable Objects are: [list from top_5_cos_for_selected_bl]. Would you like to see the top COs from the entire Benedicks portfolio instead?"
    4.  **Answer ONLY from Context:** Do not invent data or use external knowledge. If the context doesn't contain the answer, state that clearly.
    """
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
            sheet_name = st.selectbox("Select Sheet to Analyze", xls.sheet_names)
        except Exception as e: st.error(f"Could not read Excel sheets: {e}")

    st.subheader("👥 Personnel")
    branch_size = st.number_input("Branch Size", min_value=1, value=17)
    hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.01, value=141.36, step=0.01)
    st.subheader("🎯 Project")
    selected_bl = st.selectbox("BL Code for Top 5 COs", ['BL12200', 'BL10000', 'BL12000', 'BL12100', 'BL12300', 'BL16200'])
    st.subheader("📅 Dates & Fiscal Year")
    report_date = st.date_input("Report Date", value=date.today())
    fiscal_year = st.selectbox("Select Fiscal Year", [2024, 2025, 2026, 2027], index=1)
    st.subheader("🤖 AI Assistant")
    enable_ai_chat = st.checkbox("Enable BFM AI Assistant", value=True)

for key in ['chat_history', 'analysis_context', 'top_cos', 'appropriations_data']:
    if key not in st.session_state: st.session_state[key] = [] if key in ['chat_history', 'top_cos'] else {} if key == 'analysis_context' else None

col1, col2, col3 = st.columns(3)
# ... input fields for OMN, OPN, SCN ...

if st.button("🚀 Calculate Analysis & Update AI", type="primary", use_container_width=True):
    if uploaded_file and not sheet_name:
        st.error("File uploaded, but could not read sheets. Please ensure it's a valid Excel file.")
    else:
        report_datetime = datetime.combine(report_date, datetime.min.time())
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
        
        # MODIFIED: AI context now includes the selected BL and its top COs
        st.session_state.analysis_context = {
            "financial_summary": { "total_balance": omn_balance + opn_balance + scn_balance, "monthly_personnel_cost": hourly_rate * 40 * 4.333 * branch_size},
            "appropriations": {k: {**v, 'expiry': v['expiry'].isoformat()} for k, v in appropriations.items()},
            "ui_context": {
                "selected_bl_for_ui": selected_bl,
                "top_5_cos_for_selected_bl": st.session_state.top_cos
            },
            "benedicks_portfolio_details": extract_benedicks_data_for_ai(uploaded_file, sheet_name) 
        }
        st.success("Analysis Complete!")

# --- Display Results Area ---
# ... (The UI display logic remains largely the same, as it correctly uses session state)

# --- Chatbot UI ---
if enable_ai_chat:
    st.markdown("---")
    # ... (Chatbot UI code remains the same)
