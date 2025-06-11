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
.urgent-expiry {animation: pulse 2s infinite;}
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
    
    st.subheader("🎯 Project Branch Analysis")
    bl_codes = ['BL12200', 'BL10000', 'BL12000', 'BL12100', 'BL12300', 'BL16200', 'BL31100', 'BL41000']
    selected_bl = st.selectbox("Select BL Code for Branch Analysis", bl_codes)
    
    st.subheader("👨‍💼 PM Portfolio Analysis")
    enable_pm_analysis = st.checkbox("Enable PM Portfolio Analysis", value=False)
    pm_name_filter = st.text_input("PM Name to Analyze", value="Benedick")
    personal_bl_filter = st.text_input("Your 'Home' BL Code", value="BL16200")
    managed_bl_filter = st.text_input("Managed/Excluded BL Code", value="BL12200")


# --- Core Logic Functions ---
def get_federal_holidays(year):
    # Expanded for multiple years, can be updated as needed
    holidays = {
        2024: [datetime(2024, 10, 14), datetime(2024, 11, 11), datetime(2024, 11, 28), datetime(2024, 12, 25)],
        2025: [datetime(2025, 1, 1), datetime(2025, 1, 20), datetime(2025, 2, 17), datetime(2025, 5, 26),
               datetime(2025, 6, 19), datetime(2025, 7, 4), datetime(2025, 9, 1), datetime(2024, 10, 14), 
               datetime(2024, 11, 11), datetime(2024, 11, 28), datetime(2024, 12, 25)], # Includes FY25 holidays in calendar year 2024
        2026: [datetime(2026, 1, 1), datetime(2026, 1, 19), datetime(2026, 2, 16), datetime(2026, 5, 25),
               datetime(2026, 6, 19), datetime(2026, 7, 3), datetime(2026, 9, 7)]
    }
    return holidays.get(year, [])

def count_working_days(start, end, fy):
    holidays_start_year = get_federal_holidays(start.year)
    holidays_end_year = get_federal_holidays(end.year)
    holidays = list(set(holidays_start_year + holidays_end_year))
    
    working_days = 0
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            working_days += 1
        current += timedelta(days=1)
    return working_days

def get_appropriation_expiry_date(appn, fy):
    if 'OMN' in appn.upper():
        return datetime(fy, 9, 30)
    elif 'OPN' in appn.upper():
        return datetime(fy + 1, 9, 30) # OPN is typically a 2-year appropriation
    elif 'SCN' in appn.upper():
        return datetime(fy + 2, 9, 30) # SCN is typically a 3-year appropriation
    else:
        return datetime(fy, 9, 30)

def is_expiring_soon(report_dt, expiry_dt, months=2):
    return expiry_dt <= report_dt + timedelta(days=months * 30.5)

def analyze_pm_portfolio(file, pm_name, personal_bl, managed_bl):
    """
    Analyzes all funding associated with a specific PM name, categorizing it.
    - Personal Branch: Funding under a specific BL code (e.g., BL16200).
    - Other Branches: Funding given out to other departments.
    - Managed Branch: A specific BL code to be excluded from totals (e.g., BL12200).
    """
    if not pm_name:
        return None, "❌ Please provide a PM Name in the sidebar for analysis.", []

    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        
        # Consistent column names for clarity (assuming standard VLA format)
        # It's safer to use names if the columns might shift
        df.columns.values[1] = "Type"
        df.columns.values[2] = "APPN"
        df.columns.values[3] = "PM"
        df.columns.values[5] = "Description"
        df.columns.values[7] = "BL_Code"
        df.columns.values[16] = "Balance"

        pm_mask = df["PM"].astype(str).str.lower().str.contains(pm_name.lower(), na=False)
        pm_data = df[pm_mask]
        
        if pm_data.empty:
            return None, f"No entries found for PM '{pm_name}'", []
        
        # Categorize data
        personal_mask = pm_data["BL_Code"].astype(str).str.contains(personal_bl, na=False)
        managed_mask = pm_data["BL_Code"].astype(str).str.contains(managed_bl, na=False)
        
        categories = {
            'personal': {'data': pm_data[personal_mask], 'name': f'{personal_bl} (Your Home Branch)'},
            'other': {'data': pm_data[~personal_mask & ~managed_mask], 'name': 'Other Branches (Funded by You)'},
            'managed': {'data': pm_data[managed_mask], 'name': f'{managed_bl} (Managed Branch - Excluded)'}
        }
        
        results = {}
        all_projects = []
        other_bl_code_breakdown = {}
        
        for cat_key, cat_info in categories.items():
            cat_data = cat_info['data']
            results[cat_key] = {
                'omn': {'balance': 0.0, 'count': 0}, 'opn': {'balance': 0.0, 'count': 0},
                'scn': {'balance': 0.0, 'count': 0}, 'other': {'balance': 0.0, 'count': 0},
                'total_balance': 0.0, 'total_count': 0, 'projects': []
            }

            for _, row in cat_data.iterrows():
                try:
                    balance_str = str(row["Balance"]).replace('$', '').replace(',', '').strip()
                    balance = float(balance_str) if balance_str and balance_str.lower() != 'nan' else 0.0
                    if balance == 0: continue

                    project_info = {
                        'PM': row["PM"], 'APPN': row["APPN"], 'Type': row["Type"], 'Balance': balance,
                        'BL_Code': row["BL_Code"], 'Description': row["Description"], 'Category': cat_info['name']
                    }
                    results[cat_key]['projects'].append(project_info)
                    if cat_key != 'managed':
                         all_projects.append(project_info)

                    # Determine appropriation category
                    appn = str(row["APPN"]).upper()
                    if 'OMN' in appn: appn_key = 'omn'
                    elif 'SCN' in appn: appn_key = 'scn'
                    elif 'OPN' in appn: appn_key = 'opn'
                    else: appn_key = 'other'

                    results[cat_key][appn_key]['balance'] += balance
                    results[cat_key][appn_key]['count'] += 1
                    results[cat_key]['total_balance'] += balance
                    results[cat_key]['total_count'] += 1

                    # Track BL code breakdown for 'other' category
                    if cat_key == 'other':
                        bl_code = row["BL_Code"]
                        if bl_code not in other_bl_code_breakdown:
                            other_bl_code_breakdown[bl_code] = {'balance': 0.0, 'count': 0}
                        other_bl_code_breakdown[bl_code]['balance'] += balance
                        other_bl_code_breakdown[bl_code]['count'] += 1

                except (ValueError, TypeError) as e:
                    st.warning(f"Skipping a row in PM analysis due to data issue: {e}")
                    continue
        
        sorted_projects = sorted(all_projects, key=lambda x: x['Balance'], reverse=True)
        sorted_bl_codes = sorted(other_bl_code_breakdown.items(), key=lambda x: x[1]['balance'], reverse=True)
        
        total_portfolio_balance = results['personal']['total_balance'] + results['other']['total_balance']
        total_portfolio_count = results['personal']['total_count'] + results['other']['total_count']

        final_result = {
            'categories': results,
            'all_projects': sorted_projects,
            'other_bl_code_breakdown': sorted_bl_codes,
            'total_portfolio_balance': total_portfolio_balance,
            'total_portfolio_count': total_portfolio_count,
        }
        
        message = f"✅ Found {total_portfolio_count} projects for PM '{pm_name}' worth ${total_portfolio_balance:,.0f} (excluding {managed_bl})."
        return final_result, message, sorted_projects

    except Exception as e:
        return None, f"❌ Error analyzing PM portfolio: {str(e)}", []


def extract_vla_data(file, target_bl):
    """Extracts financial data for a specific BL code."""
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        # Use column index 7 for 'Billing Element' consistently
        bl_data = df[df.iloc[:, 7].astype(str).str.contains(target_bl, na=False)]
        
        if bl_data.empty:
            return None, f"No data found for BL Code {target_bl}", []
        
        result = {'omn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0},
                  'opn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0},
                  'scn': {'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}}
        
        chargeable_objects = []
        
        for _, row in bl_data.iterrows():
            try:
                balance_str = str(row.iloc[16]).replace('$', '').replace(',', '').strip()
                balance = float(balance_str) if balance_str and balance_str.lower() != 'nan' else 0.0
                if balance <= 0: continue

                appn = str(row.iloc[2]).upper()
                type_code = str(row.iloc[1]).upper().strip()
                co_number = str(row.iloc[3])
                
                chargeable_objects.append({'CO_Number': co_number, 'APPN': appn, 'Type': type_code, 'Balance': balance})
                
                appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
                result[appn_key]['balance'] += balance
                
                if type_code == 'L': result[appn_key]['L'] += balance
                elif type_code == 'M': result[appn_key]['M'] += balance
                elif type_code == 'T': result[appn_key]['T'] += balance
                else: # Proportional distribution for unknown types
                    result[appn_key]['L'] += balance * 0.6
                    result[appn_key]['M'] += balance * 0.3
                    result[appn_key]['T'] += balance * 0.1
            except (ValueError, TypeError):
                continue

        top_cos = sorted(chargeable_objects, key=lambda x: x['Balance'], reverse=True)[:5]
        return result, f"✅ Extracted data for {target_bl}", top_cos
    except Exception as e:
        return None, f"❌ Error extracting VLA data: {str(e)}", []

# --- Initialize Session State ---
if 'extracted_data' not in st.session_state: st.session_state.extracted_data = None
if 'last_bl_code' not in st.session_state: st.session_state.last_bl_code = None
if 'top_cos' not in st.session_state: st.session_state.top_cos = []
if 'pm_portfolio_data' not in st.session_state: st.session_state.pm_portfolio_data = None
if 'pm_projects' not in st.session_state: st.session_state.pm_projects = []

# --- PM Portfolio Analysis Section ---
if enable_pm_analysis and uploaded_file:
    st.markdown("---")
    st.markdown(f"### 👨‍💼 PM Portfolio Analysis for '{pm_name_filter}'")
    
    # Analyze PM portfolio data
    pm_analysis, pm_message, pm_projects = analyze_pm_portfolio(uploaded_file, pm_name_filter, personal_bl_filter, managed_bl_filter)
    st.session_state.pm_portfolio_data = pm_analysis
    st.session_state.pm_projects = pm_projects
    
    if pm_analysis:
        st.success(pm_message)
        
        # Unpack data for easier access
        cats = pm_analysis['categories']
        personal_funding = cats['personal']['total_balance']
        other_funding = cats['other']['total_balance']
        managed_funding = cats['managed']['total_balance']
        total_portfolio_balance = pm_analysis['total_portfolio_balance']

        # Strategic Overview Card
        if personal_funding > other_funding:
            strat_status, strat_color, strat_msg = "✅ GOOD", "#27ae60", "You hold more funding than you've given out."
        elif personal_funding > other_funding * 0.75:
            strat_status, strat_color, strat_msg = "⚠️ MONITOR", "#f39c12", "Your funding is balanced, but monitor funds given out."
        else:
            strat_status, strat_color, strat_msg = "🚨 REALLOCATE?", "#e74c3c", "Consider pulling funds back from other branches."
        
        st.markdown(f"""
        <div class="pm-analysis-card" style="border-color: {strat_color};">
            <h3>📈 Strategic Portfolio Status: <span style="color: {strat_color};">{strat_status}</span></h3>
            <p style="font-size: 1.1em;">{strat_msg}</p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Your 'Home' Branch</h4><h3>${personal_funding:,.0f}</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Funded to Others</h4><h3>${other_funding:,.0f}</h3>
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">
                    <h4>Total Portfolio Value</h4><h3>${total_portfolio_balance:,.0f}</h3>
                </div>
                 <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 10px;">
                    <h4>Managed (Excluded)</h4><h3>${managed_funding:,.0f}</h3>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detailed Breakdown
        st.markdown("#### 📊 Funding Breakdown by Category")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"##### 🎯 {personal_bl_filter} (Your Home Branch)")
            p_cat = cats['personal']
            st.metric(label="Total Balance", value=f"${p_cat['total_balance']:,.0f}", delta=f"{p_cat['total_count']} projects")
            if p_cat['total_count'] > 0:
                c1, c2, c3 = st.columns(3)
                c1.metric("OMN", f"${p_cat['omn']['balance']:,.0f}", f"{p_cat['omn']['count']} projects")
                c2.metric("OPN", f"${p_cat['opn']['balance']:,.0f}", f"{p_cat['opn']['count']} projects")
                c3.metric("SCN", f"${p_cat['scn']['balance']:,.0f}", f"{p_cat['scn']['count']} projects")

        with col2:
            st.markdown("##### 🏢 Other Branches (Funded by You)")
            o_cat = cats['other']
            st.metric(label="Total Balance", value=f"${o_cat['total_balance']:,.0f}", delta=f"{o_cat['total_count']} projects")
            if o_cat['total_count'] > 0:
                c1, c2, c3 = st.columns(3)
                c1.metric("OMN", f"${o_cat['omn']['balance']:,.0f}", f"{o_cat['omn']['count']} projects")
                c2.metric("OPN", f"${o_cat['opn']['balance']:,.0f}", f"{o_cat['opn']['count']} projects")
                c3.metric("SCN", f"${o_cat['scn']['balance']:,.0f}", f"{o_cat['scn']['count']} projects")

        # Top Funded 'Other' Branches
        if pm_analysis['other_bl_code_breakdown']:
            st.markdown("#### 🏗️ Top Branches Funded by You")
            st.info("💡 Monitor these departments to assess performance and see if you need to reclaim funding.")
            for i, (bl_code, bl_data) in enumerate(pm_analysis['other_bl_code_breakdown'][:5]):
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #34495eaa, #2c3e50aa); color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h5 style="margin:0;">#{i+1}: {bl_code}</h5>
                        <div>
                            <span style="margin-right: 1rem;"><strong>Projects:</strong> {bl_data["count"]}</span>
                            <span><strong>Balance:</strong> ${bl_data["balance"]:,.0f}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(pm_message)

st.markdown("---")

# --- Main Branch Analysis Section ---
st.markdown(f"### 🗂️ Branch Analysis for {selected_bl}")

# Auto-extract data when file or BL code changes
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
else:
    extracted_data = None
    top_cos = []

# Data Input Fields (pre-filled if data extracted, otherwise default)
col1, col2, col3 = st.columns(3)
omn_default = {'balance': 44053.0, 'L': 44053.0, 'M': 0.0, 'T': 0.0}
opn_default = {'balance': 1947299.0, 'L': 1947299.0, 'M': 0.0, 'T': 0.0}
scn_default = {'balance': 1148438.0, 'L': 813595.0, 'M': 334843.0, 'T': 0.0}

data_source = extracted_data if extracted_data else {'omn': omn_default, 'opn': opn_default, 'scn': scn_default}

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

# --- Calculate & Display Results ---
if st.button("🚀 Calculate Full Analysis", type="primary", use_container_width=True):
    # Core Calculations
    report_datetime = datetime.combine(report_date, datetime.min.time())
    
    # Expiry dates
    omn_expiry = get_appropriation_expiry_date('OMN', fiscal_year)
    opn_expiry = get_appropriation_expiry_date('OPN', fiscal_year)
    scn_expiry = get_appropriation_expiry_date('SCN', fiscal_year)

    # Working days
    omn_working_days = count_working_days(report_datetime, omn_expiry, fiscal_year)
    opn_working_days = count_working_days(report_datetime, opn_expiry, fiscal_year)
    scn_working_days = count_working_days(report_datetime, scn_expiry, fiscal_year)

    # Expiring soon checks
    omn_expiring_soon = is_expiring_soon(report_datetime, omn_expiry, 2)
    opn_expiring_soon = is_expiring_soon(report_datetime, opn_expiry, 2)
    scn_expiring_soon = is_expiring_soon(report_datetime, scn_expiry, 2)
    
    # Personnel calculations
    monthly_personnel_cost = hourly_rate * hours_per_week * 4.333 * branch_size * (1 + overhead_rate / 100)
    total_balance = omn_balance + opn_balance + scn_balance

    # --- URGENT ALERTS ---
    urgent_appropriations = []
    if omn_expiring_soon and omn_balance > 0: urgent_appropriations.append(f"OMN (expires {omn_expiry.strftime('%b %d')})")
    if opn_expiring_soon and opn_balance > 0: urgent_appropriations.append(f"OPN (expires {opn_expiry.strftime('%b %d')})")
    if scn_expiring_soon and scn_balance > 0: urgent_appropriations.append(f"SCN (expires {scn_expiry.strftime('%b %d')})")
    
    if urgent_appropriations:
        st.error(f"🚨 **URGENT EXPIRY ALERT**: {', '.join(urgent_appropriations)} are expiring within 2 months!")
    
    # --- SMART APPN CHARGING STRATEGY ---
    st.markdown('<div class="bubble"><h3 style="text-align: center;">💡 Smart APPN Charging Strategy</h3><p style="text-align: center;">This prioritizes spending funds that expire the soonest to ensure no money is lost.</p></div>', unsafe_allow_html=True)
    
    # Create optimal charging strategy
    charging_strategy = []
    appn_data = [
        ("OMN", omn_balance, omn_expiry), 
        ("OPN", opn_balance, opn_expiry), 
        ("SCN", scn_balance, scn_expiry)
    ]
    appn_data.sort(key=lambda x: x[2]) # Sort by expiry date, earliest first
    
    cumulative_months = 0
    for appn, balance, expiry in appn_data:
        if balance > 0 and monthly_personnel_cost > 0:
            months_from_this_appn = balance / monthly_personnel_cost
            start_date = report_datetime + timedelta(days=cumulative_months * 30.44)
            end_date = start_date + timedelta(days=months_from_this_appn * 30.44)
            
            days_until_expiry = (expiry - report_datetime).days
            if days_until_expiry < 60: urgency, urgency_color = "🚨 URGENT", "#e74c3c"
            elif days_until_expiry < 120: urgency, urgency_color = "⚠️ PRIORITY", "#f39c12"
            else: urgency, urgency_color = "✅ PLANNED", "#27ae60"
            
            charging_strategy.append({
                'appn': appn, 'amount': balance, 'months': months_from_this_appn,
                'start_date': start_date, 'end_date': end_date, 'expiry_date': expiry,
                'urgency': urgency, 'urgency_color': urgency_color
            })
            cumulative_months += months_from_this_appn

    # Display charging strategy
    current_month_rec = charging_strategy[0] if charging_strategy else None
    if current_month_rec:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {current_month_rec['urgency_color']}, #333); color: white; padding: 2rem; border-radius: 15px; border: 2px solid white; text-align: center;">
            <h2>💳 This Month's Recommendation: Charge ALL Labor to {current_month_rec['appn']}</h2>
            <p style="font-size: 1.2em;">This appropriation expires the soonest. Using it first prevents loss of funds.</p>
            <p>This will cover costs for approx. <strong>{current_month_rec['months']:.1f} months</strong>, until around <strong>{current_month_rec['end_date'].strftime('%b %d, %Y')}</strong>.</p>
        </div>
        """, unsafe_allow_html=True)

    # --- ENHANCED ANALYSIS & VISUALIZATIONS ---
    st.markdown("### 📈 Financial Analysis & Visualizations")
    col1, col2 = st.columns(2)

    with col1: # Top Chargeable Objects
        if top_cos:
            st.markdown("##### 🎯 Top 5 Chargeable Objects")
            for i, co in enumerate(top_cos):
                expiry_date = get_appropriation_expiry_date(co['APPN'], fiscal_year)
                expiring_soon = is_expiring_soon(report_datetime, expiry_date, 2)
                card_class = "urgent-expiry" if expiring_soon else ""
                
                st.markdown(f"""
                <div class="status-card {card_class}" style="background: #4a4a4a; margin-bottom: 0.5rem; padding: 0.75rem; text-align: left;">
                    <strong>#{i+1}: {co["CO_Number"]} ({co["APPN"]})</strong><br>
                    Balance: ${co["Balance"]:,.0f} | Expires: {expiry_date.strftime("%b %d, %Y")}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Upload a VLA file to see the Top 5 Chargeable Objects for the selected BL Code.")
            
    with col2: # Funding breakdown charts
        st.markdown("##### 💰 Funding Composition")
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Labor', x=['OMN', 'OPN', 'SCN'], y=[omn_l, opn_l, scn_l], marker_color='#3498db'))
        fig.add_trace(go.Bar(name='Material', x=['OMN', 'OPN', 'SCN'], y=[omn_m, opn_m, scn_m], marker_color='#e74c3c'))
        fig.add_trace(go.Bar(name='Travel', x=['OMN', 'OPN', 'SCN'], y=[omn_t, opn_t, scn_t], marker_color='#f39c12'))
        fig.update_layout(title="L/M/T Breakdown by Appropriation", barmode='stack', height=300, margin=dict(l=20, r=20, t=40, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

    # PM Portfolio Charts (if enabled)
    if enable_pm_analysis and st.session_state.pm_portfolio_data:
        st.markdown("##### 👨‍💼 PM Portfolio Visualizations")
        pm_data = st.session_state.pm_portfolio_data
        c1, c2 = st.columns(2)
        with c1:
            if pm_data['total_portfolio_balance'] > 0:
                fig_pm_pie = px.pie(
                    values=[pm_data['categories']['personal']['total_balance'], pm_data['categories']['other']['total_balance']], 
                    names=['Your Home Branch', 'Funded to Others'], 
                    title="PM Funding Distribution",
                    color_discrete_map={'Your Home Branch':'#3498db', 'Funded to Others':'#e67e22'},
                    height=300
                )
                fig_pm_pie.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_pm_pie, use_container_width=True)
        with c2:
            if pm_data['other_bl_code_breakdown']:
                top_bl = pm_data['other_bl_code_breakdown'][:6]
                bl_names = [bl[0] for bl, _ in top_bl]
                bl_balances = [data['balance'] for _, data in top_bl]
                fig_pm_bar = px.bar(
                    x=bl_balances, y=bl_names, orientation='h',
                    title="Top Branches Funded by You",
                    color=bl_balances, color_continuous_scale='oranges',
                    height=300
                )
                fig_pm_bar.update_layout(showlegend=False, yaxis_title=None, xaxis_title="Balance ($)", yaxis={'categoryorder':'total ascending'}, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_pm_bar, use_container_width=True)


    # --- EXPORT SECTION ---
    st.markdown("### 📤 Export Results")
    export_cols = st.columns(4)

    # Export 1: Main Branch Analysis
    export_data = {'Metric': [], 'Value': []}
    for appn_name, appn_balance, expiry in [( 'OMN', omn_balance, omn_expiry), ('OPN', opn_balance, opn_expiry), ('SCN', scn_balance, scn_expiry)]:
        export_data['Metric'].extend([f'{appn_name} Balance', f'{appn_name} Expiry'])
        export_data['Value'].extend([f"${appn_balance:,.0f}", expiry.strftime('%Y-%m-%d')])
    csv_buffer = io.StringIO()
    pd.DataFrame(export_data).to_csv(csv_buffer, index=False)
    export_cols[0].download_button("📊 Download Branch Analysis", csv_buffer.getvalue(), f"Branch_Analysis_{selected_bl}.csv", mime="text/csv", use_container_width=True)
    
    # Export 2: Charging Strategy
    strategy_export = []
    for i, s in enumerate(charging_strategy, 1):
        strategy_export.append({ 'Phase': i, 'APPN': s['appn'], 'Amount': s['amount'], 'Covers (Months)': f"{s['months']:.1f}", 'Est_End_Date': s['end_date'].strftime('%Y-%m-%d'), 'Expiry_Date': s['expiry_date'].strftime('%Y-%m-%d')})
    strategy_csv_buffer = io.StringIO()
    pd.DataFrame(strategy_export).to_csv(strategy_csv_buffer, index=False)
    export_cols[1].download_button("📅 Download Charging Strategy", strategy_csv_buffer.getvalue(), f"Charging_Strategy_{selected_bl}.csv", mime="text/csv", use_container_width=True)

    # Export 3: PM Portfolio Projects
    if enable_pm_analysis and st.session_state.pm_projects:
        pm_projects_df = pd.DataFrame(st.session_state.pm_projects)
        pm_csv_buffer = io.StringIO()
        pm_projects_df.to_csv(pm_csv_buffer, index=False)
        export_cols[2].download_button("👨‍💼 Download PM Portfolio", pm_csv_buffer.getvalue(), f"PM_Portfolio_{pm_name_filter}.csv", mime="text/csv", use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>🚀 My Little BFM • Enhanced with Smart APPN Charging, Expiry Analysis, & PM Portfolio Insights</p></div>', unsafe_allow_html=True)
