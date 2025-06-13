import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import json
import requests

# --- Page Configuration ---
st.set_page_config(page_title="My Little BFM", page_icon="💰", layout="wide")

# --- CSS Styling ---
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
    bl_codes = ['BL16200', 'BL12200', 'BL10000', 'BL12000', 'BL12100', 'BL12300', 'BL31100', 'BL41000']
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
        return float(str(value).replace('$', '').replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0

def extract_vla_data(file, target_bl):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        bl_data = df[df.iloc[:, 8].astype(str).str.contains(target_bl, na=False)]
        
        if bl_data.empty: return None, f"No data found for {target_bl}", []
        
        result = {'omn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}, 'opn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}, 'scn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}}
        chargeable_objects = []
        
        for _, row in bl_data.iterrows():
            appn = str(row.iloc[2]).upper()
            type_code = str(row.iloc[1]).upper().strip()
            # CORRECTED: Use column 10 for "Balance"
            balance = parse_balance(row.iloc[10])
            
            if balance > 0:
                chargeable_objects.append({'CO_Number': str(row.iloc[5]), 'APPN': appn, 'Type': type_code, 'Balance': balance})

            appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
            result[appn_key]['balance'] += balance
            
            if type_code == 'L': result[appn_key]['L'] += balance
            elif type_code == 'M': result[appn_key]['M'] += balance
            elif type_code == 'T': result[appn_key]['T'] += balance

        top_cos = sorted(chargeable_objects, key=lambda x: x['Balance'], reverse=True)[:5]
        return result, f"✅ Extracted data for {target_bl}", top_cos
    except Exception as e:
        return None, f"❌ Error: {str(e)}", []

def analyze_benedicks_portfolio(file):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick|denovellis', na=False)
        benedicks_data = df[benedicks_mask]
        
        if benedicks_data.empty: return None, "No Benedicks/Denovellis entries found", []
        
        non_main_bl_mask = ~benedicks_data.iloc[:, 8].astype(str).str.contains(selected_bl, na=False)
        filtered_data = benedicks_data[non_main_bl_mask]
        
        if filtered_data.empty: return None, f"All Benedicks/Denovellis entries are within {selected_bl}", []
        
        result = {'omn': {'balance': 0.0, 'count': 0}, 'opn': {'balance': 0.0, 'count': 0}, 'scn': {'balance': 0.0, 'count': 0}, 'other': {'balance': 0.0, 'count': 0}}
        projects = []
        bl_code_summary = {}

        for _, row in filtered_data.iterrows():
            # CORRECTED: Use column 10 for "Balance"
            balance = parse_balance(row.iloc[10])
            if balance <= 0: continue

            appn = str(row.iloc[2]).upper()
            bl_code = str(row.iloc[8])
            
            projects.append({'APPN': appn, 'Balance': balance, 'BL_Code': bl_code, 'Description': str(row.iloc[5])})
            
            if bl_code not in bl_code_summary: bl_code_summary[bl_code] = {'balance': 0.0, 'count': 0}
            bl_code_summary[bl_code]['balance'] += balance
            bl_code_summary[bl_code]['count'] += 1
            
            appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn' if 'OPN' in appn else 'other'
            result[appn_key]['balance'] += balance
            result[appn_key]['count'] += 1

        total_balance = sum(item['balance'] for item in result.values())
        total_count = sum(item['count'] for item in result.values())
        
        return {
            'summary': result, 'projects': sorted(projects, key=lambda x: x['Balance'], reverse=True),
            'bl_codes': sorted(bl_code_summary.items(), key=lambda x: x[1]['balance'], reverse=True),
            'total_balance': total_balance, 'total_count': total_count
        }, f"✅ Found {total_count} external projects worth ${total_balance:,.0f}", projects
    except Exception as e:
        return None, f"❌ Error analyzing Benedicks portfolio: {str(e)}", []

def analyze_all_personal_funding(file):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick|denovellis', na=False)
        benedicks_data = df[benedicks_mask]

        if benedicks_data.empty: return None, "No Benedicks/Denovellis entries found", []

        exclude_mask = benedicks_data.iloc[:, 8].astype(str).str.contains(f'BL12200|{selected_bl}', na=False, regex=True)
        filtered_data = benedicks_data[~exclude_mask]

        if filtered_data.empty: return None, f"No other department projects found for Benedicks/Denovellis (outside of {selected_bl} and BL12200).", []

        bl_code_analysis = {}
        for _, row in filtered_data.iterrows():
            # CORRECTED: Use column 10 for "Balance"
            balance = parse_balance(row.iloc[10])
            if balance <= 0: continue
            
            bl_code = str(row.iloc[8])
            if bl_code not in bl_code_analysis:
                bl_code_analysis[bl_code] = {'total_balance': 0.0, 'project_count': 0, 'projects': []}
            
            bl_code_analysis[bl_code]['total_balance'] += balance
            bl_code_analysis[bl_code]['project_count'] += 1
            bl_code_analysis[bl_code]['projects'].append({'CO_Number': str(row.iloc[5]), 'Balance': balance, 'Description': str(row.iloc[4])})

        sorted_bl_codes = sorted(bl_code_analysis.items(), key=lambda x: x[1]['total_balance'], reverse=True)
        total_balance = sum(data['total_balance'] for _, data in sorted_bl_codes)
        total_projects = sum(data['project_count'] for _, data in sorted_bl_codes)

        return {
            'bl_code_analysis': sorted_bl_codes, 'total_balance': total_balance,
            'total_projects': total_projects, 'bl_code_count': len(sorted_bl_codes)
        }, f"✅ Found {total_projects} projects across {len(sorted_bl_codes)} other departments worth ${total_balance:,.0f}", []
    except Exception as e:
        return None, f"❌ Error analyzing personal funding: {str(e)}", []

# --- AI Integration ---
def format_analysis_for_ai(extracted_data, benedicks_data, total_balance, monthly_personnel_cost, charging_strategy):
    context = {
        "financial_summary": { "total_balance": total_balance, "monthly_personnel_cost": monthly_personnel_cost, },
        "charging_strategy": charging_strategy, "benedicks_portfolio": {}
    }
    if extracted_data:
        context["financial_summary"].update({
            "omn_balance": extracted_data['omn']['balance'], "opn_balance": extracted_data['opn']['balance'], "scn_balance": extracted_data['scn']['balance']
        })
    if benedicks_data:
        context["benedicks_portfolio"].update({
            "total_projects": benedicks_data['total_count'], "total_value": benedicks_data['total_balance'],
            "top_bl_codes": [bl[0] for bl in benedicks_data['bl_codes'][:3]] if benedicks_data.get('bl_codes') else []
        })
    return context

def call_google_ai_api(user_message, context, api_key):
    if not api_key: return "The Google AI API key is not configured. Please add it to the script."
    
    # CORRECTED: Helper function to convert datetime objects for JSON
    def json_converter(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()

    try:
        # CORRECTED: Use the json_converter in the dumps call
        api_context_json = json.dumps(context, indent=2, default=json_converter)
        
        system_prompt = f"""You are a Budget and Financial Management (BFM) AI Assistant specializing in Navy appropriations. 
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
        return "Received an unexpected response from the AI. Please try again."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# --- Session State Initialization ---
if 'extracted_data' not in st.session_state: st.session_state.extracted_data = None
if 'last_bl_code' not in st.session_state: st.session_state.last_bl_code = None
if 'benedicks_data' not in st.session_state: st.session_state.benedicks_data = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'analysis_context' not in st.session_state: st.session_state.analysis_context = {}

# --- Main Application ---
if uploaded_file:
    if st.session_state.last_bl_code != selected_bl:
        extracted_data, message, _ = extract_vla_data(uploaded_file, selected_bl)
        st.session_state.extracted_data = extracted_data
        st.session_state.last_bl_code = selected_bl
        st.info(message)
    
    if enable_personal_funding:
        st.markdown("### 💼 Complete Personal Funding Analysis (Other Departments)")
        st.info(f"💡 Analyzing all projects where you are PM, excluding your main department ({selected_bl}) and managed funds (BL12200).")
        personal_analysis, personal_message, _ = analyze_all_personal_funding(uploaded_file)
        if personal_analysis:
            st.success(personal_message)
            for i, (bl_code, bl_data) in enumerate(personal_analysis['bl_code_analysis']):
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #e67e22aa, #d35400dd); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <h5>#{i+1}: {bl_code} (Other Dept)</h5>
                    <p><strong>Total Balance:</strong> ${bl_data["total_balance"]:,.0f} | <strong>Projects:</strong> {bl_data["project_count"]}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning(personal_message)

    if enable_pm_analysis:
        st.markdown("### 👨‍💼 Benedicks/Denovellis External Portfolio Analysis")
        benedicks_analysis, benedicks_message, _ = analyze_benedicks_portfolio(uploaded_file)
        st.session_state.benedicks_data = benedicks_analysis
        if benedicks_analysis:
            st.success(benedicks_message)
            st.markdown(f"""
            <div class="pm-analysis-card">
                <h3>External Portfolio Summary</h3>
                <p><strong>Total Projects:</strong> {benedicks_analysis['total_count']} | <strong>Total Value:</strong> ${benedicks_analysis['total_balance']:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(benedicks_message)

# --- Data Input & Calculation ---
st.markdown(f"--- \n### 💰 Main Analysis for {selected_bl}")

extracted_data = st.session_state.get('extracted_data')
defaults = {
    'omn': {'balance': 44053.0, 'L': 44053.0, 'M': 0.0, 'T': 0.0},
    'opn': {'balance': 1947299.0, 'L': 1947299.0, 'M': 0.0, 'T': 0.0},
    'scn': {'balance': 1148438.0, 'L': 813595.0, 'M': 334843.0, 'T': 0.0}
}
data_source = extracted_data if extracted_data else defaults

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
    omn_balance = st.number_input("OMN Balance ($)", value=data_source['omn']['balance'])
with col2:
    st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
    opn_balance = st.number_input("OPN Balance ($)", value=data_source['opn']['balance'])
with col3:
    st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
    scn_balance = st.number_input("SCN Balance ($)", value=data_source['scn']['balance'])

if st.button("🚀 Calculate Full Analysis", type="primary"):
    report_datetime = datetime.combine(report_date, datetime.min.time())
    monthly_personnel_cost = hourly_rate * hours_per_week * 4.3 * branch_size * (1 + overhead_rate / 100) if (hourly_rate * hours_per_week * branch_size) > 0 else 1
    total_balance = omn_balance + opn_balance + scn_balance

    appn_data = [
        {"name": "OMN", "balance": omn_balance, "expiry": get_appropriation_expiry_date('OMN', fiscal_year)},
        {"name": "OPN", "balance": opn_balance, "expiry": get_appropriation_expiry_date('OPN', fiscal_year)},
        {"name": "SCN", "balance": scn_balance, "expiry": get_appropriation_expiry_date('SCN', fiscal_year)}
    ]
    appn_data.sort(key=lambda x: x['expiry'])
    
    st.markdown('<div class="bubble"><h3>💡 Smart APPN Charging Strategy</h3></div>', unsafe_allow_html=True)
    
    charging_strategy = []
    cumulative_months_funded = 0
    for appn in appn_data:
        if appn['balance'] > 0:
            months_covered = appn['balance'] / monthly_personnel_cost
            start_date = report_datetime + timedelta(days=cumulative_months_funded * 30.5)
            end_date = start_date + timedelta(days=months_covered * 30.5)
            days_to_expiry = (appn['expiry'] - report_datetime).days
            card_class = "urgent-expiry" if is_expiring_soon(report_datetime, appn['expiry']) else "status-card"
            
            charging_strategy.append({
                'appn': appn['name'], 'amount': appn['balance'], 'months': months_covered,
                'start_date': start_date, 'end_date': end_date, 'expiry_date': appn['expiry']
            })

            st.markdown(f"""
            <div class="{card_class}" style="background: linear-gradient(135deg, #2c3e50, #466368);">
                <h4>Charge to {appn['name']}</h4>
                <p><strong>Funding:</strong> ${appn['balance']:,.0f} | <strong>Covers:</strong> {months_covered:.1f} months</p>
                <p><strong>Timeframe:</strong> {start_date.strftime("%b %Y")} → {end_date.strftime("%b %Y")}</p>
                <p><strong>Expires:</strong> {appn['expiry'].strftime("%b %d, %Y")} ({days_to_expiry} days)</p>
            </div>
            """, unsafe_allow_html=True)
            cumulative_months_funded += months_covered

    st.markdown("### 📉 Funding Burn Down")
    if charging_strategy:
        burn_down_df = pd.DataFrame(charging_strategy)
        burn_down_df['cumulative_balance'] = burn_down_df['amount'].cumsum()

        fig_burn = go.Figure()
        fig_burn.add_trace(go.Scatter(x=burn_down_df['end_date'], y=total_balance - burn_down_df['cumulative_balance'],
                                    mode='lines+markers', name='Remaining Balance', line=dict(shape='spline')))
        fig_burn.update_layout(title='Projected Funding Burn Down', xaxis_title='Date', yaxis_title='Remaining Balance ($)')
        st.plotly_chart(fig_burn, use_container_width=True)

    st.session_state.analysis_context = format_analysis_for_ai(
        extracted_data, st.session_state.benedicks_data, total_balance, monthly_personnel_cost, charging_strategy)

# --- BFM AI Assistant ---
if enable_ai_chat:
    st.markdown("--- \n### 🤖 BFM AI Assistant")
    if not GOOGLE_API_KEY:
        st.error("The Google AI API key is missing. The chat assistant is disabled.")
    else:
        for role, message in st.session_state.chat_history:
            with st.chat_message(role):
                st.markdown(message)
        
        if prompt := st.chat_input("Ask about your financial data..."):
            st.session_state.chat_history.append(("user", prompt))
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Thinking..."):
                    response = call_google_ai_api(prompt, st.session_state.analysis_context, GOOGLE_API_KEY)
                    st.markdown(response)
            
            st.session_state.chat_history.append(("assistant", response))

# --- Footer ---
st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>🚀 My Little BFM • Enhanced with Smart APPN Charging & Portfolio Analysis</p></div>', unsafe_allow_html=True)
