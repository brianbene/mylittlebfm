import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import io

st.set_page_config(page_title="My Little BFM", page_icon="💰", layout="wide")

# Clean, modern CSS
st.markdown("""
<style>
.main-header {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;}
.metric-card {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin: 0.5rem 0;}
.bubble {background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 20px; padding: 1.5rem; margin: 1rem 0; border: 1px solid rgba(255,255,255,0.3);}
.status-card {border-radius: 15px; padding: 1rem; text-align: center; margin: 0.5rem 0; color: white;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🚀 My Little BFM</h1><p>Budget & Financial Management System</p></div>',
            unsafe_allow_html=True)

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
            datetime(2023, 10, 9),  # Columbus Day (FY start)
            datetime(2023, 11, 10),  # Veterans Day (observed)
            datetime(2023, 11, 23),  # Thanksgiving
            datetime(2023, 11, 24),  # Day after Thanksgiving
            datetime(2023, 12, 25),  # Christmas
            datetime(2024, 1, 1),  # New Year's Day
            datetime(2024, 1, 15),  # MLK Day
            datetime(2024, 2, 19),  # Presidents Day
            datetime(2024, 5, 27),  # Memorial Day
            datetime(2024, 6, 19),  # Juneteenth
            datetime(2024, 7, 4),  # Independence Day
            datetime(2024, 9, 2),  # Labor Day
        ]
    elif fiscal_year == 2025:
        holidays = [
            datetime(2024, 10, 14),  # Columbus Day
            datetime(2024, 11, 11),  # Veterans Day
            datetime(2024, 11, 28),  # Thanksgiving
            datetime(2024, 11, 29),  # Day after Thanksgiving
            datetime(2024, 12, 25),  # Christmas
            datetime(2025, 1, 1),  # New Year's Day
            datetime(2025, 1, 20),  # MLK Day
            datetime(2025, 2, 17),  # Presidents Day
            datetime(2025, 5, 26),  # Memorial Day
            datetime(2025, 6, 19),  # Juneteenth
            datetime(2025, 7, 4),  # Independence Day
            datetime(2025, 9, 1),  # Labor Day
        ]
    elif fiscal_year == 2026:
        holidays = [
            datetime(2025, 10, 13),  # Columbus Day
            datetime(2025, 11, 11),  # Veterans Day
            datetime(2025, 11, 27),  # Thanksgiving
            datetime(2025, 11, 28),  # Day after Thanksgiving
            datetime(2025, 12, 25),  # Christmas
            datetime(2026, 1, 1),  # New Year's Day
            datetime(2026, 1, 19),  # MLK Day
            datetime(2026, 2, 16),  # Presidents Day
            datetime(2026, 5, 25),  # Memorial Day
            datetime(2026, 6, 19),  # Juneteenth
            datetime(2026, 7, 4),  # Independence Day (observed July 3)
            datetime(2026, 9, 7),  # Labor Day
        ]
    elif fiscal_year == 2027:
        holidays = [
            datetime(2026, 10, 12),  # Columbus Day
            datetime(2026, 11, 11),  # Veterans Day
            datetime(2026, 11, 26),  # Thanksgiving
            datetime(2026, 11, 27),  # Day after Thanksgiving
            datetime(2026, 12, 25),  # Christmas
            datetime(2027, 1, 1),  # New Year's Day
            datetime(2027, 1, 18),  # MLK Day
            datetime(2027, 2, 15),  # Presidents Day
            datetime(2027, 5, 31),  # Memorial Day
            datetime(2027, 6, 19),  # Juneteenth (observed June 18)
            datetime(2027, 7, 5),  # Independence Day (observed)
            datetime(2027, 9, 6),  # Labor Day
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


# Data Input Section
if uploaded_file:
    extracted_data, message, top_cos = extract_vla_data(uploaded_file, selected_bl)
    st.info(message)

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

    # Determine fiscal year end date based on selected fiscal year
    fy_end_date = datetime(fiscal_year, 9, 30)  # Federal FY ends Sept 30
    working_days_to_fy_end = count_working_days(report_datetime, fy_end_date, fiscal_year)

    # Also calculate to Dec 30 for comparison
    dec_30 = datetime(fiscal_year - 1 if fiscal_year > 2025 else 2025, 12, 30)
    working_days_to_dec30 = count_working_days(report_datetime, dec_30, fiscal_year)

    weekly_burn_rate = hourly_rate * hours_per_week * branch_size * (1 + overhead_rate / 100)
    total_balance = omn_balance + opn_balance + scn_balance
    total_labor = omn_l + opn_l + scn_l

    # Use fiscal year end for primary calculations
    hours_needed = working_days_to_fy_end * 8 * branch_size
    total_hours_available = total_balance / hourly_rate if hourly_rate > 0 else 0
    labor_hours_available = total_labor / hourly_rate if hourly_rate > 0 else 0

    coverage_pct = (total_hours_available / hours_needed * 100) if hours_needed > 0 else 0
    labor_coverage_pct = (labor_hours_available / hours_needed * 100) if hours_needed > 0 else 0

    hours_excess = total_hours_available - hours_needed
    weeks_funding = total_balance / weekly_burn_rate if weekly_burn_rate > 0 else float('inf')

    # Top 5 Chargeable Objects Table
    if top_cos:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #E67E22, #D35400); color: white; padding: 2rem; border-radius: 15px; margin: 2rem 0;">
            <h2>🎯 Top 5 Recommended Chargeable Objects</h2>
            <p>Prioritized by balance, urgency, and strategic value</p>
        </div>
        """, unsafe_allow_html=True)

        # Create a cleaner dataframe approach instead of raw HTML
        co_data = []
        for i, co in enumerate(top_cos):
            priority = "HIGH" if co['Balance'] > 500000 else "MEDIUM" if co['Balance'] > 200000 else "LOW"
            co_data.append({
                'Rank': f"#{i + 1}",
                'Project Object': co['CO_Number'],
                'APPN': co['APPN'],
                'Balance': f"${co['Balance']:,.0f}",
                'Priority': priority,
                'Description': f"{co['Type']} {co['APPN']} {selected_bl} Operations"
            })

        # Display as styled dataframe
        df_cos = pd.DataFrame(co_data)

        # Custom CSS for the dataframe
        st.markdown("""
        <style>
        .stDataFrame {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }
        .stDataFrame thead tr th {
            background: #E67E22 !important;
            color: white !important;
            font-weight: bold !important;
            text-align: center !important;
            padding: 1rem !important;
        }
        .stDataFrame tbody tr td {
            text-align: center !important;
            padding: 1rem !important;
            border-bottom: 1px solid #ECF0F1 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.dataframe(df_cos, use_container_width=True, hide_index=True)

        # Add color-coded summary cards for top 3
        st.markdown("### 🏆 Top 3 Highlights")
        col1, col2, col3 = st.columns(3)

        for idx, col in enumerate([col1, col2, col3]):
            if idx < len(top_cos):
                co = top_cos[idx]
                priority = "HIGH" if co['Balance'] > 500000 else "MEDIUM" if co['Balance'] > 200000 else "LOW"
                priority_color = "#27AE60" if priority == "HIGH" else "#F39C12" if priority == "MEDIUM" else "#E74C3C"
                appn_color = "#E74C3C" if 'OMN' in co['APPN'] else "#27AE60" if 'SCN' in co['APPN'] else "#F39C12"

                with col:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, {priority_color}aa, {priority_color}dd); 
                                color: white; padding: 1.5rem; border-radius: 15px; text-align: center;">
                        <h4>#{idx + 1} - {co['CO_Number']}</h4>
                        <div style="background: {appn_color}; padding: 0.5rem; border-radius: 10px; margin: 0.5rem 0;">
                            {co['APPN']}
                        </div>
                        <h3>${co['Balance']:,.0f}</h3>
                        <p>{priority} Priority</p>
                    </div>
                    """, unsafe_allow_html=True)

        # Strategy Box
        primary = top_cos[0]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #E67E22aa, #D35400aa); color: white; padding: 1.5rem; border-radius: 10px; margin: 1rem 0;">
            <h3>💡 Charging Strategy for {selected_bl}</h3>
            <p><strong>Primary Target:</strong> {primary['CO_Number']} ({primary['APPN']}) - ${primary['Balance']:,.0f} available</p>
            <p><strong>Total Available:</strong> ${sum(co['Balance'] for co in top_cos):,.0f} across top 5 objects</p>
        </div>
        """, unsafe_allow_html=True)

    # Summary Metrics
    st.markdown('<div class="bubble"><h2 style="text-align: center;">📊 Financial Analysis Results</h2></div>',
                unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><h4>💰 Total Balance</h4></div>', unsafe_allow_html=True)
        st.metric("Total Balance", f"${total_balance:,.0f}")
        st.metric("Weekly Burn Rate", f"${weekly_burn_rate:,.0f}")

    with col2:
        st.markdown('<div class="metric-card"><h4>⏰ Time Analysis</h4></div>', unsafe_allow_html=True)
        st.metric(f"Working Days to FY{fiscal_year} End", f"{working_days_to_fy_end}")
        weeks_display = f"{weeks_funding:.1f}" if weeks_funding != float('inf') else "∞"
        st.metric("Weeks of Funding", weeks_display)

    with col3:
        st.markdown('<div class="metric-card"><h4>👥 Hours Analysis</h4></div>', unsafe_allow_html=True)
        st.metric(f"Hours Needed to FY{fiscal_year} End", f"{hours_needed:,}")
        st.metric("Total Hours Available", f"{total_hours_available:,.0f}")

    with col4:
        st.markdown('<div class="metric-card"><h4>📈 Coverage</h4></div>', unsafe_allow_html=True)
        st.metric("Total Coverage", f"{coverage_pct:.1f}%")
        st.metric("Man Years Excess", f"{abs(hours_excess / 1740):.2f}")

    # Appropriation Cards
    col1, col2, col3 = st.columns(3)
    colors = {'OMN': '#e74c3c', 'OPN': '#f39c12', 'SCN': '#27ae60'}

    # Appropriation expiry dates based on fiscal year
    expiry_dates = {
        'OMN': f"Sep 30, {fiscal_year}",
        'OPN': f"Nov 30, {fiscal_year}",
        'SCN': f"Dec 30, {fiscal_year}"
    }

    for i, (appn, balance, l, m, t) in enumerate([('OMN', omn_balance, omn_l, omn_m, omn_t),
                                                  ('OPN', opn_balance, opn_l, opn_m, opn_t),
                                                  ('SCN', scn_balance, scn_l, scn_m, scn_t)]):
        with [col1, col2, col3][i]:
            st.markdown(f"""
            <div class="status-card" style="background: linear-gradient(135deg, {colors[appn]}aa, {colors[appn]}dd);">
                <h3>{appn} Appropriation</h3>
                <p>Expires: {expiry_dates[appn]}</p>
                <h4>${balance:,.0f}</h4>
                <p>L: ${l:,.0f} | M: ${m:,.0f} | T: ${t:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

    # Charts
    st.markdown('<div class="bubble"><h3 style="text-align: center;">📈 Financial Visualizations</h3></div>',
                unsafe_allow_html=True)

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
        # Balance by Appropriation
        fig2 = px.bar(x=['OMN', 'OPN', 'SCN'], y=[omn_balance, opn_balance, scn_balance],
                      title="Balance by Appropriation", color=['OMN', 'OPN', 'SCN'],
                      color_discrete_map=colors, height=400)
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Recommendations
    st.markdown('<div class="bubble"><h3 style="text-align: center;">📋 Strategic Recommendations</h3></div>',
                unsafe_allow_html=True)

    if weeks_funding < 10:
        st.error(f"🚨 URGENT: Only {weeks_funding:.1f} weeks of funding remaining!")

    if coverage_pct < 80:
        st.error(
            f"🚨 DEFICIT: Coverage only {coverage_pct:.1f}%. Need ${abs(hours_excess * hourly_rate):,.0f} more funding.")
    elif hours_excess > 0:
        st.success(f"💡 SURPLUS: {hours_excess:,.0f} excess hours ({hours_excess / 1740:.2f} man-years) available.")

    # Export
    st.markdown('<div class="bubble"><h3 style="text-align: center;">📤 Export Results</h3></div>',
                unsafe_allow_html=True)

    # Create comprehensive export data
    export_data = {
        'Metric': [
            'Fiscal Year', 'Total Balance', 'Weekly Burn Rate', 'Weeks of Funding',
            f'Working Days to FY{fiscal_year} End', f'Hours Needed to FY{fiscal_year} End',
            'Total Hours Available', 'Total Coverage %', 'Hours Excess/Deficit', 'Man Years Excess/Deficit',
            'OMN Balance', 'OMN Labor', 'OMN Material', 'OMN Travel',
            'OPN Balance', 'OPN Labor', 'OPN Material', 'OPN Travel',
            'SCN Balance', 'SCN Labor', 'SCN Material', 'SCN Travel',
            'Labor-Only Hours', 'Labor Coverage %'
        ],
        'Value': [
            f"FY{fiscal_year}", f"${total_balance:,.0f}", f"${weekly_burn_rate:,.0f}", weeks_display,
            f"{working_days_to_fy_end}", f"{hours_needed:,}",
            f"{total_hours_available:,.0f}", f"{coverage_pct:.1f}%", f"{hours_excess:,.0f}",
            f"{abs(hours_excess / 1740):.2f}",
            f"${omn_balance:,.0f}", f"${omn_l:,.0f}", f"${omn_m:,.0f}", f"${omn_t:,.0f}",
            f"${opn_balance:,.0f}", f"${opn_l:,.0f}", f"${opn_m:,.0f}", f"${opn_t:,.0f}",
            f"${scn_balance:,.0f}", f"${scn_l:,.0f}", f"${scn_m:,.0f}", f"${scn_t:,.0f}",
            f"{labor_hours_available:,.0f}", f"{labor_coverage_pct:.1f}%"
        ]
    }

    # Create detailed report text
    report_text = f"""# My Little BFM - Financial Analysis Report
**BL Code:** {selected_bl}
**Fiscal Year:** FY{fiscal_year}
**Report Date:** {report_date.strftime('%B %d, %Y')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
- **Total Balance:** ${total_balance:,.0f}
- **Weekly Burn Rate:** ${weekly_burn_rate:,.0f}
- **Weeks of Funding:** {weeks_display}
- **Total Coverage:** {coverage_pct:.1f}%
- **Working Days to FY{fiscal_year} End:** {working_days_to_fy_end}

## Appropriation Breakdown (FY{fiscal_year})
### OMN (Expires Sep 30, {fiscal_year})
- **Balance:** ${omn_balance:,.0f}
- **Labor (L):** ${omn_l:,.0f}
- **Material (M):** ${omn_m:,.0f}
- **Travel (T):** ${omn_t:,.0f}

### OPN (Expires Nov 30, {fiscal_year})
- **Balance:** ${opn_balance:,.0f}
- **Labor (L):** ${opn_l:,.0f}
- **Material (M):** ${opn_m:,.0f}
- **Travel (T):** ${opn_t:,.0f}

### SCN (Expires Dec 30, {fiscal_year})
- **Balance:** ${scn_balance:,.0f}
- **Labor (L):** ${scn_l:,.0f}
- **Material (M):** ${scn_m:,.0f}
- **Travel (T):** ${scn_t:,.0f}

## Personnel Analysis
- **Branch Size:** {branch_size} people
- **Hourly Rate:** ${hourly_rate:.2f}/hr
- **Hours per Week:** {hours_per_week}
- **Overhead Rate:** {overhead_rate}%
- **Total Hours Available (L+M+T):** {total_hours_available:,.0f}
- **Labor-Only Hours Available:** {labor_hours_available:,.0f}
- **Hours Needed to FY{fiscal_year} End:** {hours_needed:,}
- **Hours Excess/Deficit:** {hours_excess:,.0f} ({hours_excess / 1740:.2f} man-years)

## Federal Holidays Excluded (FY{fiscal_year})
Federal holidays for FY{fiscal_year} have been excluded from working day calculations.
"""

    if top_cos:
        report_text += f"""
## Top 5 Highest Chargeable Objects
"""
        for i, co in enumerate(top_cos, 1):
            priority = "HIGH" if co['Balance'] > 500000 else "MEDIUM" if co['Balance'] > 200000 else "LOW"
            report_text += f"""
### Rank #{i}: {co['CO_Number']}
- **Balance:** ${co['Balance']:,.0f}
- **Budget:** ${co['Budget']:,.0f}
- **Planned:** ${co['Planned']:,.0f}
- **Appropriation:** {co['APPN']}
- **Type:** {co['Type']}
- **Priority:** {priority}
"""

    # Add strategic recommendations to report
    report_text += "\n## Strategic Recommendations\n"
    if weeks_funding < 10:
        report_text += f"- 🚨 **URGENT ACTION REQUIRED:** Only {weeks_funding:.1f} weeks of funding remaining at current burn rate.\n"

    if coverage_pct < 80:
        report_text += f"- 🚨 **FUNDING DEFICIT:** Coverage only {coverage_pct:.1f}%. Need additional ${abs(hours_excess * hourly_rate):,.0f} in funding or scope reduction.\n"
    elif hours_excess > 0:
        report_text += f"- 💡 **FUNDING SURPLUS:** {hours_excess:,.0f} excess hours ({hours_excess / 1740:.2f} man-years) available for scope expansion or reallocation.\n"

    report_text += f"\n---\n*Report generated by My Little BFM for {selected_bl} analysis in FY{fiscal_year}*"

    csv_buffer = io.StringIO()
    pd.DataFrame(export_data).to_csv(csv_buffer, index=False)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📊 Download CSV Report",
            csv_buffer.getvalue(),
            f"BFM_Analysis_{selected_bl}_FY{fiscal_year}_{report_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    with col2:
        st.download_button(
            "📄 Download Detailed Report",
            report_text,
            f"BFM_Report_{selected_bl}_FY{fiscal_year}_{report_date.strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )

# Footer
st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>🚀 My Little BFM • Built with Streamlit</p></div>',
            unsafe_allow_html=True)