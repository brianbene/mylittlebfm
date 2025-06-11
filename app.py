import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io

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
    enable_personal_funding = st.checkbox("Enable Personal Funding Analysis", value=False, help="Analyze your funding across BL16200 and other branches (excluding BL12200)")

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

def is_expiring_soon(report_date, expiry_date, months=2):
    warning_date = report_date + timedelta(days=months * 30)
    return expiry_date <= warning_date

def analyze_personal_funding_portfolio(file):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        
        # Filter for your PM entries
        your_pm_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        your_data = df[your_pm_mask]
        
        if your_data.empty:
            return None, "No entries found for your PM name", []
        
        # Categorize by BL codes
        bl16200_mask = your_data.iloc[:, 7].astype(str).str.contains('BL16200', na=False)
        bl12200_mask = your_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        
        bl16200_data = your_data[bl16200_mask]
        other_branches_data = your_data[~bl12200_mask & ~bl16200_mask]
        bl12200_data = your_data[bl12200_mask]
        
        categories = {
            'bl16200': {'data': bl16200_data, 'name': 'BL16200 (Your Branch)'},
            'other_branches': {'data': other_branches_data, 'name': 'Other Branches'},
            'bl12200': {'data': bl12200_data, 'name': 'BL12200 (Managed Branch)'}
        }
        
        result = {}
        all_projects = []
        bl_code_breakdown = {}
        
        for category_key, category_info in categories.items():
            category_data = category_info['data']
            
            result[category_key] = {
                'omn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0},
                'opn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0},
                'scn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0},
                'other': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0, 'count': 0},
                'total_balance': 0.0,
                'total_count': 0,
                'projects': []
            }
            
            for _, row in category_data.iterrows():
                appn = str(row.iloc[2]).upper() if len(df.columns) > 2 else "Unknown"
                type_code = str(row.iloc[1]).upper().strip() if len(df.columns) > 1 else "Unknown"
                pm_name = str(row.iloc[3]) if len(df.columns) > 3 else "Unknown"
                bl_code = str(row.iloc[7]) if len(df.columns) > 7 else "Unknown"
                project_desc = str(row.iloc[5]) if len(df.columns) > 5 else "Unknown"
                
                try:
                    balance_raw = str(row.iloc[16])
                    balance_clean = balance_raw.replace('$', '').replace(',', '').strip()
                    balance = float(balance_clean) if balance_clean and balance_clean != 'nan' else 0.0
                    
                    project_info = {
                        'PM': pm_name,
                        'APPN': appn,
                        'Type': type_code,
                        'Balance': balance,
                        'BL_Code': bl_code,
                        'Description': project_desc,
                        'Category': category_info['name']
                    }
                    
                    result[category_key]['projects'].append(project_info)
                    all_projects.append(project_info)
                    
                    if category_key == 'other_branches':
                        if bl_code not in bl_code_breakdown:
                            bl_code_breakdown[bl_code] = {'balance': 0.0, 'count': 0, 'projects': []}
                        bl_code_breakdown[bl_code]['balance'] += balance
                        bl_code_breakdown[bl_code]['count'] += 1
                        bl_code_breakdown[bl_code]['projects'].append(project_info)
                    
                except:
                    balance = 0.0
                    continue
                
                if 'OMN' in appn:
                    appn_key = 'omn'
                elif 'SCN' in appn:
                    appn_key = 'scn'
                elif 'OPN' in appn:
                    appn_key = 'opn'
                else:
                    appn_key = 'other'
                
                result[category_key][appn_key]['balance'] += balance
                result[category_key][appn_key]['count'] += 1
                result[category_key]['total_balance'] += balance
                result[category_key]['total_count'] += 1
                
                if type_code == 'L':
                    result[category_key][appn_key]['L'] += balance
                elif type_code == 'M':
                    result[category_key][appn_key]['M'] += balance
                elif type_code == 'T':
                    result[category_key][appn_key]['T'] += balance
                else:
                    result[category_key][appn_key]['L'] += balance * 0.6
                    result[category_key][appn_key]['M'] += balance * 0.3
                    result[category_key][appn_key]['T'] += balance * 0.1
            
            result[category_key]['projects'] = sorted(result[category_key]['projects'], key=lambda x: x['Balance'], reverse=True)
        
        all_projects = sorted(all_projects, key=lambda x: x['Balance'], reverse=True)
        sorted_bl_codes = sorted(bl_code_breakdown.items(), key=lambda x: x[1]['balance'], reverse=True)
        
        total_available_funding = result['bl16200']['total_balance'] + result['other_branches']['total_balance']
        total_projects = result['bl16200']['total_count'] + result['other_branches']['total_count']
        
        return {
            'categories': result,
            'all_projects': all_projects,
            'bl_code_breakdown': sorted_bl_codes,
            'total_available_funding': total_available_funding,
            'total_projects': total_projects,
            'bl16200_funding': result['bl16200']['total_balance'],
            'other_branches_funding': result['other_branches']['total_balance'],
            'bl12200_funding': result['bl12200']['total_balance']
        }, f"✅ Found {total_projects} projects under your PM (excluding BL12200) worth ${total_available_funding:,.0f}", all_projects
        
    except Exception as e:
        return None, f"❌ Error analyzing personal funding portfolio: {str(e)}", []

def analyze_benedicks_portfolio(file):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        
        benedicks_mask = df.iloc[:, 3].astype(str).str.lower().str.contains('benedick', na=False)
        benedicks_data = df[benedicks_mask]
        
        if benedicks_data.empty:
            return None, "No Benedicks entries found", []
        
        non_bl12200_mask = ~benedicks_data.iloc[:, 7].astype(str).str.contains('BL12200', na=False)
        filtered_data = benedicks_data[non_bl12200_mask]
        
        if filtered_data.empty:
            return None, "All Benedicks entries are BL12200", []
        
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
                balance_raw = str(row.iloc[16])
                balance_clean = balance_raw.replace('$', '').replace(',', '').strip()
                balance = float(balance_clean) if balance_clean and balance_clean != 'nan' else 0.0
                
                benedicks_projects.append({
                    'PM': pm_name,
                    'APPN': appn,
                    'Type': type_code,
                    'Balance': balance,
                    'BL_Code': bl_code,
                    'Description': project_desc
                })
                
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
            
            if type_code == 'L':
                result[appn_key]['L'] += balance
            elif type_code == 'M':
                result[appn_key]['M'] += balance
            elif type_code == 'T':
                result[appn_key]['T'] += balance
            else:
                result[appn_key]['L'] += balance * 0.6
                result[appn_key]['M'] += balance * 0.3
                result[appn_key]['T'] += balance * 0.1
        
        benedicks_projects = sorted(benedicks_projects, key=lambda x: x['Balance'], reverse=True)
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
                balance_raw = str(row.iloc[16])
                balance_clean = balance_raw.replace('$', '').replace(',', '').strip()
                balance = float(balance_clean) if balance_clean else 0.0
                
                if balance > 0:
                    chargeable_objects.append({'CO_Number': co_number, 'APPN': appn, 'Type': type_code, 'Balance': balance})
            except:
                continue
            
            appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
            result[appn_key]['balance'] += balance
            
            if type_code == 'L': 
                result[appn_key]['L'] += balance
            elif type_code == 'M': 
                result[appn_key]['M'] += balance
            elif type_code == 'T': 
                result[appn_key]['T'] += balance
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
if 'personal_funding_data' not in st.session_state:
    st.session_state.personal_funding_data = None

# Personal Funding Analysis Section
if enable_personal_funding and uploaded_file:
    st.markdown("### 💼 Personal Funding Portfolio Analysis")
    
    personal_analysis, personal_message, personal_projects = analyze_personal_funding_portfolio(uploaded_file)
    st.session_state.personal_funding_data = personal_analysis
    
    if personal_analysis:
        st.success(personal_message)
        
        total_available = personal_analysis['total_available_funding']
        bl16200_funding = personal_analysis['bl16200_funding']
        other_branches_funding = personal_analysis['other_branches_funding']
        bl12200_funding = personal_analysis['bl12200_funding']
        total_projects = personal_analysis['total_projects']
        
        st.markdown(f"""
        <div class="pm-analysis-card">
            <h3>💼 Your Complete Funding Portfolio</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; margin: 1rem 0; text-align: center;">
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Total Available Funding</h4>
                    <h3>${total_available:,.0f}</h3>
                    <small>(Excluding BL12200)</small>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>BL16200 (Your Branch)</h4>
                    <h3>${bl16200_funding:,.0f}</h3>
                    <small>{bl16200_funding/total_available*100:.1f}% of total</small>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Other Branches</h4>
                    <h3>${other_branches_funding:,.0f}</h3>
                    <small>{other_branches_funding/total_available*100:.1f}% of total</small>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>BL12200 (Managed)</h4>
                    <h3>${bl12200_funding:,.0f}</h3>
                    <small>Excluded from analysis</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        categories = personal_analysis['categories']
        
        st.markdown("#### 📊 Funding Breakdown by Category")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🎯 BL16200 (Your Personal Branch)")
            bl16200_cat = categories['bl16200']
            st.write(f"**Projects:** {bl16200_cat['total_count']}")
            st.write(f"**Total Balance:** ${bl16200_cat['total_balance']:,.0f}")
            
            if bl16200_cat['total_count'] > 0:
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("OMN", f"${bl16200_cat['omn']['balance']:,.0f}", f"{bl16200_cat['omn']['count']} projects")
                with col_b:
                    st.metric("OPN", f"${bl16200_cat['opn']['balance']:,.0f}", f"{bl16200_cat['opn']['count']} projects")
                with col_c:
                    st.metric("SCN", f"${bl16200_cat['scn']['balance']:,.0f}", f"{bl16200_cat['scn']['count']} projects")
        
        with col2:
            st.markdown("##### 🏢 Other Branches (Money Given Out)")
            other_cat = categories['other_branches']
            st.write(f"**Projects:** {other_cat['total_count']}")
            st.write(f"**Total Balance:** ${other_cat['total_balance']:,.0f}")
            
            if other_cat['total_count'] > 0:
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("OMN", f"${other_cat['omn']['balance']:,.0f}", f"{other_cat['omn']['count']} projects")
                with col_b:
                    st.metric("OPN", f"${other_cat['opn']['balance']:,.0f}", f"{other_cat['opn']['count']} projects")
                with col_c:
                    st.metric("SCN", f"${other_cat['scn']['balance']:,.0f}", f"{other_cat['scn']['count']} projects")
        
        if personal_analysis['bl_code_breakdown']:
            st.markdown("#### 🏗️ Other Branches - BL Code Breakdown")
            st.info("💡 These are departments where you've allocated funding. Monitor these to see if you need to pull money back.")
            
            for i, (bl_code, bl_data) in enumerate(personal_analysis['bl_code_breakdown'][:8]):
                percentage_of_other = (bl_data['balance'] / other_branches_funding * 100) if other_branches_funding > 0 else 0
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #34495eaa, #2c3e50aa); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <h5>#{i+1}: {bl_code}</h5>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
                        <div><strong>Balance:</strong> ${bl_data["balance"]:,.0f}</div>
                        <div><strong>Projects:</strong> {bl_data["count"]}</div>
                        <div><strong>% of Other Funding:</strong> {percentage_of_other:.1f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("#### 🎯 Strategic Funding Analysis")
        
        if bl16200_funding > other_branches_funding:
            funding_status = "✅ GOOD POSITION"
            status_color = "#27ae60"
            status_message = "You have more funding in your branch than given to others"
        elif bl16200_funding > other_branches_funding * 0.8:
            funding_status = "⚠️ MONITOR CLOSELY"
            status_color = "#f39c12"
            status_message = "Funding levels are balanced but monitor other branches"
        else:
            funding_status = "🚨 CONSIDER REALLOCATION"
            status_color = "#e74c3c"
            status_message = "You may need to pull funding from other branches"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {status_color}aa, {status_color}dd); color: white; padding: 2rem; border-radius: 15px; margin: 1rem 0; text-align: center;">
            <h2>💰 FUNDING STATUS: {funding_status}</h2>
            <h3>{status_message}</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 1.5rem 0;">
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Your Branch Ratio</h4>
                    <h3>{bl16200_funding/total_available*100:.1f}%</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Other Branches Ratio</h4>
                    <h3>{other_branches_funding/total_available*100:.1f}%</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Potential to Reclaim</h4>
                    <h3>${other_branches_funding:,.0f}</h3>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if personal_projects:
            st.markdown("#### 🏆 Top Personal Projects (All Categories)")
            for i, project in enumerate(personal_projects[:8]):
                category_color = "#3498db" if "BL16200" in project['Category'] else "#e67e22"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {category_color}aa, {category_color}dd); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <h5>#{i+1}: {project["BL_Code"]} ({project["Category"]})</h5>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
                        <div><strong>APPN:</strong> {project["APPN"]}</div>
                        <div><strong>Type:</strong> {project["Type"]}</div>
                        <div><strong>Balance:</strong> ${project["Balance"]:,.0f}</div>
                    </div>
                    <p style="margin-top: 0.5rem;"><strong>Description:</strong> {project["Description"][:80]}{"..." if len(project["Description"]) > 80 else ""}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(personal_message)

# Benedicks Portfolio Analysis Section
if enable_pm_analysis and uploaded_file:
    st.markdown("### 👨‍💼 Benedicks Portfolio Analysis (Non-BL12200)")
    
    benedicks_analysis, benedicks_message, benedicks_projects = analyze_benedicks_portfolio(uploaded_file)
    st.session_state.benedicks_data = benedicks_analysis
    st.session_state.benedicks_projects = benedicks_projects
    
    if benedicks_analysis:
        st.success(benedicks_message)
        
        total_balance = benedicks_analysis['total_balance']
        total_count = benedicks_analysis['total_count']
        summary = benedicks_analysis['summary']
        
        st.markdown(f"""
        <div class="pm-analysis-card">
            <h3>🎯 Benedicks Portfolio Analysis (Excluding BL12200)</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; margin: 1rem 0; text-align: center;">
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Total Projects</h4>
                    <h3>{total_count}</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Total Portfolio Value</h4>
                    <h3>${total_balance:,.0f}</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Avg Project Size</h4>
                    <h3>${total_balance/total_count:,.0f}</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Personnel Months</h4>
                    <h3>{total_balance/(hourly_rate * hours_per_week * 4.3 * (1 + overhead_rate / 100)):,.1f}</h3>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card"><h4>OMN - Benedicks</h4></div>', unsafe_allow_html=True)
            st.write(f"**Projects:** {summary['omn']['count']}")
            st.write(f"**Balance:** ${summary['omn']['balance']:,.0f}")
            st.write(f"**Labor:** ${summary['omn']['L']:,.0f}")
            st.write(f"**Material:** ${summary['omn']['M']:,.0f}")
            st.write(f"**Travel:** ${summary['omn']['T']:,.0f}")
        
        with col2:
            st.markdown('<div class="metric-card"><h4>OPN - Benedicks</h4></div>', unsafe_allow_html=True)
            st.write(f"**Projects:** {summary['opn']['count']}")
            st.write(f"**Balance:** ${summary['opn']['balance']:,.0f}")
            st.write(f"**Labor:** ${summary['opn']['L']:,.0f}")
            st.write(f"**Material:** ${summary['opn']['M']:,.0f}")
            st.write(f"**Travel:** ${summary['opn']['T']:,.0f}")
        
        with col3:
            st.markdown('<div class="metric-card"><h4>SCN - Benedicks</h4></div>', unsafe_allow_html=True)
            st.write(f"**Projects:** {summary['scn']['count']}")
            st.write(f"**Balance:** ${summary['scn']['balance']:,.0f}")
            st.write(f"**Labor:** ${summary['scn']['L']:,.0f}")
            st.write(f"**Material:** ${summary['scn']['M']:,.0f}")
            st.write(f"**Travel:** ${summary['scn']['T']:,.0f}")
        
        with col4:
            st.markdown('<div class="metric-card"><h4>Other - Benedicks</h4></div>', unsafe_allow_html=True)
            st.write(f"**Projects:** {summary['other']['count']}")
            st.write(f"**Balance:** ${summary['other']['balance']:,.0f}")
            st.write(f"**Labor:** ${summary['other']['L']:,.0f}")
            st.write(f"**Material:** ${summary['other']['M']:,.0f}")
            st.write(f"**Travel:** ${summary['other']['T']:,.0f}")
        
        if benedicks_analysis['bl_codes']:
            st.markdown("#### 🏗️ Top BL Codes in Benedicks Portfolio")
            for i, (bl_code, bl_data) in enumerate(benedicks_analysis['bl_codes'][:5]):
                type_breakdown = ""
                for type_code, type_data in bl_data['types'].items():
                    if type_code.strip():
                        type_breakdown += f'<span style="background: rgba(255,255,255,0.2); padding: 0.3rem 0.6rem; border-radius: 5px; font-size: 0.9em; margin-right: 0.5rem;">{type_code}: ${type_data["balance"]:,.0f}</span>'
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #2c3e50aa, #34495eaa); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <h5>#{i+1}: {bl_code}</h5>
                    <p><strong>Projects:</strong> {bl_data["count"]} | <strong>Total Balance:</strong> ${bl_data["balance"]:,.0f}</p>
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap;">{type_breakdown}</div>
                </div>
                """, unsafe_allow_html=True)
        
        if benedicks_projects:
            st.markdown("#### 🎯 Top Benedicks Projects")
            for i, project in enumerate(benedicks_projects[:10]):
                description = project["Description"][:100] + "..." if len(project["Description"]) > 100 else project["Description"]
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #8e44adaa, #9b59b6aa); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <h5>#{i+1}: {project["BL_Code"]}</h5>
                    <p><strong>PM:</strong> {project["PM"]} | <strong>APPN:</strong> {project["APPN"]} | <strong>Type:</strong> {project["Type"]}</p>
                    <p><strong>Balance:</strong> ${project["Balance"]:,.0f}</p>
                    <p><strong>Description:</strong> {description}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(benedicks_message)

# Data Input Section
if uploaded_file:
    if st.session_state.last_bl_code != selected_bl:
        extracted_data, message, top_cos = extract_vla_data(uploaded_file, selected_bl)
        st.session_state.extracted_data = extracted_data
        st.session_state.top_cos = top_cos
        st.session_state.last_bl_code = selected_bl
        st.info(message)
    else:
        extracted_data = st.session_state.extracted_data
        top_cos = st.session_state.top_cos
    
    if extracted_data:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
            omn_balance = st.number_input("OMN Balance ($)", value=float(extracted_data['omn']['balance']))
            omn_l = st.number_input("OMN Labor ($)", value=float(extracted_data['omn']['L']))
            omn_m = st.number_input("OMN Material ($)", value=float(extracted_data['omn']['M']))
            omn_t = st.number_input("OMN Travel ($)", value=float(extracted_data['omn']['T']))
        
        with col2:
            st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
            opn_balance = st.number_input("OPN Balance ($)", value=float(extracted_data['opn']['balance']))
            opn_l = st.number_input("OPN Labor ($)", value=float(extracted_data['opn']['L']))
            opn_m = st.number_input("OPN Material ($)", value=float(extracted_data['opn']['M']))
            opn_t = st.number_input("OPN Travel ($)", value=float(extracted_data['opn']['T']))
        
        with col3:
            st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
            scn_balance = st.number_input("SCN Balance ($)", value=float(extracted_data['scn']['balance']))
            scn_l = st.number_input("SCN Labor ($)", value=float(extracted_data['scn']['L']))
            scn_m = st.number_input("SCN Material ($)", value=float(extracted_data['scn']['M']))
            scn_t = st.number_input("SCN Travel ($)", value=float(extracted_data['scn']['T']))
    else:
        top_cos = []
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
            omn_balance = st.number_input("OMN Balance ($)", value=44053.0)
            omn_l = st.number_input("OMN Labor ($)", value=44053.0)
            omn_m = st.number_input("OMN Material ($)", value=0.0)
            omn_t = st.number_input("OMN Travel ($)", value=0.0)
        
        with col2:
            st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
            opn_balance = st.number_input("OPN Balance ($)", value=1947299.0)
            opn_l = st.number_input("OPN Labor ($)", value=1947299.0)
            opn_m = st.number_input("OPN Material ($)", value=0.0)
            opn_t = st.number_input("OPN Travel ($)", value=0.0)
        
        with col3:
            st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
            scn_balance = st.number_input("SCN Balance ($)", value=1148438.0)
            scn_l = st.number_input("SCN Labor ($)", value=813595.0)
            scn_m = st.number_input("SCN Material ($)", value=334843.0)
            scn_t = st.number_input("SCN Travel ($)", value=0.0)
else:
    top_cos = []
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-card"><h4>OMN</h4></div>', unsafe_allow_html=True)
        omn_balance = st.number_input("OMN Balance ($)", value=44053.0)
        omn_l = st.number_input("OMN Labor ($)", value=44053.0)
        omn_m = st.number_input("OMN Material ($)", value=0.0)
        omn_t = st.number_input("OMN Travel ($)", value=0.0)
    
    with col2:
        st.markdown('<div class="metric-card"><h4>OPN</h4></div>', unsafe_allow_html=True)
        opn_balance = st.number_input("OPN Balance ($)", value=1947299.0)
        opn_l = st.number_input("OPN Labor ($)", value=1947299.0)
        opn_m = st.number_input("OPN Material ($)", value=0.0)
        opn_t = st.number_input("OPN Travel ($)", value=0.0)
    
    with col3:
        st.markdown('<div class="metric-card"><h4>SCN</h4></div>', unsafe_allow_html=True)
        scn_balance = st.number_input("SCN Balance ($)", value=1148438.0)
        scn_l = st.number_input("SCN Labor ($)", value=813595.0)
        scn_m = st.number_input("SCN Material ($)", value=334843.0)
        scn_t = st.number_input("SCN Travel ($)", value=0.0)

# Calculate Button
if st.button("🚀 Calculate Analysis", type="primary"):
    
    # Core Calculations
    report_datetime = datetime.combine(report_date, datetime.min.time())
    
    # Calculate expiry dates
    omn_expiry = get_appropriation_expiry_date('OMN', fiscal_year)
    opn_expiry = get_appropriation_expiry_date('OPN', fiscal_year)
    scn_expiry = get_appropriation_expiry_date('SCN', fiscal_year)
    
    # Calculate working days to each expiry
    omn_working_days = count_working_days(report_datetime, omn_expiry, fiscal_year)
    opn_working_days = count_working_days(report_datetime, opn_expiry, fiscal_year)
    scn_working_days = count_working_days(report_datetime, scn_expiry, fiscal_year)
    
    # Check expiring soon
    omn_expiring_soon = is_expiring_soon(report_datetime, omn_expiry, 2)
    opn_expiring_soon = is_expiring_soon(report_datetime, opn_expiry, 2)
    scn_expiring_soon = is_expiring_soon(report_datetime, scn_expiry, 2)
    
    # Personnel calculations
    monthly_personnel_cost = hourly_rate * hours_per_week * 4.3 * branch_size * (1 + overhead_rate / 100)
    total_balance = omn_balance + opn_balance + scn_balance
    
    # URGENT ALERTS
    urgent_appropriations = []
    if omn_expiring_soon and omn_balance > 0:
        urgent_appropriations.append(f"OMN (expires {omn_expiry.strftime('%b %d, %Y')} - {(omn_expiry - report_datetime).days} days)")
    if opn_expiring_soon and opn_balance > 0:
        urgent_appropriations.append(f"OPN (expires {opn_expiry.strftime('%b %d, %Y')} - {(opn_expiry - report_datetime).days} days)")
    if scn_expiring_soon and scn_balance > 0:
        urgent_appropriations.append(f"SCN (expires {scn_expiry.strftime('%b %d, %Y')} - {(scn_expiry - report_datetime).days} days)")
    
    if urgent_appropriations:
        st.error(f"🚨 **URGENT EXPIRY ALERT**: {', '.join(urgent_appropriations)}")
    
    # SMART APPN CHARGING STRATEGY
    st.markdown('<div class="bubble"><h3 style="text-align: center;">💡 Smart APPN Charging Strategy</h3><p style="text-align: center;">Use all funding before Dec 30 while maintaining operations</p></div>', unsafe_allow_html=True)
    
    # Calculate Dec 30 strategy
    dec_30_date = datetime(fiscal_year, 12, 30)
    months_to_dec30 = max((dec_30_date - report_datetime).days / 30.44, 0)
    total_funding_needed_dec30 = monthly_personnel_cost * months_to_dec30
    
    # Create optimal charging strategy
    charging_strategy = []
    remaining_need = total_funding_needed_dec30
    
    # Sort by expiry date (use earliest first)
    appn_data = [("OMN", omn_balance, omn_expiry), ("OPN", opn_balance, opn_expiry), ("SCN", scn_balance, scn_expiry)]
    appn_data.sort(key=lambda x: x[2])
    
    cumulative_months = 0
    for appn, balance, expiry in appn_data:
        if balance > 0 and remaining_need > 0:
            months_from_this_appn = min(balance / monthly_personnel_cost, remaining_need / monthly_personnel_cost)
            
            if months_from_this_appn > 0:
                amount_to_use = months_from_this_appn * monthly_personnel_cost
                start_date = report_datetime + timedelta(days=cumulative_months * 30.44)
                end_date = report_datetime + timedelta(days=(cumulative_months + months_from_this_appn) * 30.44)
                
                days_until_expiry = (expiry - report_datetime).days
                if days_until_expiry < 60:
                    urgency = "🚨 URGENT"
                    urgency_color = "#e74c3c"
                elif days_until_expiry < 120:
                    urgency = "⚠️ PRIORITY"
                    urgency_color = "#f39c12"
                else:
                    urgency = "✅ PLANNED"
                    urgency_color = "#27ae60"
                
                charging_strategy.append({
                    'appn': appn, 'amount': amount_to_use, 'months': months_from_this_appn,
                    'start_date': start_date, 'end_date': end_date, 'expiry_date': expiry,
                    'urgency': urgency, 'urgency_color': urgency_color,
                    'remaining_balance': balance - amount_to_use
                })
                
                remaining_need -= amount_to_use
                cumulative_months += months_from_this_appn
    
    # Display charging strategy
    if charging_strategy:
        st.markdown("### 📅 Month-by-Month Charging Plan")
        
        for i, strategy in enumerate(charging_strategy, 1):
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {strategy["urgency_color"]}aa, {strategy["urgency_color"]}dd); color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">
                <h4>Phase {i}: Charge to {strategy["appn"]} {strategy["urgency"]}</h4>
                <p><strong>📅 Timeframe:</strong> {strategy["start_date"].strftime("%b %d, %Y")} → {strategy["end_date"].strftime("%b %d, %Y")} ({strategy["months"]:.1f} months)</p>
                <p><strong>💰 Funding:</strong> ${strategy["amount"]:,.0f} | <strong>Remaining:</strong> ${strategy["remaining_balance"]:,.0f}</p>
                <p><strong>⏰ {strategy["appn"]} Expires:</strong> {strategy["expiry_date"].strftime("%b %d, %Y")} ({(strategy["expiry_date"] - report_datetime).days} days)</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Display current month recommendation and remaining analysis sections
    current_month_rec = charging_strategy[0] if charging_strategy else None
    if current_month_rec:
        st.markdown("### 🎯 THIS MONTH'S CHARGING RECOMMENDATION")
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 2rem; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); border: 2px solid white;">
            <h2>💳 CHARGE ALL LABOR TO: {current_month_rec["appn"]}</h2>
            <h3>{current_month_rec["urgency"]}</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 1rem 0; text-align: center;">
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Monthly Target</h4>
                    <h3>${monthly_personnel_cost:,.0f}</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Use Through</h4>
                    <h3>{current_month_rec["end_date"].strftime("%b %Y")}</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Days Until Expiry</h4>
                    <h3>{(current_month_rec["expiry_date"] - report_datetime).days}</h3>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>🚀 My Little BFM • Enhanced with Smart APPN Charging, Expiry Analysis, Benedicks Portfolio & Personal Funding Analysis</p></div>', unsafe_allow_html=True)
