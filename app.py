import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io

st.set_page_config(page_title="My Little BFM", page_icon="💰", layout="wide")

# Clean, modern CSS
st.markdown("""
<style>
.main-header {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;}
.metric-card {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin: 0.5rem 0;}
.bubble {background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 1.5rem; margin: 1rem 0; border: 1px solid rgba(255,255,255,0.3);}
.status-card {border-radius: 15px; padding: 1rem; text-align: center; margin: 0.5rem 0; color: white;}
.urgent-expiry {background: linear-gradient(135deg, #e74c3c, #c0392b) !important; animation: pulse 2s infinite;}
.warning-expiry {background: linear-gradient(135deg, #f39c12, #e67e22) !important;}
.normal-expiry {background: linear-gradient(135deg, #27ae60, #229954) !important;}
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

def get_federal_holidays(fiscal_year):
    """Get federal holidays for the specified fiscal year (Oct 1 - Sep 30)"""
    holidays = []
    
    if fiscal_year == 2024:
        holidays = [
            datetime(2023, 10, 9),   # Columbus Day (FY start)
            datetime(2023, 11, 10),  # Veterans Day (observed)
            datetime(2023, 11, 23),  # Thanksgiving
            datetime(2023, 11, 24),  # Day after Thanksgiving
            datetime(2023, 12, 25),  # Christmas
            datetime(2024, 1, 1),    # New Year's Day
            datetime(2024, 1, 15),   # MLK Day
            datetime(2024, 2, 19),   # Presidents Day
            datetime(2024, 5, 27),   # Memorial Day
            datetime(2024, 6, 19),   # Juneteenth
            datetime(2024, 7, 4),    # Independence Day
            datetime(2024, 9, 2),    # Labor Day
        ]
    elif fiscal_year == 2025:
        holidays = [
            datetime(2024, 10, 14),  # Columbus Day
            datetime(2024, 11, 11),  # Veterans Day
            datetime(2024, 11, 28),  # Thanksgiving
            datetime(2024, 11, 29),  # Day after Thanksgiving
            datetime(2024, 12, 25),  # Christmas
            datetime(2025, 1, 1),    # New Year's Day
            datetime(2025, 1, 20),   # MLK Day
            datetime(2025, 2, 17),   # Presidents Day
            datetime(2025, 5, 26),   # Memorial Day
            datetime(2025, 6, 19),   # Juneteenth
            datetime(2025, 7, 4),    # Independence Day
            datetime(2025, 9, 1),    # Labor Day
        ]
    elif fiscal_year == 2026:
        holidays = [
            datetime(2025, 10, 13),  # Columbus Day
            datetime(2025, 11, 11),  # Veterans Day
            datetime(2025, 11, 27),  # Thanksgiving
            datetime(2025, 11, 28),  # Day after Thanksgiving
            datetime(2025, 12, 25),  # Christmas
            datetime(2026, 1, 1),    # New Year's Day
            datetime(2026, 1, 19),   # MLK Day
            datetime(2026, 2, 16),   # Presidents Day
            datetime(2026, 5, 25),   # Memorial Day
            datetime(2026, 6, 19),   # Juneteenth
            datetime(2026, 7, 4),    # Independence Day (observed July 3)
            datetime(2026, 9, 7),    # Labor Day
        ]
    elif fiscal_year == 2027:
        holidays = [
            datetime(2026, 10, 12),  # Columbus Day
            datetime(2026, 11, 11),  # Veterans Day
            datetime(2026, 11, 26),  # Thanksgiving
            datetime(2026, 11, 27),  # Day after Thanksgiving
            datetime(2026, 12, 25),  # Christmas
            datetime(2027, 1, 1),    # New Year's Day
            datetime(2027, 1, 18),   # MLK Day
            datetime(2027, 2, 15),   # Presidents Day
            datetime(2027, 5, 31),   # Memorial Day
            datetime(2027, 6, 19),   # Juneteenth (observed June 18)
            datetime(2027, 7, 5),    # Independence Day (observed)
            datetime(2027, 9, 6),    # Labor Day
        ]
    
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
    """Get the actual expiry date for each appropriation type"""
    if 'OMN' in appn.upper():
        return datetime(fiscal_year, 9, 30)  # Sep 30
    elif 'OPN' in appn.upper():
        return datetime(fiscal_year, 11, 30)  # Nov 30
    elif 'SCN' in appn.upper():
        return datetime(fiscal_year, 12, 30)  # Dec 30
    else:
        return datetime(fiscal_year, 9, 30)  # Default to OMN expiry

def calculate_days_to_expiry(report_date, expiry_date):
    """Calculate working days until appropriation expires"""
    if expiry_date < report_date:
        return 0
    return (expiry_date - report_date).days

def is_expiring_soon(report_date, expiry_date, months=2):
    """Check if appropriation expires within specified months"""
    warning_date = report_date + timedelta(days=months * 30)
    return expiry_date <= warning_date

def extract_vla_data(file, target_bl):
    try:
        df = pd.read_excel(file, sheet_name='Consolidated Data', header=1)
        bl_data = df[df.iloc[:, 8].astype(str).str.contains(target_bl, na=False)]
        
        if bl_data.empty:
            return None, f"No data found for {target_bl}", []
        
        result = {'omn': {'planned': 0.0, 'budget': 0.0, 'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0},
                 'opn': {'planned': 0.0, 'budget': 0.0, 'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0},
                 'scn': {'planned': 0.0, 'budget': 0.0, 'balance': 0.0, 'L': 0.0, 'M': 0.0, 'T': 0.0}}
        
        chargeable_objects = []
        
        for _, row in bl_data.iterrows():
            appn = str(row.iloc[2]).upper()
            type_code = str(row.iloc[1]).upper().strip()
            co_number = str(row.iloc[3]) if len(df.columns) > 3 else "Unknown"
            
            try:
                planned = float(str(row.iloc[9]).replace('$', '').replace(',', '').strip() or 0)
                budget = float(str(row.iloc[10]).replace('$', '').replace(',', '').strip() or 0)
                balance = float(str(row.iloc[16]).replace('$', '').replace(',', '').strip() or 0)
                
                if balance > 0:
                    chargeable_objects.append({'CO_Number': co_number, 'APPN': appn, 'Type': type_code, 
                                             'Balance': balance, 'Budget': budget, 'Planned': planned})
            except:
                continue
            
            appn_key = 'omn' if 'OMN' in appn else 'scn' if 'SCN' in appn else 'opn'
            result[appn_key]['planned'] += planned
            result[appn_key]['budget'] += budget
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

# Initialize session state for extracted data
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'last_bl_code' not in st.session_state:
    st.session_state.last_bl_code = None
if 'top_cos' not in st.session_state:
    st.session_state.top_cos = []

# Data Input Section - Auto-extract when BL code changes
if uploaded_file:
    # Check if BL code changed - if so, re-extract data
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
    
    # Calculate expiry dates for each appropriation
    omn_expiry = get_appropriation_expiry_date('OMN', fiscal_year)
    opn_expiry = get_appropriation_expiry_date('OPN', fiscal_year)
    scn_expiry = get_appropriation_expiry_date('SCN', fiscal_year)
    
    # Calculate working days to each expiry
    omn_working_days = count_working_days(report_datetime, omn_expiry, fiscal_year)
    opn_working_days = count_working_days(report_datetime, opn_expiry, fiscal_year)
    scn_working_days = count_working_days(report_datetime, scn_expiry, fiscal_year)
    
    # Check which appropriations are expiring soon (within 2 months)
    omn_expiring_soon = is_expiring_soon(report_datetime, omn_expiry, 2)
    opn_expiring_soon = is_expiring_soon(report_datetime, opn_expiry, 2)
    scn_expiring_soon = is_expiring_soon(report_datetime, scn_expiry, 2)
    
    weekly_burn_rate = hourly_rate * hours_per_week * branch_size * (1 + overhead_rate / 100)
    total_balance = omn_balance + opn_balance + scn_balance
    total_labor = omn_l + opn_l + scn_l
    
    # Calculate individual appropriation burn rates and coverage
    omn_hours_needed = omn_working_days * 8 * branch_size if omn_working_days > 0 else 0
    opn_hours_needed = opn_working_days * 8 * branch_size if opn_working_days > 0 else 0
    scn_hours_needed = scn_working_days * 8 * branch_size if scn_working_days > 0 else 0
    
    omn_hours_available = omn_balance / hourly_rate if hourly_rate > 0 else 0
    opn_hours_available = opn_balance / hourly_rate if hourly_rate > 0 else 0
    scn_hours_available = scn_balance / hourly_rate if hourly_rate > 0 else 0
    
    omn_coverage = (omn_hours_available / omn_hours_needed * 100) if omn_hours_needed > 0 else 0
    opn_coverage = (opn_hours_available / opn_hours_needed * 100) if opn_hours_needed > 0 else 0
    scn_coverage = (scn_hours_available / scn_hours_needed * 100) if scn_hours_needed > 0 else 0
    
    # Overall metrics using earliest expiry date as limiting factor
    earliest_expiry = min([d for d in [omn_expiry, opn_expiry, scn_expiry] if d >= report_datetime], default=omn_expiry)
    working_days_to_earliest = count_working_days(report_datetime, earliest_expiry, fiscal_year)
    
    hours_needed = working_days_to_earliest * 8 * branch_size
    total_hours_available = total_balance / hourly_rate if hourly_rate > 0 else 0
    labor_hours_available = total_labor / hourly_rate if hourly_rate > 0 else 0
    
    coverage_pct = (total_hours_available / hours_needed * 100) if hours_needed > 0 else 0
    labor_coverage_pct = (labor_hours_available / hours_needed * 100) if hours_needed > 0 else 0
    
    hours_excess = total_hours_available - hours_needed
    weeks_funding = total_balance / weekly_burn_rate if weekly_burn_rate > 0 else float('inf')
    
    # Expiry Urgency Alert
    urgent_appropriations = []
    if omn_expiring_soon and omn_balance > 0:
        urgent_appropriations.append(f"OMN (expires {omn_expiry.strftime('%b %d, %Y')} - {(omn_expiry - report_datetime).days} days)")
    if opn_expiring_soon and opn_balance > 0:
        urgent_appropriations.append(f"OPN (expires {opn_expiry.strftime('%b %d, %Y')} - {(opn_expiry - report_datetime).days} days)")
    if scn_expiring_soon and scn_balance > 0:
        urgent_appropriations.append(f"SCN (expires {scn_expiry.strftime('%b %d, %Y')} - {(scn_expiry - report_datetime).days} days)")
    
    if urgent_appropriations:
        st.error(f"🚨 **URGENT EXPIRY ALERT**: The following appropriations expire within 2 months: {', '.join(urgent_appropriations)}")
    
    # Top 5 Chargeable Objects Table with expiry highlighting
    if top_cos:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #E67E22, #D35400); color: white; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
            <h2>🎯 Top 5 Recommended Chargeable Objects</h2>
            <p>Prioritized by balance, urgency, and expiry dates</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create enhanced CO data with expiry information
        co_data = []
        for i, co in enumerate(top_cos):
            priority = "HIGH" if co['Balance'] > 500000 else "MEDIUM" if co['Balance'] > 200000 else "LOW"
            appn = co['APPN']
            expiry_date = get_appropriation_expiry_date(appn, fiscal_year)
            days_to_expiry = (expiry_date - report_datetime).days
            expiring_soon = is_expiring_soon(report_datetime, expiry_date, 2)
            
            urgency = "🚨 URGENT" if expiring_soon else "⚠️ MONITOR" if days_to_expiry < 120 else "✅ STABLE"
            
            co_data.append({
                'Rank': f"#{i+1}",
                'Project Object': co['CO_Number'],
                'APPN': co['APPN'],
                'Balance': f"${co['Balance']:,.0f}",
                'Expires': expiry_date.strftime('%b %d, %Y'),
                'Days Left': days_to_expiry,
                'Urgency': urgency,
                'Priority': priority
            })
        
        df_cos = pd.DataFrame(co_data)
        st.dataframe(df_cos, use_container_width=True, hide_index=True)
        
        # Enhanced summary cards for top 3 with expiry info
        st.markdown("### 🏆 Top 3 Highlights with Expiry Status")
        col1, col2, col3 = st.columns(3)
        
        for idx, col in enumerate([col1, col2, col3]):
            if idx < len(top_cos):
                co = top_cos[idx]
                expiry_date = get_appropriation_expiry_date(co['APPN'], fiscal_year)
                days_to_expiry = (expiry_date - report_datetime).days
                expiring_soon = is_expiring_soon(report_datetime, expiry_date, 2)
                
                # Determine card styling based on expiry urgency
                if expiring_soon:
                    card_class = "urgent-expiry"
                    urgency_text = f"🚨 EXPIRES IN {days_to_expiry} DAYS"
                elif days_to_expiry < 120:
                    card_class = "warning-expiry"
                    urgency_text = f"⚠️ {days_to_expiry} days left"
                else:
                    card_class = "normal-expiry"
                    urgency_text = f"✅ {days_to_expiry} days left"
                
                priority = "HIGH" if co['Balance'] > 500000 else "MEDIUM" if co['Balance'] > 200000 else "LOW"
                appn_color = "#E74C3C" if 'OMN' in co['APPN'] else "#27AE60" if 'SCN' in co['APPN'] else "#F39C12"
                
                with col:
                    st.markdown(f"""
                    <div class="status-card {card_class}">
                        <h4>#{idx+1} - {co['CO_Number']}</h4>
                        <div style="background: {appn_color}; padding: 0.5rem; border-radius: 10px; margin: 0.5rem 0;">
                            {co['APPN']}
                        </div>
                        <h3>${co['Balance']:,.0f}</h3>
                        <p>{priority} Priority</p>
                        <p><strong>{urgency_text}</strong></p>
                        <p>Expires: {expiry_date.strftime('%b %d, %Y')}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Summary Metrics
    st.markdown('<div class="bubble"><h2 style="text-align: center;">📊 Financial Analysis Results</h2></div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><h4>💰 Total Balance</h4></div>', unsafe_allow_html=True)
        st.metric("Total Balance", f"${total_balance:,.0f}")
        st.metric("Weekly Burn Rate", f"${weekly_burn_rate:,.0f}")
    
    with col2:
        st.markdown('<div class="metric-card"><h4>⏰ Time Analysis</h4></div>', unsafe_allow_html=True)
        st.metric(f"Days to Earliest Expiry", f"{working_days_to_earliest}")
        weeks_display = f"{weeks_funding:.1f}" if weeks_funding != float('inf') else "∞"
        st.metric("Weeks of Funding", weeks_display)
    
    with col3:
        st.markdown('<div class="metric-card"><h4>👥 Hours Analysis</h4></div>', unsafe_allow_html=True)
        st.metric(f"Hours to Earliest Expiry", f"{hours_needed:,}")
        st.metric("Total Hours Available", f"{total_hours_available:,.0f}")
    
    with col4:
        st.markdown('<div class="metric-card"><h4>📈 Coverage</h4></div>', unsafe_allow_html=True)
        st.metric("Total Coverage", f"{coverage_pct:.1f}%")
        st.metric("Man Years Excess", f"{abs(hours_excess / 1740):.2f}")
    
    # Enhanced Appropriation Cards with individual expiry analysis
    st.markdown('<div class="bubble"><h3 style="text-align: center;">📅 Individual Appropriation Analysis</h3></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    colors = {'OMN': '#e74c3c', 'OPN': '#f39c12', 'SCN': '#27ae60'}
    
    appropriations_data = [
        ('OMN', omn_balance, omn_l, omn_m, omn_t, omn_expiry, omn_working_days, omn_coverage, omn_expiring_soon),
        ('OPN', opn_balance, opn_l, opn_m, opn_t, opn_expiry, opn_working_days, opn_coverage, opn_expiring_soon),
        ('SCN', scn_balance, scn_l, scn_m, scn_t, scn_expiry, scn_working_days, scn_coverage, scn_expiring_soon)
    ]
    
    for i, (appn, balance, l, m, t, expiry, working_days, coverage, expiring_soon) in enumerate(appropriations_data):
        with [col1, col2, col3][i]:
            # Determine card styling based on expiry urgency
            card_class = "urgent-expiry" if expiring_soon else "warning-expiry" if working_days < 60 else "normal-expiry"
            days_left = (expiry - report_datetime).days
            
            st.markdown(f"""
            <div class="status-card {card_class}" style="background: linear-gradient(135deg, {colors[appn]}aa, {colors[appn]}dd);">
                <h3>{appn} Appropriation</h3>
                <p><strong>Expires: {expiry.strftime('%b %d, %Y')}</strong></p>
                <p>🕒 {days_left} days ({working_days} working days)</p>
                <h4>${balance:,.0f}</h4>
                <p>Coverage: {coverage:.1f}%</p>
                <p>L: ${l:,.0f} | M: ${m:,.0f} | T: ${t:,.0f}</p>
                {f'<p style="font-weight: bold; animation: pulse 2s infinite;">🚨 EXPIRES SOON!</p>' if expiring_soon else ''}
            </div>
            """, unsafe_allow_html=True)
            
            # Individual appropriation metrics
            hours_available_appn = balance / hourly_rate if hourly_rate > 0 else 0
            hours_needed_appn = working_days * 8 * branch_size if working_days > 0 else 0
            weeks_remaining_appn = balance / weekly_burn_rate if weekly_burn_rate > 0 else float('inf')
            
            st.metric(f"{appn} Hours Available", f"{hours_available_appn:,.0f}")
            st.metric(f"{appn} Hours Needed", f"{hours_needed_appn:,}")
            weeks_display_appn = f"{weeks_remaining_appn:.1f}" if weeks_remaining_appn != float('inf') else "∞"
            st.metric(f"{appn} Weeks Funding", weeks_display_appn)
    
    # Charts
    st.markdown('<div class="bubble"><h3 style="text-align: center;">📈 Financial Visualizations</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # L/M/T Breakdown
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Labor', x=['OMN', 'OPN', 'SCN'], y=[omn_l, opn_l, scn_l], marker_color='#3498db'))
        fig.add_trace(go.Bar(name='Material', x=['OMN', 'OPN', 'SCN'], y=[omn_m, opn_m, scn_m], marker_color='#e74c3c'))
        fig.add_trace(go.Bar(name='Travel', x=['OMN', 'OPN', 'SCN'], y=[omn_t, opn_t, scn_t], marker_color='#f39c12'))
        fig.update_layout(title="L/M/T Breakdown", barmode='stack', height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Coverage by Appropriation with expiry urgency
        coverage_data = [omn_coverage, opn_coverage, scn_coverage]
        coverage_colors = ['#e74c3c' if omn_expiring_soon else '#27ae60',
                          '#f39c12' if opn_expiring_soon else '#27ae60', 
                          '#e74c3c' if scn_expiring_soon else '#27ae60']
        
        fig2 = go.Figure(data=[go.Bar(x=['OMN', 'OPN', 'SCN'], y=coverage_data, 
                                     marker_color=coverage_colors)])
        fig2.update_layout(title="Coverage % by Appropriation", height=400, yaxis_title="Coverage %")
        fig2.add_hline(y=100, line_dash="dash", line_color="white", 
                      annotation_text="100% Coverage Target")
        st.plotly_chart(fig2, use_container_width=True)
    
    # Enhanced Recommendations
    st.markdown('<div class="bubble"><h3 style="text-align: center;">📋 Strategic Recommendations</h3></div>', unsafe_allow_html=True)
    
    # Priority-based recommendations
    recommendations = []
    
    # Expiry urgency recommendations
    if urgent_appropriations:
        recommendations.append({
            'priority': 'URGENT',
            'message': f"🚨 **IMMEDIATE ACTION**: {', '.join(urgent_appropriations)} expire within 2 months. Prioritize spending these funds first.",
            'color': '#e74c3c'
        })
    
    # Coverage recommendations
    if omn_coverage < 80 and omn_balance > 0:
        recommendations.append({
            'priority': 'HIGH',
            'message': f"⚠️ **OMN DEFICIT**: Only {omn_coverage:.1f}% coverage. Need scope reduction or additional funding.",
            'color': '#f39c12'
        })
    
    if opn_coverage < 80 and opn_balance > 0:
        recommendations.append({
            'priority': 'HIGH', 
            'message': f"⚠️ **OPN DEFICIT**: Only {opn_coverage:.1f}% coverage. Need scope reduction or additional funding.",
            'color': '#f39c12'
        })
        
    if scn_coverage < 80 and scn_balance > 0:
        recommendations.append({
            'priority': 'HIGH',
            'message': f"⚠️ **SCN DEFICIT**: Only {scn_coverage:.1f}% coverage. Need scope reduction or additional funding.", 
            'color': '#f39c12'
        })
    
    # Surplus recommendations
    if omn_coverage > 120:
        excess_omn = (omn_coverage - 100) / 100 * omn_balance
        recommendations.append({
            'priority': 'OPPORTUNITY',
            'message': f"💡 **OMN SURPLUS**: {omn_coverage:.1f}% coverage. ~${excess_omn:,.0f} available for scope expansion.",
            'color': '#27ae60'
        })
    
    if opn_coverage > 120:
        excess_opn = (opn_coverage - 100) / 100 * opn_balance
        recommendations.append({
            'priority': 'OPPORTUNITY',
            'message': f"💡 **OPN SURPLUS**: {opn_coverage:.1f}% coverage. ~${excess_opn:,.0f} available for scope expansion.",
            'color': '#27ae60'
        })
        
    if scn_coverage > 120:
        excess_scn = (scn_coverage - 100) / 100 * scn_balance
        recommendations.append({
            'priority': 'OPPORTUNITY', 
            'message': f"💡 **SCN SURPLUS**: {scn_coverage:.1f}% coverage. ~${excess_scn:,.0f} available for scope expansion.",
            'color': '#27ae60'
        })
    
    # Overall funding recommendations
    if weeks_funding < 10:
        recommendations.append({
            'priority': 'URGENT',
            'message': f"🚨 **CRITICAL**: Only {weeks_funding:.1f} weeks of funding remaining at current burn rate!",
            'color': '#e74c3c'
        })
    
    # Display recommendations by priority
    for rec in sorted(recommendations, key=lambda x: {'URGENT': 0, 'HIGH': 1, 'OPPORTUNITY': 2}.get(x['priority'], 3)):
        if rec['priority'] == 'URGENT':
            st.error(rec['message'])
        elif rec['priority'] == 'HIGH':
            st.warning(rec['message'])
        else:
            st.success(rec['message'])
    
    # Export enhanced with expiry analysis
    st.markdown('<div class="bubble"><h3 style="text-align: center;">📤 Export Results</h3></div>', unsafe_allow_html=True)
    
    # Create comprehensive export data with expiry information
    export_data = {
        'Metric': [
            'Fiscal Year', 'Total Balance', 'Weekly Burn Rate', 'Weeks of Funding',
            'Days to Earliest Expiry', 'Hours to Earliest Expiry', 'Total Hours Available', 'Total Coverage %',
            'OMN Balance', 'OMN Expiry Date', 'OMN Days Left', 'OMN Working Days', 'OMN Coverage %', 'OMN Expiring Soon',
            'OPN Balance', 'OPN Expiry Date', 'OPN Days Left', 'OPN Working Days', 'OPN Coverage %', 'OPN Expiring Soon',
            'SCN Balance', 'SCN Expiry Date', 'SCN Days Left', 'SCN Working Days', 'SCN Coverage %', 'SCN Expiring Soon',
            'Labor Hours Available', 'Labor Coverage %'
        ],
        'Value': [
            f"FY{fiscal_year}", f"${total_balance:,.0f}", f"${weekly_burn_rate:,.0f}", weeks_display,
            f"{working_days_to_earliest}", f"{hours_needed:,}", f"{total_hours_available:,.0f}", f"{coverage_pct:.1f}%",
            f"${omn_balance:,.0f}", omn_expiry.strftime('%Y-%m-%d'), f"{(omn_expiry - report_datetime).days}", 
            f"{omn_working_days}", f"{omn_coverage:.1f}%", "YES" if omn_expiring_soon else "NO",
            f"${opn_balance:,.0f}", opn_expiry.strftime('%Y-%m-%d'), f"{(opn_expiry - report_datetime).days}",
            f"{opn_working_days}", f"{opn_coverage:.1f}%", "YES" if opn_expiring_soon else "NO",
            f"${scn_balance:,.0f}", scn_expiry.strftime('%Y-%m-%d'), f"{(scn_expiry - report_datetime).days}",
            f"{scn_working_days}", f"{scn_coverage:.1f}%", "YES" if scn_expiring_soon else "NO",
            f"{labor_hours_available:,.0f}", f"{labor_coverage_pct:.1f}%"
        ]
    }
    
    # Enhanced report text with expiry analysis
    report_text = f"""# My Little BFM - Enhanced Financial Analysis Report
**BL Code:** {selected_bl}
**Fiscal Year:** FY{fiscal_year}
**Report Date:** {report_date.strftime('%B %d, %Y')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
- **Total Balance:** ${total_balance:,.0f}
- **Weekly Burn Rate:** ${weekly_burn_rate:,.0f}
- **Days to Earliest Expiry:** {working_days_to_earliest}
- **Total Coverage:** {coverage_pct:.1f}%

## Appropriation Expiry Analysis (FY{fiscal_year})

### OMN Appropriation
- **Balance:** ${omn_balance:,.0f}
- **Expires:** {omn_expiry.strftime('%B %d, %Y')} ({(omn_expiry - report_datetime).days} days)
- **Working Days Remaining:** {omn_working_days}
- **Coverage:** {omn_coverage:.1f}%
- **Expiring Soon:** {'🚨 YES' if omn_expiring_soon else '✅ NO'}
- **L/M/T:** ${omn_l:,.0f} / ${omn_m:,.0f} / ${omn_t:,.0f}

### OPN Appropriation  
- **Balance:** ${opn_balance:,.0f}
- **Expires:** {opn_expiry.strftime('%B %d, %Y')} ({(opn_expiry - report_datetime).days} days)
- **Working Days Remaining:** {opn_working_days}
- **Coverage:** {opn_coverage:.1f}%
- **Expiring Soon:** {'🚨 YES' if opn_expiring_soon else '✅ NO'}
- **L/M/T:** ${opn_l:,.0f} / ${opn_m:,.0f} / ${opn_t:,.0f}

### SCN Appropriation
- **Balance:** ${scn_balance:,.0f}
- **Expires:** {scn_expiry.strftime('%B %d, %Y')} ({(scn_expiry - report_datetime).days} days)
- **Working Days Remaining:** {scn_working_days}
- **Coverage:** {scn_coverage:.1f}%
- **Expiring Soon:** {'🚨 YES' if scn_expiring_soon else '✅ NO'}
- **L/M/T:** ${scn_l:,.0f} / ${scn_m:,.0f} / ${scn_t:,.0f}

## Strategic Recommendations
"""
    
    if urgent_appropriations:
        report_text += f"- 🚨 **URGENT EXPIRY ALERT:** {', '.join(urgent_appropriations)}\n"
    
    for rec in recommendations:
        report_text += f"- {rec['message']}\n"
    
    if top_cos:
        report_text += f"""
## Top 5 Chargeable Objects with Expiry Status
"""
        for i, co in enumerate(top_cos, 1):
            expiry_date = get_appropriation_expiry_date(co['APPN'], fiscal_year)
            days_to_expiry = (expiry_date - report_datetime).days
            expiring_soon = is_expiring_soon(report_datetime, expiry_date, 2)
            urgency = "🚨 URGENT" if expiring_soon else "⚠️ MONITOR" if days_to_expiry < 120 else "✅ STABLE"
            
            report_text += f"""
### Rank #{i}: {co['CO_Number']}
- **Balance:** ${co['Balance']:,.0f}
- **Appropriation:** {co['APPN']}
- **Expires:** {expiry_date.strftime('%B %d, %Y')} ({days_to_expiry} days)
- **Urgency:** {urgency}
"""
    
    report_text += f"\n---\n*Enhanced report generated by My Little BFM for {selected_bl} analysis in FY{fiscal_year}*"
    
    csv_buffer = io.StringIO()
    pd.DataFrame(export_data).to_csv(csv_buffer, index=False)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📊 Download Enhanced CSV Report", 
            csv_buffer.getvalue(), 
            f"BFM_Enhanced_Analysis_{selected_bl}_FY{fiscal_year}_{report_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        st.download_button(
            "📄 Download Detailed Expiry Report", 
            report_text, 
            f"BFM_Expiry_Report_{selected_bl}_FY{fiscal_year}_{report_date.strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )

# Footer
st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>🚀 My Little BFM • Enhanced with Expiry Analysis</p></div>', unsafe_allow_html=True)
