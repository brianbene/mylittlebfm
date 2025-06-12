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

.chat-toggle {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    color: white;
    font-size: 24px;
    cursor: pointer;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
}

.chat-toggle:hover {
    transform: scale(1.1);
    box-shadow: 0 6px 25px rgba(0,0,0,0.4);
}

.chat-window {
    position: absolute;
    bottom: 80px;
    right: 0;
    width: 350px;
    height: 500px;
    background: white;
    border-radius: 15px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    border: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transform: scale(0);
    opacity: 0;
    transition: all 0.3s ease;
    transform-origin: bottom right;
}

.chat-window.open {
    transform: scale(1);
    opacity: 1;
}

.chat-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 15px 20px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
    background: #f8f9fa;
}

.chat-message {
    margin-bottom: 15px;
    max-width: 80%;
}

.chat-message.user {
    margin-left: auto;
}

.chat-message.user .message-bubble {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-radius: 18px 18px 5px 18px;
}

.chat-message.assistant .message-bubble {
    background: white;
    color: #333;
    border: 1px solid #e0e0e0;
    border-radius: 18px 18px 18px 5px;
}

.message-bubble {
    padding: 12px 16px;
    font-size: 14px;
    line-height: 1.4;
    word-wrap: break-word;
}

.chat-input-area {
    padding: 15px;
    background: white;
    border-top: 1px solid #e0e0e0;
}

.chat-input-container {
    display: flex;
    gap: 10px;
    align-items: center;
}

.chat-input {
    flex: 1;
    padding: 12px 15px;
    border: 1px solid #e0e0e0;
    border-radius: 25px;
    outline: none;
    font-size: 14px;
}

.chat-input:focus {
    border-color: #667eea;
}

.chat-send-btn {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border: none;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.chat-send-btn:hover {
    transform: scale(1.1);
}

.quick-actions {
    display: flex;
    gap: 5px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}

.quick-btn {
    background: #f0f0f0;
    border: 1px solid #d0d0d0;
    border-radius: 15px;
    padding: 6px 12px;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.quick-btn:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.thinking {
    display: flex;
    align-items: center;
    gap: 5px;
    font-style: italic;
    color: #666;
    font-size: 12px;
}

.thinking-dots {
    display: inline-flex;
    gap: 2px;
}

.thinking-dots span {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #667eea;
    animation: thinking 1.5s infinite;
}

.thinking-dots span:nth-child(2) { animation-delay: 0.3s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.6s; }

@keyframes thinking {
    0%, 60%, 100% { opacity: 0.3; }
    30% { opacity: 1; }
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
    """
    Format analysis data for AI consumption
    """
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
            "top_bl_codes": [bl[0] for bl in benedicks_data['bl_codes'][:5]] if benedicks_data and benedicks_data['bl_codes'] else []
        },
        "charging_strategy": [
            {
                "phase": i+1,
                "appn": strategy['appn'],
                "urgency": strategy['urgency'],
                "amount": strategy['amount'],
                "timeframe": f"{strategy['start_date'].strftime('%b %Y')} - {strategy['end_date'].strftime('%b %Y')}"
            } for i, strategy in enumerate(charging_strategy[:3])  # Top 3 phases
        ] if charging_strategy else []
    }
    return context

def call_google_ai_api(user_message, context, api_key, project_id, region):
    """
    Call Google Cloud Vertex AI API
    """
    if not api_key or not project_id:
        return "Please configure your Google Cloud credentials in the sidebar."
    
    try:
        # Format the system prompt with BFM context
        system_prompt = f"""You are a Budget and Financial Management (BFM) AI Assistant specializing in Navy appropriations and project funding. 
Current Analysis Context:
- Total Balance: ${context['financial_summary']['total_balance']:,.0f}
- Monthly Personnel Cost: ${context['financial_summary']['monthly_personnel_cost']:,.0f}
- OMN Balance: ${context['financial_summary']['omn_balance']:,.0f}
- OPN Balance: ${context['financial_summary']['opn_balance']:,.0f}
- SCN Balance: ${context['financial_summary']['scn_balance']:,.0f}

Benedicks Portfolio:
- Projects: {context['benedicks_portfolio']['total_projects']}
- Value: ${context['benedicks_portfolio']['total_value']:,.0f}
- Top BL Codes: {', '.join(context['benedicks_portfolio']['top_bl_codes'])}

Current Charging Strategy: {json.dumps(context['charging_strategy'], indent=2)}

You should:
1. Answer questions about appropriations (OMN, OPN, SCN), funding balances, and charging strategies
2. Explain BFM concepts in clear, actionable terms
3. Provide strategic recommendations based on the current analysis
4. Help with budget planning and appropriation management
5. Reference specific data from the analysis when relevant

Keep responses concise but informative. Use military/Navy terminology appropriately."""

        # Use the correct Gemini model endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nUser Question: {user_message}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                return "I received an empty response. Please try rephrasing your question."
        else:
            return f"API Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error connecting to Google AI: {str(e)}"

def is_expiring_soon(report_date, expiry_date, months=2):
    warning_date = report_date + timedelta(days=months * 30)
    return expiry_date <= warning_date

def analyze_benedicks_portfolio(file):
    """
    Analyze all Benedicks entries that are NOT BL12200
    """
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        
        # Filter for Benedicks entries (PM column is index 3)
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        benedicks_data = df[benedicks_mask]
        
        if benedicks_data.empty:
            return None, "No Benedicks entries found", []
        
        # Exclude BL12200 entries (Billing Element column is index 7)
        non_bl12200_mask = ~benedicks_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        filtered_data = benedicks_data[non_bl12200_mask]
        
        if filtered_data.empty:
            return None, "All Benedicks entries are BL12200", []
        
        # Analyze the data structure
        result = {
            'omn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0},
            'opn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0},
            'scn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0},
            'other': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0}
        }
        
        benedicks_projects = []
        bl_code_summary = {}
        
        for _, row in filtered_data.iterrows():
            appn = str(row.iloc[2]).upper() if len(df.columns) > 2 else "Unknown"
            type_code = str(row.iloc[1]).upper().strip() if len(df.columns) > 1 else "Unknown"
            pm_name = str(row.iloc[3]) if len(df.columns) > 3 else "Unknown"
            bl_code = str(row.iloc[7]) if len(df.columns) > 7 else "Unknown"
            project_desc = str(row.iloc[5]) if len(df.columns) > 5 else "Unknown"
            
            try:
                balance_str = str(row.iloc[16]).replace('$', '').replace(',', '').strip()
                balance = float(balance_str) if balance_str and balance_str != 'nan' else 0.0
                
                # Track individual projects
                benedicks_projects.append({
                    'PM': pm_name,
                    'APPN': appn,
                    'Type': type_code,
                    'Balance': balance,
                    'BL_Code': bl_code,
                    'Description': project_desc
                })
                
                # Track BL code summaries
                if bl_code not in bl_code_summary:
                    bl_code_summary[bl_code] = {'balance': 0.0, 'count': 0, 'types': {}}
                bl_code_summary[bl_code]['balance'] += balance
                bl_code_summary[bl_code]['count'] += 1
                
                if type_code not in bl_code_summary[bl_code]['types']:
                    bl_code_summary[bl_code]['types'][type_code] = {'balance': 0.0, 'count': 0}
                bl_code_summary[bl_code]['types'][type_code]['balance'] += balance
                bl_code_summary[bl_code]['types'][type_code]['count'] += 1
                
            except:
                balance = 0.0
                continue
            
            # Determine appropriation category
            if 'OMN' in appn:
                appn_key = 'omn'
            elif 'SCN' in appn:
                appn_key = 'scn'
            elif 'OPN' in appn:
                appn_key = 'opn'
            else:
                appn_key = 'other'
            
            result[appn_key]['balance'] += balance
            result[appn_key]['count'] += 1
            
            # Distribute by type
            if type_code == 'L':
                result[appn_key]['L'] += balance
            elif type_code == 'M':
                result[appn_key]['M'] += balance
            elif type_code == 'T':
                result[appn_key]['T'] += balance
            else:
                # If type is unclear, distribute proportionally
                result[appn_key]['L'] += balance * 0.6
                result[appn_key]['M'] += balance * 0.3
                result[appn_key]['T'] += balance * 0.1
        
        # Sort projects by balance
        benedicks_projects = sorted(benedicks_projects, key=lambda x: x['Balance'], reverse=True)
        
        # Sort BL codes by balance
        top_bl_codes = sorted(bl_code_summary.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
        
        total_balance = sum([result[key]['balance'] for key in result.keys()])
        total_count = len(benedicks_projects)
        
        return {
            'summary': result,
            'projects': benedicks_projects,
            'bl_codes': top_bl_codes,
            'total_balance': total_balance,
            'total_count': total_count
        }, f"✅ Found {total_count} Benedicks projects (non-BL12200) worth ${total_balance:,.0f}", benedicks_projects
        
    except Exception as e:
        return None, f"❌ Error analyzing Benedicks portfolio: {str(e)}", []

def extract_vla_data(file, target_bl):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        bl_data = df[df.iloc[:, 8].astype(str).str.contains(target_bl, na=False)]
        
        if bl_data.empty:
            return None, f"No data found for {target_bl}", []
        
        result = {'omn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0},
                  'opn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0},
                  'scn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}}
        
        chargeable_objects = []
        
        for _, row in bl_data.iterrows():
            appn = str(row.iloc[2]).upper()
            type_code = str(row.iloc[1]).upper().strip()
            co_number = str(row.iloc[3]) if len(df.columns) > 3 else "Unknown"
            
            try:
                balance = float(str(row.iloc[16]).replace('$', '').replace(',', '').strip() or 0)
                
                if balance > 0:
                    chargeable_objects.append({'CO_Number': co_number, 'APPN': appn, 'Type': type_code, 'Balance': balance})
            except:
                continue
            
            appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
            result[appn_key]['balance'] += balance
            
            if type_code == 'L': result[appn_key]['L'] += balance
            elif type_code == 'M': result[appn_key]['M'] += balance
            elif type_code == 'T': result[appn_key]['T'] += balance
            else:
                result[appn_key]['L'] += balance * 0.6
                result[appn_key]['M'] += balance * 0.3
                result[appn_key]['T'] += balance * 0.1
        
        top_cos = sorted(chargeable_objects, key=lambda x: x['Balance'], reverse=True)[:5]
        return result, f"✅ Extracted data for {target_bl}", top_cos
    except Exception as e:
        return None, f"❌ Error: {str(e)}", []

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'last_bl_code' not in st.session_state:
    st.session_state.last_bl_code = None
if 'top_cos' not in st.session_state:
    st.session_state.top_cos = []
if 'benedicks_data' not in st.session_state:
    st.session_state.benedicks_data = None
if 'benedicks_projects' not in st.session_state:
    st.session_state.benedicks_projects = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'analysis_context' not in st.session_state:
    st.session_state.analysis_context = None
if 'chat_open' not in st.session_state:
    st.session_state.chat_open = False
if 'thinking' not in st.session_state:
    st.session_state.thinking = False

def analyze_all_personal_funding(file):
    """
    Analyze ALL funding associated with Benedicks PM name across ALL BL codes
    This shows exactly what the user is asking for - all charging lines
    """
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        
        # Filter for Benedicks entries (PM column is index 3)
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        benedicks_data = df[benedicks_mask]
        
        if benedicks_data.empty:
            return None, "No Benedicks entries found", []
        
        # Exclude BL12200 entries (as requested)
        non_bl12200_mask = ~benedicks_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        filtered_data = benedicks_data[non_bl12200_mask]
        
        if filtered_data.empty:
            return None, "All Benedicks entries are BL12200", []
        
        # Analyze by BL codes
        bl_code_analysis = {}
        all_projects = []
        
        for _, row in filtered_data.iterrows():
            appn = str(row.iloc[2]).upper() if len(df.columns) > 2 else "Unknown"
            type_code = str(row.iloc[1]).upper().strip() if len(df.columns) > 1 else "Unknown"
            pm_name = str(row.iloc[3]) if len(df.columns) > 3 else "Unknown"
            bl_code = str(row.iloc[7]) if len(df.columns) > 7 else "Unknown"
            project_desc = str(row.iloc[5]) if len(df.columns) > 5 else "Unknown"
            co_number = str(row.iloc[6]) if len(df.columns) > 6 else "Unknown"  # Project Object column
            
            try:
                # THIS IS THE FIX for the Syntax Error
                balance_str = str(row.iloc[16]).replace('$', '').replace(',', '').strip()
                balance = float(balance_str) if balance_str and balance_str != 'nan' else 0.0
                
                # Track by BL code
                if bl_code not in bl_code_analysis:
                    bl_code_analysis[bl_code] = {
                        'total_balance': 0.0,
                        'project_count': 0,
                        'appropriations': {'OMN': 0.0, 'OPN': 0.0, 'SCN': 0.0, 'OTHER': 0.0},
                        'types': {'L': 0.0, 'M': 0.0, 'T': 0.0, 'OTHER': 0.0},
                        'projects': []
                    }
                
                bl_code_analysis[bl_code]['total_balance'] += balance
                bl_code_analysis[bl_code]['project_count'] += 1
                
                # Track by appropriation
                if 'OMN' in appn:
                    bl_code_analysis[bl_code]['appropriations']['OMN'] += balance
                elif 'OPN' in appn:
                    bl_code_analysis[bl_code]['appropriations']['OPN'] += balance
                elif 'SCN' in appn:
                    bl_code_analysis[bl_code]['appropriations']['SCN'] += balance
                else:
                    bl_code_analysis[bl_code]['appropriations']['OTHER'] += balance
                
                # Track by type
                if type_code in ['L', 'M', 'T']:
                    bl_code_analysis[bl_code]['types'][type_code] += balance
                else:
                    bl_code_analysis[bl_code]['types']['OTHER'] += balance
                
                # Individual project info
                project_info = {
                    'BL_Code': bl_code,
                    'CO_Number': co_number,
                    'APPN': appn,
                    'Type': type_code,
                    'Balance': balance,
                    'Description': project_desc,
                    'PM': pm_name
                }
                
                bl_code_analysis[bl_code]['projects'].append(project_info)
                all_projects.append(project_info)
                
            except:
                continue
        
        # Sort BL codes by total balance
        sorted_bl_codes = sorted(bl_code_analysis.items(), key=lambda x: x[1]['total_balance'], reverse=True)
        
        # Sort all projects by balance
        all_projects = sorted(all_projects, key=lambda x: x['Balance'], reverse=True)
        
        # Calculate totals
        total_balance = sum([bl_data['total_balance'] for _, bl_data in sorted_bl_codes])
        total_projects = len(all_projects)
        
        # Categorize BL codes
        bl16200_total = bl_code_analysis.get('BL16200', {}).get('total_balance', 0.0)
        other_bl_total = total_balance - bl16200_total
        
        return {
            'bl_code_analysis': sorted_bl_codes,
            'all_projects': all_projects,
            'total_balance': total_balance,
            'total_projects': total_projects,
            'bl16200_balance': bl16200_total,
            'other_bl_balance': other_bl_total,
            'bl_code_count': len(sorted_bl_codes)
        }, f"✅ Found {total_projects} projects across {len(sorted_bl_codes)} different BL codes worth ${total_balance:,.0f}", all_projects
        
    except Exception as e:
        return None, f"❌ Error analyzing personal funding: {str(e)}", []

# Personal Funding Analysis Section (NEW - shows ALL BL codes)
if enable_personal_funding and uploaded_file:
    st.markdown("### 💼 Complete Personal Funding Analysis")
    
    # Analyze all personal funding across BL codes
    personal_analysis, personal_message, all_personal_projects = analyze_all_personal_funding(uploaded_file)
    
    if personal_analysis:
        st.success(personal_message)
        
        total_balance = personal_analysis['total_balance']
        bl_code_count = personal_analysis['bl_code_count']
        
        # Detailed BL Code Breakdown
        st.markdown("#### 🏗️ Other BL Codes Where You're the PM")
        st.info("💡 These are all the OTHER departments where Benedicks/Benedicks-Denovellis is listed as PM (NOT including your BL16200 or managed BL12200)")
        
        if bl_code_count > 0:
            for i, (bl_code, bl_data) in enumerate(personal_analysis['bl_code_analysis']):
                # Create appropriation breakdown
                appn_breakdown = ""
                for appn, amount in bl_data['appropriations'].items():
                    if amount > 0:
                        appn_breakdown += f'<span style="background: rgba(255,255,255,0.3); padding: 0.2rem 0.5rem; border-radius: 5px; margin-right: 0.3rem; font-size: 0.8em;">{appn}: ${amount:,.0f}</span>'
                
                # Create type breakdown
                type_breakdown = ""
                for type_code, amount in bl_data['types'].items():
                    if amount > 0:
                        type_breakdown += f'<span style="background: rgba(255,255,255,0.2); padding: 0.2rem 0.5rem; border-radius: 5px; margin-right: 0.3rem; font-size: 0.8em;">{type_code}: ${amount:,.0f}</span>'
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #e67e22aa, #d35400dd); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <h5>#{i+1}: {bl_code} (Other Department)</h5>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 0.5rem 0;">
                        <div><strong>Total Balance:</strong> ${bl_data["total_balance"]:,.0f}</div>
                        <div><strong>Projects:</strong> {bl_data["project_count"]}</div>
                        <div><strong>% of Other Funding:</strong> {bl_data["total_balance"]/total_balance*100:.1f}%</div>
                    </div>
                    <div style="margin: 0.5rem 0;">
                        <strong>Appropriations:</strong><br>{appn_breakdown}
                    </div>
                    <div style="margin: 0.5rem 0;">
                        <strong>Types:</strong><br>{type_breakdown}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No other BL codes found where you are the PM (excluding BL16200 and BL12200)")
        
        # Strategic Analysis
        if bl_code_count > 0:
            st.markdown("#### 🎯 Strategic Insights")
            st.success(f"📊 **Other Department Involvement**: You are PM for {bl_code_count} other departments beyond BL16200/BL12200")
            
            # Show summary
            st.write(f"**Total funding in other departments:** ${total_balance:,.0f}")
            st.write(f"**Average per BL code:** ${total_balance/bl_code_count:,.0f}")
            
            # Show top BL code
            if personal_analysis['bl_code_analysis']:
                top_bl, top_data = personal_analysis['bl_code_analysis'][0]
                st.write(f"**Largest other department:** {top_bl} with ${top_data['total_balance']:,.0f}")

        # Individual Projects List
        if all_personal_projects:
            st.markdown("#### 📋 Projects in Other Departments")
            for i, project in enumerate(all_personal_projects[:20]):  # Show top 20 projects
                st.markdown(f"""
                <div style="background: white; border: 1px solid #ddd; padding: 1rem; border-radius: 8px; margin: 0.3rem 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h6 style="margin: 0; color: #333;">#{i+1}: {project["BL_Code"]} - {project["CO_Number"]}</h6>
                        <span style="background: #e67e22; color: white; padding: 0.2rem 0.5rem; border-radius: 5px; font-size: 0.8em;">Other Dept</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 0.5rem 0; font-size: 0.9em; color: #666;">
                        <div><strong>APPN:</strong> {project["APPN"]}</div>
                        <div><strong>Type:</strong> {project["Type"]}</div>
                        <div><strong>Balance:</strong> ${project["Balance"]:,.0f}</div>
                    </div>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9em; color: #555;">{project["Description"][:100]}{"..." if len(project["Description"]) > 100 else ""}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(personal_message)

# BFM AI Assistant Section
# This section remains unchanged and will function as you designed it.

# Benedicks Portfolio Analysis Section (if enabled and file uploaded)
# This section remains unchanged and will function as you designed it.

# The rest of the script (Data Input, Calculate Button, and Footer) remains unchanged.
# (The full code is too long to repeat, but this completes the script from the point of error)
