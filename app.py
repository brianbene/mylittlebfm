import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import json
import requests

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

/* Chat Messenger Styles */
.chat-widget {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
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
    
    st.subheader("👨‍💼 Analysis Options")
    enable_pm_analysis = st.checkbox("Enable Benedicks Portfolio Analysis", value=False)
    enable_personal_funding = st.checkbox("Enable Personal Funding Analysis", value=False, help="Analyze ALL your funding across different BL codes (excluding BL12200)")
    
    st.subheader("🤖 AI Assistant")
    enable_ai_chat = st.checkbox("Enable BFM AI Assistant", value=False)
    
    # Built-in API configuration
    GOOGLE_API_KEY = "AIzaSyBynjotD4bpji6ThOtpO14tstc-qF2cFp4"
    PROJECT_ID = "bfm-analysis-project"  # Default project ID
    REGION = "us-central1"

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
    if start > end:
        return 0
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

def format_analysis_for_ai(extracted_data, benedicks_data, total_balance, monthly_personnel_cost, charging_strategy):
    context = {
        "financial_summary": {
            "total_balance": total_balance,
            "monthly_personnel_cost": monthly_personnel_cost,
            "omn_balance": extracted_data['omn']['balance'] if extracted_data else 0,
            "opn_balance": extracted_data['opn']['balance'] if extracted_data else 0,
            "scn_balance": extracted_data['scn']['balance'] if extracted_data else 0
        },
        "benedicks_portfolio": {
            "total_projects": benedicks_data['total_count'] if benedicks_data else 0,
            "total_value": benedicks_data['total_balance'] if benedicks_data else 0,
            "top_bl_codes": [bl[0] for bl in benedicks_data['bl_codes'][:5]] if benedicks_data and benedicks_data.get('bl_codes') else []
        },
        "charging_strategy": [
            {
                "phase": i+1,
                "appn": strategy['appn'],
                "urgency": strategy['urgency'],
                "amount": strategy['amount'],
                "timeframe": f"{strategy['start_date'].strftime('%b %Y')} - {strategy['end_date'].strftime('%b %Y')}"
            } for i, strategy in enumerate(charging_strategy[:3])
        ] if charging_strategy else []
    }
    return context

def call_google_ai_api(user_message, context, api_key, project_id, region):
    if not api_key or not project_id:
        return "Please configure your Google Cloud credentials in the sidebar."
    
    try:
        system_prompt = f"""You are a Budget and Financial Management (BFM) AI Assistant specializing in Navy appropriations and project funding. Current Analysis Context: {json.dumps(context, indent=2)}. You should answer questions about appropriations (OMN, OPN, SCN), funding balances, and charging strategies. Explain BFM concepts in clear, actionable terms. Provide strategic recommendations based on the current analysis. Help with budget planning and appropriation management. Reference specific data from the analysis when relevant. Keep responses concise but informative. Use military/Navy terminology appropriately."""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser Question: {user_message}"}]}],
            "generationConfig": {"temperature": 0.7, "topK": 40, "topP": 0.95, "maxOutputTokens": 1024}
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0 and 'content' in result['candidates'][0]:
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "I received an unexpected response. Please try again."
        else:
            return f"API Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error connecting to Google AI: {str(e)}"

def is_expiring_soon(report_date, expiry_date, months=2):
    warning_date = report_date + timedelta(days=months * 30)
    return expiry_date <= warning_date

def analyze_benedicks_portfolio(file):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        benedicks_data = df[benedicks_mask]
        if benedicks_data.empty: return None, "No Benedicks entries found", []
        
        non_bl12200_mask = ~benedicks_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        filtered_data = benedicks_data[non_bl12200_mask]
        if filtered_data.empty: return None, "All Benedicks entries are BL12200", []

        result = {'omn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0}, 'opn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0}, 'scn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0}, 'other': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0}}
        benedicks_projects, bl_code_summary = [], {}

        for _, row in filtered_data.iterrows():
            try:
                balance = float(str(row.iloc[16]).replace('$', '').replace(',', '').strip())
                appn, type_code, pm_name, bl_code, project_desc = str(row.iloc[2]).upper(), str(row.iloc[1]).upper().strip(), str(row.iloc[3]), str(row.iloc[7]), str(row.iloc[5])
                
                benedicks_projects.append({'PM': pm_name, 'APPN': appn, 'Type': type_code, 'Balance': balance, 'BL_Code': bl_code, 'Description': project_desc})
                
                if bl_code not in bl_code_summary: bl_code_summary[bl_code] = {'balance': 0.0, 'count': 0, 'types': {}}
                bl_code_summary[bl_code]['balance'] += balance
                bl_code_summary[bl_code]['count'] += 1
                if type_code not in bl_code_summary[bl_code]['types']: bl_code_summary[bl_code]['types'][type_code] = {'balance': 0.0, 'count': 0}
                bl_code_summary[bl_code]['types'][type_code]['balance'] += balance
                bl_code_summary[bl_code]['types'][type_code]['count'] += 1
                
                appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn' if 'OPN' in appn else 'other'
                result[appn_key]['balance'] += balance
                result[appn_key]['count'] += 1
                if type_code == 'L': result[appn_key]['L'] += balance
                elif type_code == 'M': result[appn_key]['M'] += balance
                elif type_code == 'T': result[appn_key]['T'] += balance
                else:
                    result[appn_key]['L'] += balance * 0.6
                    result[appn_key]['M'] += balance * 0.3
                    result[appn_key]['T'] += balance * 0.1
            except (ValueError, TypeError): continue
        
        benedicks_projects.sort(key=lambda x: x['Balance'], reverse=True)
        top_bl_codes = sorted(bl_code_summary.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
        total_balance = sum(v['balance'] for v in result.values())
        total_count = len(benedicks_projects)
        
        return {'summary': result, 'projects': benedicks_projects, 'bl_codes': top_bl_codes, 'total_balance': total_balance, 'total_count': total_count}, f"✅ Found {total_count} Benedicks projects (non-BL12200) worth ${total_balance:,.0f}", benedicks_projects
    except Exception as e:
        return None, f"❌ Error analyzing Benedicks portfolio: {str(e)}", []

def extract_vla_data(file, target_bl):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        bl_data = df[df.iloc[:, 7].astype(str).str.contains(target_bl, na=False)]
        if bl_data.empty: return None, f"No data found for {target_bl}", []

        result = {'omn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}, 'opn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}, 'scn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}}
        chargeable_objects = []

        for _, row in bl_data.iterrows():
            try:
                balance = float(str(row.iloc[16]).replace('$', '').replace(',', '').strip())
                if balance > 0:
                    appn, type_code, co_number = str(row.iloc[2]).upper(), str(row.iloc[1]).upper().strip(), str(row.iloc[3])
                    chargeable_objects.append({'CO_Number': co_number, 'APPN': appn, 'Type': type_code, 'Balance': balance})
                    appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
                    result[appn_key]['balance'] += balance
                    if type_code == 'L': result[appn_key]['L'] += balance
                    elif type_code == 'M': result[appn_key]['M'] += balance
                    elif type_code == 'T': result[appn_key]['T'] += balance
                    else:
                        result[appn_key]['L'] += balance * 0.6
                        result[appn_key]['M'] += balance * 0.3
                        result[appn_key]['T'] += balance * 0.1
            except (ValueError, TypeError): continue
        
        top_cos = sorted(chargeable_objects, key=lambda x: x['Balance'], reverse=True)[:5]
        return result, f"✅ Extracted data for {target_bl}", top_cos
    except Exception as e:
        return None, f"❌ Error: {str(e)}", []

def analyze_all_personal_funding(file):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        benedicks_data = df[benedicks_mask]
        if benedicks_data.empty: return None, "No Benedicks entries found", []

        non_bl12200_mask = ~benedicks_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        filtered_data = benedicks_data[non_bl12200_mask]
        if filtered_data.empty: return None, "All Benedicks entries are BL12200", []

        bl_code_analysis, all_projects = {}, []
        for _, row in filtered_data.iterrows():
            try:
                balance = float(str(row.iloc[16]).replace('$', '').replace(',', '').strip())
                appn, type_code, pm_name = str(row.iloc[2]).upper(), str(row.iloc[1]).upper().strip(), str(row.iloc[3])
                bl_code, project_desc, co_number = str(row.iloc[7]), str(row.iloc[5]), str(row.iloc[6])

                if bl_code not in bl_code_analysis:
                    bl_code_analysis[bl_code] = {'total_balance': 0.0, 'project_count': 0, 'appropriations': {'OMN': 0.0, 'OPN': 0.0, 'SCN': 0.0, 'OTHER': 0.0}, 'types': {'L': 0.0, 'M': 0.0, 'T': 0.0, 'OTHER': 0.0}, 'projects': []}
                
                bl_code_analysis[bl_code]['total_balance'] += balance
                bl_code_analysis[bl_code]['project_count'] += 1
                
                appn_key = 'OMN' if 'OMN' in appn else 'OPN' if 'OPN' in appn else 'SCN' if 'SCN' in appn else 'OTHER'
                bl_code_analysis[bl_code]['appropriations'][appn_key] += balance
                
                type_key = type_code if type_code in ['L', 'M', 'T'] else 'OTHER'
                bl_code_analysis[bl_code]['types'][type_key] += balance

                project_info = {'BL_Code': bl_code, 'CO_Number': co_number, 'APPN': appn, 'Type': type_code, 'Balance': balance, 'Description': project_desc, 'PM': pm_name}
                bl_code_analysis[bl_code]['projects'].append(project_info)
                all_projects.append(project_info)
            except (ValueError, TypeError): continue

        sorted_bl_codes = sorted(bl_code_analysis.items(), key=lambda x: x[1]['total_balance'], reverse=True)
        all_projects.sort(key=lambda x: x['Balance'], reverse=True)
        total_balance = sum(data['total_balance'] for _, data in sorted_bl_codes)
        
        return {'bl_code_analysis': sorted_bl_codes, 'all_projects': all_projects, 'total_balance': total_balance, 'total_projects': len(all_projects), 'bl_code_count': len(sorted_bl_codes)}, f"✅ Found {len(all_projects)} projects across {len(sorted_bl_codes)} BL codes worth ${total_balance:,.0f}", all_projects
    except Exception as e:
        return None, f"❌ Error analyzing personal funding: {str(e)}", []

# --- Initialize Session State ---
# (This block is kept for conceptual clarity, though Streamlit handles state persistence)
for key in ['extracted_data', 'last_bl_code', 'top_cos', 'benedicks_data', 'benedicks_projects', 'chat_history', 'analysis_context', 'chat_open', 'thinking']:
    if key not in st.session_state:
        st.session_state[key] = [] if 'projects' in key or 'history' in key else None

# --- Main UI and Logic ---
# (The UI sections for personal funding, Benedicks analysis, data input, etc. follow here as in your original script)

# Data Input Section
if uploaded_file:
    if st.session_state.last_bl_code != selected_bl:
        st.session_state.extracted_data, message, st.session_state.top_cos = extract_vla_data(uploaded_file, selected_bl)
        st.session_state.last_bl_code = selected_bl
        st.info(message)
    extracted_data = st.session_state.extracted_data
else:
    extracted_data = None

# Fallback to default values if no data is extracted
data_source = extracted_data if extracted_data else {
    'omn': {'balance': 44053.0, 'L': 44053.0, 'M': 0.0, 'T': 0.0},
    'opn': {'balance': 1947299.0, 'L': 1947299.0, 'M': 0.0, 'T': 0.0},
    'scn': {'balance': 1148438.0, 'L': 813595.0, 'M': 334843.0, 'T': 0.0}
}
# (The rest of the script continues...)

# --- Calculate Button and Analysis Display ---
if st.button("🚀 Calculate Analysis", type="primary"):
    # Core Calculations
    report_datetime = datetime.combine(report_date, datetime.min.time())
    omn_expiry, opn_expiry, scn_expiry = get_appropriation_expiry_date('OMN', fiscal_year), get_appropriation_expiry_date('OPN', fiscal_year), get_appropriation_expiry_date('SCN', fiscal_year)
    
    # Check for division by zero
    monthly_cost_denominator = hourly_rate * hours_per_week * 4.3 * branch_size
    monthly_personnel_cost = monthly_cost_denominator * (1 + overhead_rate / 100) if monthly_cost_denominator > 0 else 0
    total_balance = omn_balance + opn_balance + scn_balance

    # URGENT ALERTS... and the rest of the calculation logic
    # ... (All subsequent calculations and UI rendering from your original script go here)
    # The key change is to add checks before any division. For example:

    # In the Benedicks Portfolio Card
    avg_project_size = (total_balance / total_count) if total_count > 0 else 0
    personnel_months = (total_balance / monthly_personnel_cost) if monthly_personnel_cost > 0 else 0
    st.markdown(f"""
        ...
        <h4>Avg Project Size</h4>
        <h3>${avg_project_size:,.0f}</h3>
        ...
        <h4>Personnel Months</h4>
        <h3>{personnel_months:,.1f}</h3>
        ...
    """, unsafe_allow_html=True)
    
    # In Individual Appropriation Analysis
    personnel_months_appn = (balance / monthly_personnel_cost) if monthly_personnel_cost > 0 else 0
    st.markdown(f"""... <p>Personnel Months: {personnel_months_appn:.1f}</p> ...""", unsafe_allow_html=True)

    # In Combined Branch Coverage Analysis
    coverage_pct_dec30 = (total_hours_available_dec30 / total_hours_needed_dec30 * 100) if total_hours_needed_dec30 > 0 else 0
    
    # --- The rest of your display logic follows ---
    # This ensures no ZeroDivisionError will crash the script, and some output will always be rendered.

# Ensure the rest of your original script follows here to be complete.
# I've only shown the corrected parts and the start of the logic flow.

st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>My Little BFM</p></div>', unsafe_allow_html=True)
