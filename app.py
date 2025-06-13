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

def analyze_entire_portfolio(file):
    """Analyzes the entire portfolio for the specified PMs."""
    try:
        df = pd.read_excel(file, sheet_name=0, header=2)
        pm_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick|denovellis', na=False)
        portfolio_df = df[pm_mask]

        if portfolio_df.empty:
            return None
        
        results = {
            "total_balance": 0.0,
            "total_projects": 0,
            "balance_by_appn": {},
            "balance_by_status": {},
            "expiring_soon": []
        }

        report_datetime = datetime.combine(report_date, datetime.min.time())

        for _, row in portfolio_df.iterrows():
            balance = parse_balance(row.iloc[16])
            if balance <= 0:
                continue

            results["total_projects"] += 1
            results["total_balance"] += balance
            
            appn = str(row.iloc[2]).upper()
            status = str(row.iloc[27]).upper().strip()
            
            # Aggregate by APPN
            appn_key = 'OMN' if 'OMN' in appn else 'SCN' if 'SCN' in appn else 'OPN' if 'OPN' in appn else 'OTHER'
            results["balance_by_appn"][appn_key] = results["balance_by_appn"].get(appn_key, 0) + balance

            # Aggregate by Status
            if status:
                results["balance_by_status"][status] = results["balance_by_status"].get(status, 0) + balance
            
            # Check for expiring funds
            expiry_date = get_appropriation_expiry_date(appn, fiscal_year)
            if is_expiring_soon(report_datetime, expiry_date) and appn_key != 'SCN':
                results["expiring_soon"].append({
                    "appn": appn,
                    "project": str(row.iloc[5]),
                    "balance": balance,
                    "days_left": (expiry_date - report_datetime).days
                })
        
        return results

    except Exception as e:
        st.error(f"Error analyzing full portfolio: {e}")
        return None

def generate_bfm_summary_and_email(portfolio_data):
    """Generates a detailed analysis and a draft email using the AI model."""
    if not GOOGLE_API_KEY:
        return "Error: Google AI API Key is not configured in the sidebar."

    def json_converter(o):
        if isinstance(o, (datetime, date, timedelta)):
            return str(o)

    context_json = json.dumps(portfolio_data, indent=2, default=json_converter)

    system_prompt = f"""
    You are a Senior BFM (Budget & Financial Management) Analyst for a US Navy program office.
    Your task is to analyze the provided financial data and generate a two-part report for your Branch Head, Gene.

    **Current Portfolio Data:**
    ```json
    {context_json}
    ```

    **Instructions:**
    Provide your response in two distinct sections, using Markdown for formatting.

    **Part 1: Detailed Analysis**
    - Start with the header `## Detailed Analysis`.
    - Provide a bullet-point summary of the portfolio's financial health.
    - Cover these key areas:
      - **Overall Position:** State the total balance and number of projects.
      - **Funding Breakdown:** Briefly list the balance for each major appropriation (SCN, OPN, OMN).
      - **Key Risks:** Identify the most significant risks. Focus on:
        - Any funds expiring soon (especially OMN and OPN).
        - The total amount of money currently on 'HOLD'.
      - **Opportunities:** Point out any strengths, such as a healthy SCN balance for long-term work.
      - **Recommended Charging Strategy:** Based on the data, recommend which appropriation should be prioritized for spending and why (e.g., "Prioritize spending the remaining OMN funds due to their imminent expiration.").

    **Part 2: Draft Email to Branch Head**
    - Start with the header `## Draft Email to Branch Head`.
    - Create a professional, concise email to "Gene" that summarizes the situation.
    - Use the following format:

    **Subject:** Weekly Financial Status & Spending Strategy for {date.today().strftime('%Y-%m-%d')}

    **Gene,**

    **BLUF:** [Provide a one-sentence "Bottom Line Up Front" summarizing the overall financial health - e.g., "We are in a strong financial position," or "We have an urgent risk with expiring OMN funds."]

    Here is the summary of our current financial posture:
    *   **Total Balance:** [Formatted total balance] across [Number] projects.
    *   **By Appropriation:**
        *   SCN: [Formatted SCN balance]
        *   OPN: [Formatted OPN balance]
        *   OMN: [Formatted OMN balance]
    *   **Key Risk:** We have [Formatted HOLD balance] currently on HOLD, and [Formatted expiring balance] in funds expiring within the next 60 days.

    **Recommendation:**
    [State the recommended charging strategy clearly and concisely. For example: "I recommend we prioritize charging all applicable labor to our remaining OMN funds to ensure they are fully utilized before the end-of-year deadline."]

    Please let me know if you would like to discuss this further.

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

# --- Session State and Main App Body ---
# (The rest of the script is largely the same, but with the new button added)

if uploaded_file:
    if st.session_state.last_bl_code != selected_bl or st.session_state.extracted_data is None:
        st.session_state.extracted_data, message, _ = extract_vla_data(uploaded_file, selected_bl)
        st.session_state.last_bl_code = selected_bl
        st.info(message)

st.markdown(f"--- \n### 💰 Main Analysis for {selected_bl}")
data_source = st.session_state.get('extracted_data') or defaults

# Data input fields for main analysis...
# ... (This section is unchanged)

# --- NEW AI ANALYSIS SECTION ---
st.markdown("---")
st.markdown("### 🤖 AI-Powered Full Portfolio Summary")
if st.button("Generate AI Analysis & Email Draft"):
    if uploaded_file:
        with st.spinner("Analyzing entire portfolio and generating report..."):
            portfolio_data = analyze_entire_portfolio(uploaded_file)
            if portfolio_data:
                ai_response = generate_bfm_summary_and_email(portfolio_data)
                st.markdown(ai_response)
            else:
                st.warning("Could not find any projects for the specified PMs in the file.")
    else:
        st.error("Please upload an Excel file first.")

# --- BFM AI Assistant Chat ---
# ... (This section is unchanged)
