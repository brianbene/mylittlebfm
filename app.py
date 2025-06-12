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
.status-card {border-radius: 15px; padding: 1rem; text-align: center; margin: 0.5rem 0; color: white;}
.urgent-expiry {animation: pulse 2s infinite;}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
  100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
}
</style>
""", unsafe_allow_html=True)

# --- Function Definitions ---
def get_federal_holidays(year):
    if year == 2024 or year == 2025:
        # Federal Holidays for FY2025 (Oct 2024 - Sep 2025)
        return [
            datetime(2024, 10, 14), datetime(2024, 11, 11), datetime(2024, 11, 28),
            datetime(2024, 12, 25), datetime(2025, 1, 1), datetime(2025, 1, 20),
            datetime(2025, 2, 17), datetime(2025, 5, 26), datetime(2025, 6, 19),
            datetime(2025, 7, 4), datetime(2025, 9, 1)
        ]
    return []

def count_working_days(start_date, end_date):
    if start_date > end_date:
        return 0
    
    holidays_start_year = get_federal_holidays(start_date.year)
    holidays_end_year = get_federal_holidays(end_date.year)
    holidays = set(holidays_start_year + holidays_end_year)
    
    working_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in holidays:
            working_days += 1
        current_date += timedelta(days=1)
    return working_days

def get_appropriation_expiry_date(appn, fy):
    if 'OMN' in appn.upper():
        return datetime(fy, 9, 30)
    elif 'OPN' in appn.upper():
        return datetime(fy + 1, 9, 30)
    elif 'SCN' in appn.upper():
        return datetime(fy + 2, 9, 30)
    else:
        return datetime(fy, 9, 30)

def is_expiring_soon(report_dt, expiry_dt, months=2):
    return expiry_dt <= report_dt + timedelta(days=months * 30.5)

# --- Sidebar and Input Widgets ---
st.markdown('<div class="main-header"><h1>🚀 My Little BFM</h1><p>Budget & Financial Management System</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("📊 Upload VLA Excel", type=['xlsx', 'xls'])
    
    st.subheader("👥 Personnel")
    branch_size = st.number_input("Branch Size", min_value=1, value=17)
    hourly_rate = st.number_input("Hourly Rate ($)", min_value=0.01, value=141.36, step=0.01)
    hours_per_week = st.number_input("Hours/Week", min_value=1, max_value=80, value=40)
    
    st.subheader("📅 Dates & Fiscal Year")
    report_date = st.date_input("Report Date", value=date.today())
    fiscal_year = st.selectbox("Select Fiscal Year", [2024, 2025, 2026, 2027], index=1)

# --- Data Input Fields ---
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

# --- Analysis Trigger and Display ---
if st.button("🚀 Calculate Analysis", type="primary"):
    # ALL CALCULATIONS AND DISPLAY LOGIC NOW LIVE INSIDE THE BUTTON'S 'IF' BLOCK
    
    report_datetime = datetime.combine(report_date, datetime.min.time())
    
    # Expiry Dates
    omn_expiry = get_appropriation_expiry_date('OMN', fiscal_year)
    opn_expiry = get_appropriation_expiry_date('OPN', fiscal_year)
    scn_expiry = get_appropriation_expiry_date('SCN', fiscal_year)

    # Core Financial Metrics
    monthly_personnel_cost = hourly_rate * hours_per_week * 4.333 * branch_size
    total_balance = omn_balance + opn_balance + scn_balance

    # Days Left Calculation
    days_to_omn_expiry = (omn_expiry - report_datetime).days
    days_to_opn_expiry = (opn_expiry - report_datetime).days
    days_to_scn_expiry = (scn_expiry - report_datetime).days
    
    # Working Days Calculation
    working_days_omn = count_working_days(report_datetime, omn_expiry)
    working_days_opn = count_working_days(report_datetime, opn_expiry)
    working_days_scn = count_working_days(report_datetime, scn_expiry)

    # --- Display Results ---
    st.markdown("### 📊 Financial Health Overview")
    kpi_cols = st.columns(3)
    kpi_cols[0].metric("💰 Total Balance", f"${total_balance:,.0f}")
    
    # Guard against division by zero
    if monthly_personnel_cost > 0:
        months_of_burn = total_balance / monthly_personnel_cost
        kpi_cols[1].metric("⏳ Months of Burn", f"{months_of_burn:.1f} months")
    else:
        kpi_cols[1].metric("⏳ Months of Burn", "N/A")
        
    kpi_cols[2].metric("👩‍💻 Monthly Cost", f"${monthly_personnel_cost:,.0f}")
    
    st.markdown("---")
    
    # Appropriation Status Cards
    st.markdown("###  Appropriations Status")
    card_cols = st.columns(3)
    
    with card_cols[0]:
        st.markdown(f'<div class="status-card" style="background: linear-gradient(135deg, #e74c3c, #c0392b);"><h3>OMN</h3><h4>${omn_balance:,.0f}</h4><p>Expires: {omn_expiry.strftime("%b %d, %Y")}</p><p>({days_to_omn_expiry} days / {working_days_omn} work days)</p></div>', unsafe_allow_html=True)
    with card_cols[1]:
        st.markdown(f'<div class="status-card" style="background: linear-gradient(135deg, #f39c12, #e67e22);"><h3>OPN</h3><h4>${opn_balance:,.0f}</h4><p>Expires: {opn_expiry.strftime("%b %d, %Y")}</p><p>({days_to_opn_expiry} days / {working_days_opn} work days)</p></div>', unsafe_allow_html=True)
    with card_cols[2]:
        st.markdown(f'<div class="status-card" style="background: linear-gradient(135deg, #27ae60, #2ecc71);"><h3>SCN</h3><h4>${scn_balance:,.0f}</h4><p>Expires: {scn_expiry.strftime("%b %d, %Y")}</p><p>({days_to_scn_expiry} days / {working_days_scn} work days)</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Charting
    st.markdown("### 📈 Visualizations")
    chart_cols = st.columns(2)
    
    with chart_cols[0]:
        fig_balance = px.bar(
            x=['OMN', 'OPN', 'SCN'], 
            y=[omn_balance, opn_balance, scn_balance],
            title="Balance by Appropriation",
            labels={'x': 'Appropriation', 'y': 'Balance'},
            color=['OMN', 'OPN', 'SCN'],
            color_discrete_map={'OMN': '#e74c3c', 'OPN': '#f39c12', 'SCN': '#27ae60'}
        )
        st.plotly_chart(fig_balance, use_container_width=True)

    with chart_cols[1]:
        fig_lmt = go.Figure()
        fig_lmt.add_trace(go.Bar(name='Labor', x=['OMN', 'OPN', 'SCN'], y=[omn_l, opn_l, scn_l], marker_color='#3498db'))
        fig_lmt.add_trace(go.Bar(name='Material', x=['OMN', 'OPN', 'SCN'], y=[omn_m, opn_m, scn_m], marker_color='#e74c3c'))
        fig_lmt.add_trace(go.Bar(name='Travel', x=['OMN', 'OPN', 'SCN'], y=[omn_t, opn_t, scn_t], marker_color='#f39c12'))
        fig_lmt.update_layout(title="L/M/T Breakdown", barmode='stack')
        st.plotly_chart(fig_lmt, use_container_width=True)

st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>My Little BFM</p></div>', unsafe_allow_html=True)
