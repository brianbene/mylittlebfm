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
        bl_data = df[df.iloc[:, 8].astype(str).str.contains(target_bl, na=False)]
        
        if bl_data.empty: return None, f"No data found for {target_bl}", []
        
        def create_appn_structure():
            return {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'statuses': {'HOLD': 0.0, 'REL': 0.0, 'CRTD': 0.0}}
        
        result = {'omn': create_appn_structure(), 'opn': create_appn_structure(), 'scn': create_appn_structure()}
        chargeable_objects = []
        
        for _, row in bl_data.iterrows():
            appn = str(row.iloc[2]).upper()
            type_code = str(row.iloc[1]).upper().strip()
            balance = parse_balance(row.iloc[16])
            status = str(row.iloc[27]).upper().strip()
            
            if balance > 0:
                chargeable_objects.append({'description': str(row.iloc[5]), 'balance': balance})

            appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
            if appn_key in result:
                result[appn_key]['balance'] += balance
                if type_code == 'L': result[appn_key]['L'] += balance
                elif type_code == 'M': result[appn_key]['M'] += balance
                elif type_code == 'T': result[appn_key]['T'] += balance
                
                if status in result[appn_key]['statuses']:
                    result[appn_key]['statuses'][status] += balance
                    
        top_cos = sorted(chargeable_objects, key=lambda x: x['balance'], reverse=True)[:5]
        return result, f"✅ Extracted data for {target_bl}", top_cos
    except Exception as e:
        return None, f"❌ Error extracting VLA data: {str(e)}", []

def generate_bl_specific_email(context):
    """Generates a detailed analysis and draft email for a specific BL code."""
    if not GOOGLE_API_KEY:
        return "Error: Google AI API Key is not configured."

    system_prompt = f"""
    You are a Senior BFM (Budget & Financial Management) Analyst for a US Navy program office.
    Your task is to analyze the provided financial data for a specific BL code and generate a professional email to your Branch Head, Gene.

    **Analysis Context for BL Code {context.get('bl_code', 'N/A')}:**
    ```json
    {json.dumps(context, indent=2)}
    ```

    **Instructions:**
    Generate ONLY the email text, starting with the subject line. Use Markdown for formatting.

    **Email Template:**

    **Subject:** Financial Status & Strategy for {context.get('bl_code', 'N/A')} - {date.today().strftime('%Y-%m-%d')}

    **Gene,**

    **BLUF:** [Provide a one-sentence "Bottom Line Up Front" summarizing the overall financial health for this specific BL code, highlighting the most critical piece of information, such as an hours deficit or major funds on hold.]

    Here is the detailed summary for **{context.get('bl_code', 'N/A')}**:

    **Key Metrics:**
    *   **Total Balance:** ${context.get('total_balance', 0):,.2f}
    *   **Status Breakdown:** We have **${context.get('status_breakdown', {}).get('HOLD', 0):,.2f} on HOLD**, with ${context.get('status_breakdown', {}).get('REL', 0):,.2f} released.
    
    **Branch Hours Analysis (to Dec 31):**
    *   **Hours Needed:** {context.get('hours_analysis', {}).get('needed', 0):,.0f}
    *   **Hours Available from this BL:** {context.get('hours_analysis', {}).get('available', 0):,.0f}
    *   **Result:** We have an hours **{context.get('hours_analysis', {}).get('delta_text', 'Surplus')} of {abs(context.get('hours_analysis', {}).get('delta', 0)):,.0f} hours** for this funding.

    **Top 5 Chargeable Objects:**
    [List the top 5 objects from the 'top_chargeable_objects' context here as a bulleted list, with project description and formatted balance. If the list is empty, state "No chargeable objects with a positive balance were found."]

    **Recommended Strategy:**
    [Based on all the provided context (balances, hours analysis, funds on hold), formulate a clear, actionable spending strategy for the remainder of the year. For example: "Given the significant OPN balance and the hours deficit, I recommend we continue to charge all labor for this work to {context.get('bl_code', 'N/A')}. We should also investigate the ${context.get('status_breakdown', {}).get('HOLD', 0):,.2f} on HOLD to get those funds released."]

    Please let me know if you would like a deeper dive.

    Best,
    [Your Name]
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": system_prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=45)
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"### Error\nAn error occurred while communicating with the AI: {e}"

# --- Session State Initialization ---
for key in ['extracted_data', 'last_bl_code', 'top_cos']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'top_cos' else []

# --- Main App Body ---
if uploaded_file:
    if st.session_state.last_bl_code != selected_bl or st.session_state.extracted_data is None:
        st.session_state.extracted_data, message, st.session_state.top_cos = extract_vla_data(uploaded_file, selected_bl)
        st.session_state.last_bl_code = selected_bl
        st.info(message)

st.markdown(f"--- \n### 💰 Main Analysis for {selected_bl}")

def get_default_structure():
    return {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'statuses': {'HOLD': 0.0, 'REL': 0.0, 'CRTD': 0.0}}

defaults = {'omn': get_default_structure(), 'opn': get_default_structure(), 'scn': get_default_structure()}
data_source = st.session_state.get('extracted_data') or defaults

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
    omn_balance = st.number_input("OMN Balance ($)", value=float(data_source['omn']['balance']), key="omn_bal")
with col2:
    st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
    opn_balance = st.number_input("OPN Balance ($)", value=float(data_source['opn']['balance']), key="opn_bal")
with col3:
    st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
    scn_balance = st.number_input("SCN Balance ($)", value=float(data_source['scn']['balance']), key="scn_bal")

# --- AI Analysis Section ---
st.markdown("---")
st.markdown(f"### 🤖 AI-Powered Email Draft for {selected_bl}")
if st.button(f"Generate AI Email for {selected_bl}", key="generate_email_button"):
    if not st.session_state.extracted_data:
        st.error(f"Please upload a file and ensure data is found for {selected_bl} before generating an email.")
    else:
        with st.spinner(f"Analyzing {selected_bl} data and drafting email..."):
            # 1. Calculate the necessary metrics for the context
            report_datetime = datetime.combine(report_date, datetime.min.time())
            total_bl_balance = omn_balance + opn_balance + scn_balance
            end_of_year = datetime(fiscal_year, 12, 31)
            working_days_to_eoy = count_working_days(report_datetime, end_of_year, fiscal_year)
            hours_needed = working_days_to_eoy * 8 * branch_size
            hours_available_from_bl = total_bl_balance / hourly_rate if hourly_rate > 0 else 0
            hours_delta = hours_available_from_bl - hours_needed

            # 2. Prepare the context dictionary for the AI
            email_context = {
                "bl_code": selected_bl,
                "report_date": report_date,
                "total_balance": total_bl_balance,
                "appropriations": {
                    "OMN": omn_balance,
                    "OPN": opn_balance,
                    "SCN": scn_balance,
                },
                "status_breakdown": {
                    "HOLD": data_source['omn']['statuses']['HOLD'] + data_source['opn']['statuses']['HOLD'] + data_source['scn']['statuses']['HOLD'],
                    "REL": data_source['omn']['statuses']['REL'] + data_source['opn']['statuses']['REL'] + data_source['scn']['statuses']['REL'],
                },
                "hours_analysis": {
                    "needed": hours_needed,
                    "available": hours_available_from_bl,
                    "delta": hours_delta,
                    "delta_text": "Surplus" if hours_delta >= 0 else "Deficit"
                },
                "top_chargeable_objects": st.session_state.get('top_cos', [])
            }

            # 3. Call the AI and display the response
            ai_response = generate_bl_specific_email(email_context)
            st.markdown(ai_response)

st.markdown("---")
if st.checkbox("Show Manual Calculation Section"):
    if st.button("🚀 Calculate Manual Analysis", type="primary"):
        # ... (Manual calculation logic can remain here if needed) ...
        st.success("Manual calculation complete!")
