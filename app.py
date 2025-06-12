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
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🚀 My Little BFM</h1><p>Budget & Financial Management System</p></div>', unsafe_allow_html=True)

# --- Functions (No Changes Here) ---
def get_federal_holidays(fiscal_year):
    holidays = []
    if fiscal_year == 2025:
        holidays = [datetime(2024, 10, 14), datetime(2024, 11, 11), datetime(2024, 11, 28), 
                    datetime(2024, 11, 29), datetime(2024, 12, 25), datetime(2025, 1, 1),
                    datetime(2025, 1, 20), datetime(2025, 2, 17), datetime(2025, 5, 26),
                    datetime(2025, 6, 19), datetime(2025, 7, 4), datetime(2025, 9, 1)]
    return holidays

def count_working_days(start, end, fiscal_year):
    if start > end: return 0
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
        return datetime(fiscal_year + 1, 9, 30)
    elif 'SCN' in appn.upper():
        return datetime(fiscal_year + 2, 9, 30)
    else:
        return datetime(fiscal_year, 9, 30)

def is_expiring_soon(report_date, expiry_date, months=2):
    return expiry_date <= report_date + timedelta(days=months * 30.5)

def analyze_benedicks_portfolio(file):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        benedicks_data = df[benedicks_mask]
        if benedicks_data.empty: return None, "No Benedicks entries found", []
        
        non_bl12200_mask = ~benedicks_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        filtered_data = benedicks_data[non_bl12200_mask]
        if filtered_data.empty: return None, "All Benedicks entries are BL12200", []

        result = {'omn': {}, 'opn': {}, 'scn': {}, 'other': {}}
        for k in result: result[k] = {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0}
        
        benedicks_projects, bl_code_summary = [], {}
        for _, row in filtered_data.iterrows():
            try:
                balance = float(str(row.iloc[16]).replace('$', '').replace(',', '').strip())
                if balance == 0: continue
                appn, type_code, pm, bl, desc = str(row.iloc[2]), str(row.iloc[1]), str(row.iloc[3]), str(row.iloc[7]), str(row.iloc[5])
                
                benedicks_projects.append({'PM': pm, 'APPN': appn, 'Type': type_code, 'Balance': balance, 'BL_Code': bl, 'Description': desc})
                
                if bl not in bl_code_summary: bl_code_summary[bl] = {'balance': 0.0, 'count': 0, 'types': {}}
                bl_code_summary[bl]['balance'] += balance
                bl_code_summary[bl]['count'] += 1
                if type_code not in bl_code_summary[bl]['types']: bl_code_summary[bl]['types'][type_code] = {'balance': 0.0, 'count': 0}
                bl_code_summary[bl]['types'][type_code]['balance'] += balance
                bl_code_summary[bl]['types'][type_code]['count'] += 1
                
                key = 'omn' if 'OMN' in appn.upper() else 'scn' if 'SCN' in appn.upper() else 'opn' if 'OPN' in appn.upper() else 'other'
                result[key]['balance'] += balance
                result[key]['count'] += 1
                
                if type_code == 'L': result[key]['L'] += balance
                elif type_code == 'M': result[key]['M'] += balance
                elif type_code == 'T': result[key]['T'] += balance
                else: result[key]['L'] += balance * 0.6; result[key]['M'] += balance * 0.3; result[key]['T'] += balance * 0.1
            except (ValueError, TypeError): continue
            
        benedicks_projects.sort(key=lambda x: x['Balance'], reverse=True)
        total_balance = sum(v['balance'] for v in result.values())
        return {'summary': result, 'projects': benedicks_projects, 'bl_codes': sorted(bl_code_summary.items(), key=lambda x: x[1]['balance'], reverse=True)[:10], 'total_balance': total_balance, 'total_count': len(benedicks_projects)}, f"✅ Found {len(benedicks_projects)} projects worth ${total_balance:,.0f}", benedicks_projects
    except Exception as e: return None, f"❌ Error: {e}", []

def extract_vla_data(file, target_bl):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        bl_data = df[df.iloc[:, 7].astype(str).str.contains(target_bl, na=False)]
        if bl_data.empty: return None, f"No data for {target_bl}", []

        result = {'omn': {}, 'opn': {}, 'scn': {}}
        for k in result: result[k] = {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}
        chargeable_objects = []

        for _, row in bl_data.iterrows():
            try:
                balance = float(str(row.iloc[16]).replace('$', '').replace(',', '').strip())
                if balance > 0:
                    appn, type_code, co = str(row.iloc[2]), str(row.iloc[1]), str(row.iloc[3])
                    chargeable_objects.append({'CO_Number': co, 'APPN': appn, 'Type': type_code, 'Balance': balance})
                    key = 'omn' if 'OMN' in appn.upper() else 'scn' if 'SCN' in appn.upper() else 'opn'
                    result[key]['balance'] += balance
                    if type_code == 'L': result[key]['L'] += balance
                    elif type_code == 'M': result[key]['M'] += balance
                    elif type_code == 'T': result[key]['T'] += balance
                    else: result[key]['L']+=balance*0.6; result[key]['M']+=balance*0.3; result[key]['T']+=balance*0.1
            except (ValueError, TypeError): continue
        return result, f"✅ Extracted data for {target_bl}", sorted(chargeable_objects, key=lambda x: x['Balance'], reverse=True)[:5]
    except Exception as e: return None, f"❌ Error: {e}", []

# --- Sidebar and Session State (Moved to top for clarity) ---
with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("📊 Upload VLA Excel", type=['xlsx', 'xls'])
    st.subheader("👥 Personnel")
    branch_size = st.number_input("Branch Size", min_value=1, value=17)
    hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.01, value=141.36, step=0.01)
    # ... other sidebar items
    fiscal_year = st.selectbox("Select Fiscal Year", [2024, 2025, 2026, 2027], index=1)
    selected_bl = st.selectbox("BL Code", ['BL12200', 'BL10000', 'BL12000', 'BL12100', 'BL12300', 'BL16200', 'BL31100', 'BL41000'])
    enable_pm_analysis = st.checkbox("Enable Benedicks Portfolio Analysis", value=False)


# Initialize session state
for key in ['extracted_data', 'last_bl_code', 'top_cos', 'benedicks_data', 'benedicks_projects']:
    if key not in st.session_state:
        st.session_state[key] = None if 'data' in key else []

# --- Main App Body ---

# Data Input Section - This MUST run before the button to define the variables
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

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
    omn_balance = st.number_input("OMN Balance ($)", value=float(data_source['omn']['balance']))
    omn_l = st.number_input("OMN Labor ($)", value=float(data_source['omn']['L']))
    omn_m = st.number_input("OMN Material ($)", value=float(data_source['omn']['M']))
    omn_t = st.number_input("OMN Travel ($)", value=float(data_source['omn']['T']))

with col2:
    st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
    opn_balance = st.number_input("OPN Balance ($)", value=float(data_source['opn']['balance']))
    opn_l = st.number_input("OPN Labor ($)", value=float(data_source['opn']['L']))
    opn_m = st.number_input("OPN Material ($)", value=float(data_source['opn']['M']))
    opn_t = st.number_input("OPN Travel ($)", value=float(data_source['opn']['T']))

with col3:
    st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
    scn_balance = st.number_input("SCN Balance ($)", value=float(data_source['scn']['balance']))
    scn_l = st.number_input("SCN Labor ($)", value=float(data_source['scn']['L']))
    scn_m = st.number_input("SCN Material ($)", value=float(data_source['scn']['M']))
    scn_t = st.number_input("SCN Travel ($)", value=float(data_source['scn']['T']))

# The "Calculate Analysis" button and all logic that USES the input variables
# has been moved inside this block to prevent the NameError.
if st.button("🚀 Calculate Analysis", type="primary"):
    
    # --- All calculations are now safely inside this block ---
    report_datetime = datetime.combine(report_date, datetime.min.time())
    
    # Perform all calculations using the 'omn_balance', 'opn_balance', etc. variables defined above
    total_balance = omn_balance + opn_balance + scn_balance
    
    monthly_personnel_cost = hourly_rate * hours_per_week * 4.3 * branch_size * (1 + overhead_rate / 100)

    # ... (The rest of your calculation and display logic from the original script) ...
    # ... (This includes the URGENT ALERTS, SMART APPN CHARGING STRATEGY, etc.) ...
    
    # Example of a corrected calculation to prevent division by zero
    st.markdown("### 🎯 Combined Branch Coverage Analysis (to Dec 30)")
    dec_30_date = datetime(fiscal_year, 12, 30)
    working_days_to_dec30 = count_working_days(report_datetime, dec_30_date, fiscal_year)
    total_hours_needed_dec30 = working_days_to_dec30 * 8 * branch_size
    total_hours_available_dec30 = total_balance / hourly_rate if hourly_rate > 0 else 0
    total_hours_excess_dec30 = total_hours_available_dec30 - total_hours_needed_dec30
    coverage_pct_dec30 = (total_hours_available_dec30 / total_hours_needed_dec30 * 100) if total_hours_needed_dec30 > 0 else 0

    # Displaying the results...
    if coverage_pct_dec30 >= 100:
        status_color, status_text, status_message = "#27ae60", "✅ FULLY COVERED", "Branch operations secured through Dec 30"
    elif coverage_pct_dec30 >= 80:
        status_color, status_text, status_message = "#f39c12", "⚠️ CAUTION", "Adequate coverage but monitor closely"
    else:
        status_color, status_text, status_message = "#e74c3c", "🚨 CRITICAL", "Insufficient funding for full branch operations"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {status_color}aa, {status_color}dd); color: white; padding: 2rem; border-radius: 15px; margin: 1rem 0; text-align: center;">
        <h2>🎯 BRANCH OPERATIONS STATUS: {status_text}</h2>
        <h3>{status_message}</h3>
        </div>
    """, unsafe_allow_html=True)

    # ALL of your other st.markdown, st.metric, and st.plotly_chart calls for displaying results go here.
    
st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>My Little BFM</p></div>', unsafe_allow_html=True)
