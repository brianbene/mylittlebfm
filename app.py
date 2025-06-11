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
