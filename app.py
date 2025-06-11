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
            phase_html = (
                f'<div style="background: linear-gradient(135deg, {strategy["urgency_color"]}aa, {strategy["urgency_color"]}dd); '
                f'color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">'
                f'<h4>Phase {i}: Charge to {strategy["appn"]} {strategy["urgency"]}</h4>'
                f'<p><strong>📅 Timeframe:</strong> {strategy["start_date"].strftime("%b %d, %Y")} → {strategy["end_date"].strftime("%b %d, %Y")} ({strategy["months"]:.1f} months)</p>'
                f'<p><strong>💰 Funding:</strong> ${strategy["amount"]:,.0f} | <strong>Remaining:</strong> ${strategy["remaining_balance"]:,.0f}</p>'
                f'<p><strong>⏰ {strategy["appn"]} Expires:</strong> {strategy["expiry_date"].strftime("%b %d, %Y")} ({(strategy["expiry_date"] - report_datetime).days} days)</p>'
                f'</div>'
            )
            st.markdown(phase_html, unsafe_allow_html=True)
    
    # CURRENT MONTH RECOMMENDATION
    current_month_rec = charging_strategy[0] if charging_strategy else None
    if current_month_rec:
        st.markdown("### 🎯 THIS MONTH'S CHARGING RECOMMENDATION")
        current_rec_html = (
            f'<div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 2rem; border-radius: 15px; '
            f'box-shadow: 0 8px 32px rgba(0,0,0,0.3); border: 2px solid white;">'
            f'<h2>💳 CHARGE ALL LABOR TO: {current_month_rec["appn"]}</h2>'
            f'<h3>{current_month_rec["urgency"]}</h3>'
            f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 1rem 0; text-align: center;">'
            f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
            f'<h4>Monthly Target</h4>'
            f'<h3>${monthly_personnel_cost:,.0f}</h3>'
            f'</div>'
            f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
            f'<h4>Use Through</h4>'
            f'<h3>{current_month_rec["end_date"].strftime("%b %Y")}</h3>'
            f'</div>'
            f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
            f'<h4>Days Until Expiry</h4>'
            f'<h3>{(current_month_rec["expiry_date"] - report_datetime).days}</h3>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(current_rec_html, unsafe_allow_html=True)
    
    # Top 5 Chargeable Objects with expiry highlighting
    if top_cos:
        st.markdown("### 🎯 Top 5 Chargeable Objects with Expiry Status")
        
        for i, co in enumerate(top_cos):
            expiry_date = get_appropriation_expiry_date(co['APPN'], fiscal_year)
            days_to_expiry = (expiry_date - report_datetime).days
            expiring_soon = is_expiring_soon(report_datetime, expiry_date, 2)
            
            urgency = "🚨 URGENT" if expiring_soon else "⚠️ MONITOR" if days_to_expiry < 120 else "✅ STABLE"
            card_class = "urgent-expiry" if expiring_soon else "status-card"
            
            co_card_html = (
                f'<div class="{card_class}" style="background: linear-gradient(135deg, #3498dbaa, #2980b9aa); '
                f'color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">'
                f'<h4>#{i+1}: {co["CO_Number"]} - {co["APPN"]}</h4>'
                f'<p><strong>Balance:</strong> ${co["Balance"]:,.0f}</p>'
                f'<p><strong>Expires:</strong> {expiry_date.strftime("%b %d, %Y")} ({days_to_expiry} days)</p>'
                f'<p><strong>Status:</strong> {urgency}</p>'
                f'</div>'
            )
            st.markdown(co_card_html, unsafe_allow_html=True)
    
    # Enhanced Appropriation Cards
    st.markdown("### 📅 Individual Appropriation Analysis")
    
    col1, col2, col3 = st.columns(3)
    colors = {'OMN': '#e74c3c', 'OPN': '#f39c12', 'SCN': '#27ae60'}
    
    appropriations_data = [
        ('OMN', omn_balance, omn_l, omn_m, omn_t, omn_expiry, omn_working_days, omn_expiring_soon),
        ('OPN', opn_balance, opn_l, opn_m, opn_t, opn_expiry, opn_working_days, opn_expiring_soon),
        ('SCN', scn_balance, scn_l, scn_m, scn_t, scn_expiry, scn_working_days, scn_expiring_soon)
    ]
    
    for i, (appn, balance, l, m, t, expiry, working_days, expiring_soon) in enumerate(appropriations_data):
        with [col1, col2, col3][i]:
            card_class = "urgent-expiry" if expiring_soon else "normal-expiry"
            days_left = (expiry - report_datetime).days
            
            # Calculate hours analysis for this appropriation to Dec 30
            working_days_to_dec30 = count_working_days(report_datetime, dec_30_date, fiscal_year)
            hours_needed_to_dec30 = working_days_to_dec30 * 8 * branch_size
            hours_available_appn = balance / hourly_rate if hourly_rate > 0 else 0
            hours_excess_appn = hours_available_appn - hours_needed_to_dec30
            
            appn_card_html = (
                f'<div class="status-card {card_class}" style="background: linear-gradient(135deg, {colors[appn]}aa, {colors[appn]}dd);">'
                f'<h3>{appn} Appropriation</h3>'
                f'<p><strong>Expires: {expiry.strftime("%b %d, %Y")}</strong></p>'
                f'<p>🕒 {days_left} days ({working_days} working days)</p>'
                f'<h4>${balance:,.0f}</h4>'
                f'<p>Personnel Months: {balance/monthly_personnel_cost:.1f}</p>'
                f'<p>L: ${l:,.0f} | M: ${m:,.0f} | T: ${t:,.0f}</p>'
                f'{"<p style=\"font-weight: bold; animation: pulse 2s infinite;\">🚨 EXPIRES SOON!</p>" if expiring_soon else ""}'
                f'</div>'
            )
            st.markdown(appn_card_html, unsafe_allow_html=True)
            
            # Individual hours analysis box for each appropriation
            hours_box_html = (
                f'<div style="background: rgba(255,255,255,0.15); border: 2px solid {colors[appn]}; '
                f'border-radius: 10px; padding: 1rem; margin: 0.5rem 0; color: black;">'
                f'<h5 style="color: {colors[appn]}; margin: 0 0 0.5rem 0;">📊 {appn} Hours Analysis (to Dec 30)</h5>'
                f'<div style="display: grid; grid-template-columns: 1fr; gap: 0.3rem; font-size: 0.9em;">'
                f'<div><strong>Hours Available:</strong> {hours_available_appn:,.0f}</div>'
                f'<div><strong>Hours Needed:</strong> {hours_needed_to_dec30:,}</div>'
                f'<div style="color: {"green" if hours_excess_appn >= 0 else "red"};"><strong>Hours {"Excess" if hours_excess_appn >= 0 else "Deficit"}:</strong> {abs(hours_excess_appn):,.0f}</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(hours_box_html, unsafe_allow_html=True)
    
    # Combined Analysis Box - Total to Dec 30
    st.markdown("### 🎯 Combined Branch Coverage Analysis (to Dec 30)")
    
    # Calculate total combined metrics to Dec 30
    working_days_to_dec30 = count_working_days(report_datetime, dec_30_date, fiscal_year)
    total_hours_needed_dec30 = working_days_to_dec30 * 8 * branch_size
    total_hours_available_dec30 = total_balance / hourly_rate if hourly_rate > 0 else 0
    total_hours_excess_dec30 = total_hours_available_dec30 - total_hours_needed_dec30
    
    # Calculate coverage percentage
    coverage_pct_dec30 = (total_hours_available_dec30 / total_hours_needed_dec30 * 100) if total_hours_needed_dec30 > 0 else 0
    
    # Determine status color based on coverage
    if coverage_pct_dec30 >= 100:
        status_color = "#27ae60"
        status_text = "✅ FULLY COVERED"
        status_message = "Branch operations secured through Dec 30"
    elif coverage_pct_dec30 >= 80:
        status_color = "#f39c12"
        status_text = "⚠️ CAUTION"
        status_message = "Adequate coverage but monitor closely"
    else:
        status_color = "#e74c3c"
        status_text = "🚨 CRITICAL"
        status_message = "Insufficient funding for full branch operations"
    
    # Create the status box HTML
    excess_deficit_text = "Excess" if total_hours_excess_dec30 >= 0 else "Deficit"
    excess_color = "lightgreen" if total_hours_excess_dec30 >= 0 else "lightcoral"
    
    status_html = (
        f'<div style="background: linear-gradient(135deg, {status_color}aa, {status_color}dd); '
        f'color: white; padding: 2rem; border-radius: 15px; margin: 1rem 0; text-align: center;">'
        f'<h2>🎯 BRANCH OPERATIONS STATUS: {status_text}</h2>'
        f'<h3>{status_message}</h3>'
        f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; margin: 1.5rem 0;">'
        f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
        f'<h4>Total Funding</h4>'
        f'<h3>${total_balance:,.0f}</h3>'
        f'</div>'
        f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
        f'<h4>Hours Available</h4>'
        f'<h3>{total_hours_available_dec30:,.0f}</h3>'
        f'</div>'
        f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
        f'<h4>Hours Needed</h4>'
        f'<h3>{total_hours_needed_dec30:,}</h3>'
        f'</div>'
        f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
        f'<h4>Hours {excess_deficit_text}</h4>'
        f'<h3 style="color: {excess_color};">{abs(total_hours_excess_dec30):,.0f}</h3>'
        f'</div>'
        f'</div>'
        f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px; margin: 1rem 0;">'
        f'<h4>Branch Coverage to Dec 30: {coverage_pct_dec30:.1f}%</h4>'
        f'<p>Working Days Remaining: {working_days_to_dec30} | Branch Size: {branch_size} people</p>'
        f'</div>'
        f'</div>'
    )
    
    st.markdown(status_html, unsafe_allow_html=True)
    
    # Show breakdown by appropriation contribution
    st.markdown("#### 📊 Funding Contribution Breakdown")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        omn_contribution = (omn_balance / total_balance * 100) if total_balance > 0 else 0
        st.metric("OMN Contribution", f"{omn_contribution:.1f}%", f"${omn_balance:,.0f}")
    
    with col2:
        opn_contribution = (opn_balance / total_balance * 100) if total_balance > 0 else 0
        st.metric("OPN Contribution", f"{opn_contribution:.1f}%", f"${opn_balance:,.0f}")
    
    with col3:
        scn_contribution = (scn_balance / total_balance * 100) if total_balance > 0 else 0
        st.metric("SCN Contribution", f"{scn_contribution:.1f}%", f"${scn_balance:,.0f}")
    
    # Strategic recommendations based on combined analysis
    if total_hours_excess_dec30 < 0:
        shortfall_amount = abs(total_hours_excess_dec30) * hourly_rate
        st.error(f"💰 **FUNDING SHORTFALL**: ${shortfall_amount:,.0f} additional funding needed for full branch operations through Dec 30")
        
        # Calculate what percentage of branch could be sustained
        sustainable_percentage = (total_hours_available_dec30 / total_hours_needed_dec30 * 100) if total_hours_needed_dec30 > 0 else 0
        sustainable_people = int(branch_size * sustainable_percentage / 100)
        
        st.warning(f"⚠️ **ALTERNATIVE**: Current funding can sustain {sustainable_people} people ({sustainable_percentage:.1f}% of branch) through Dec 30")
        
    elif total_hours_excess_dec30 > 0:
        excess_amount = total_hours_excess_dec30 * hourly_rate
        excess_months = total_hours_excess_dec30 / (8 * branch_size * 21.7)  # Average working days per month
        
        st.success(f"💡 **FUNDING SURPLUS**: ${excess_amount:,.0f} available for additional scope or {excess_months:.1f} extra months of operations")
    
    # Charts
    st.markdown("### 📈 Financial Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Labor', x=['OMN', 'OPN', 'SCN'], y=[omn_l, opn_l, scn_l], marker_color='#3498db'))
        fig.add_trace(go.Bar(name='Material', x=['OMN', 'OPN', 'SCN'], y=[omn_m, opn_m, scn_m], marker_color='#e74c3c'))
        fig.add_trace(go.Bar(name='Travel', x=['OMN', 'OPN', 'SCN'], y=[omn_t, opn_t, scn_t], marker_color='#f39c12'))
        fig.update_layout(title="L/M/T Breakdown", barmode='stack', height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig2 = px.bar(x=['OMN', 'OPN', 'SCN'], y=[omn_balance, opn_balance, scn_balance], 
                      title="Balance by Appropriation", color=['OMN', 'OPN', 'SCN'], 
                      color_discrete_map=colors, height=400)
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Benedicks Analysis Charts (if enabled and data available)
    if enable_pm_analysis and st.session_state.benedicks_data:
        st.markdown("### 📊 Benedicks Portfolio Visualizations")
        benedicks_data = st.session_state.benedicks_data
        benedicks_projects = st.session_state.benedicks_projects
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Benedicks Portfolio by Appropriation
            summary = benedicks_data['summary']
            appn_balances = [summary['omn']['balance'], summary['opn']['balance'], summary['scn']['balance'], summary['other']['balance']]
            appn_names = ['OMN', 'OPN', 'SCN', 'Other']
            
            # Filter out zero balances for cleaner pie chart
            filtered_data = [(name, balance) for name, balance in zip(appn_names, appn_balances) if balance > 0]
            if filtered_data:
                names, balances = zip(*filtered_data)
                fig3 = px.pie(values=balances, names=names, 
                             title="Benedicks Portfolio by Appropriation",
                             color_discrete_map={'OMN': '#e74c3c', 'OPN': '#f39c12', 'SCN': '#27ae60', 'Other': '#9b59b6'})
                st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            # Top Benedicks BL Codes
            if benedicks_data['bl_codes']:
                top_bl_codes = benedicks_data['bl_codes'][:8]  # Top 8 for readability
                bl_names = [bl[0][:20] + "..." if len(bl[0]) > 20 else bl[0] for bl, _ in top_bl_codes]  # Truncate long names
                bl_balances = [bl_data['balance'] for _, bl_data in top_bl_codes]
                
                fig4 = px.bar(x=bl_names, y=bl_balances,
                             title="Top Benedicks BL Codes by Balance",
                             color=bl_balances,
                             color_continuous_scale='viridis')
                fig4.update_layout(showlegend=False, xaxis_tickangle=-45, 
                                 xaxis_title="BL Code", yaxis_title="Balance ($)")
                st.plotly_chart(fig4, use_container_width=True)
        
        # Additional Benedicks analysis charts
        col3, col4 = st.columns(2)
        
        with col3:
            # Project count by appropriation
            appn_counts = [summary['omn']['count'], summary['opn']['count'], summary['scn']['count'], summary['other']['count']]
            filtered_count_data = [(name, count) for name, count in zip(appn_names, appn_counts) if count > 0]
            if filtered_count_data:
                names, counts = zip(*filtered_count_data)
                fig5 = px.bar(x=names, y=counts,
                             title="Benedicks Project Count by Appropriation",
                             color=names,
                             color_discrete_map={'OMN': '#e74c3c', 'OPN': '#f39c12', 'SCN': '#27ae60', 'Other': '#9b59b6'})
                fig5.update_layout(showlegend=False, yaxis_title="Number of Projects")
                st.plotly_chart(fig5, use_container_width=True)
        
        with col4:
            # L/M/T breakdown for Benedicks portfolio
            lmt_data = {
                'Type': ['Labor', 'Material', 'Travel'],
                'OMN': [summary['omn']['L'], summary['omn']['M'], summary['omn']['T']],
                'OPN': [summary['opn']['L'], summary['opn']['M'], summary['opn']['T']],
                'SCN': [summary['scn']['L'], summary['scn']['M'], summary['scn']['T']]
            }
            
            fig6 = go.Figure()
            fig6.add_trace(go.Bar(name='OMN', x=lmt_data['Type'], y=lmt_data['OMN'], marker_color='#e74c3c'))
            fig6.add_trace(go.Bar(name='OPN', x=lmt_data['Type'], y=lmt_data['OPN'], marker_color='#f39c12'))
            fig6.add_trace(go.Bar(name='SCN', x=lmt_data['Type'], y=lmt_data['SCN'], marker_color='#27ae60'))
            fig6.update_layout(title="Benedicks Portfolio L/M/T Breakdown", barmode='stack', height=400)
            st.plotly_chart(fig6, use_container_width=True)
    
    # Export
    st.markdown("### 📤 Export Results")
    
    export_data = {
        'Metric': ['Total Balance', 'Monthly Personnel Cost', 'Months to Dec 30', 'OMN Balance', 'OMN Expiry', 'OPN Balance', 'OPN Expiry', 'SCN Balance', 'SCN Expiry'],
        'Value': [f"${total_balance:,.0f}", f"${monthly_personnel_cost:,.0f}", f"{months_to_dec30:.1f}", 
                 f"${omn_balance:,.0f}", omn_expiry.strftime('%Y-%m-%d'), f"${opn_balance:,.0f}", 
                 opn_expiry.strftime('%Y-%m-%d'), f"${scn_balance:,.0f}", scn_expiry.strftime('%Y-%m-%d')]
    }
    
    csv_buffer = io.StringIO()
    pd.DataFrame(export_data).to_csv(csv_buffer, index=False)
    
    # Export Benedicks data if available
    benedicks_export_available = False
    if enable_pm_analysis and st.session_state.benedicks_projects:
        benedicks_projects = st.session_state.benedicks_projects
        benedicks_export_data = []
        for project in benedicks_projects:
            benedicks_export_data.append({
                'PM': project['PM'],
                'APPN': project['APPN'],
                'Type': project['Type'],
                'Balance': project['Balance'],
                'BL_Code': project['BL_Code'],
                'Description': project['Description']
            })
        
        benedicks_csv_buffer = io.StringIO()
        pd.DataFrame(benedicks_export_data).to_csv(benedicks_csv_buffer, index=False)
        benedicks_export_available = True
    
    if charging_strategy:
        strategy_export = []
        for i, strategy in enumerate(charging_strategy, 1):
            strategy_export.append({
                'Phase': i, 'APPN': strategy['appn'], 'Start_Date': strategy['start_date'].strftime('%Y-%m-%d'),
                'End_Date': strategy['end_date'].strftime('%Y-%m-%d'), 'Amount': strategy['amount'],
                'Expiry_Date': strategy['expiry_date'].strftime('%Y-%m-%d'), 'Urgency': strategy['urgency']
            })
        
        strategy_csv_buffer = io.StringIO()
        pd.DataFrame(strategy_export).to_csv(strategy_csv_buffer, index=False)
        
        if benedicks_export_available:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button("📊 Download Analysis CSV", csv_buffer.getvalue(), 
                                 f"BFM_Analysis_{selected_bl}_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")
            with col2:
                st.download_button("📅 Download Charging Strategy", strategy_csv_buffer.getvalue(),
                                 f"Charging_Strategy_{selected_bl}_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")
            with col3:
                st.download_button("👨‍💼 Download Benedicks Portfolio", benedicks_csv_buffer.getvalue(),
                                 f"Benedicks_Portfolio_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📊 Download Analysis CSV", csv_buffer.getvalue(), 
                                 f"BFM_Analysis_{selected_bl}_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")
            with col2:
                st.download_button("📅 Download Charging Strategy", strategy_csv_buffer.getvalue(),
                                 f"Charging_Strategy_{selected_bl}_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")
    else:
        if benedicks_export_available:
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📊 Download Analysis CSV", csv_buffer.getvalue(), 
                                 f"BFM_Analysis_{selected_bl}_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")
            with col2:
                st.download_button("👨‍💼 Download Benedicks Portfolio", benedicks_csv_buffer.getvalue(),
                                 f"Benedicks_Portfolio_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")
        else:
            st.download_button("📊 Download Analysis CSV", csv_buffer.getvalue(), 
                             f"BFM_Analysis_{selected_bl}_{report_date.strftime('%Y%m%d')}.csv", mime="text/csv")

# Footer
st.markdown("---")
st.markdown('<div style="text-align: center; opacity: 0.7;"><p>🚀 My Little BFM • Enhanced with Smart APPN Charging, Expiry Analysis & Benedicks Portfolio Analysis</p></div>', unsafe_allow_html=True)
                'import streamlit as st
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
    
    st.subheader("👨‍💼 Benedicks Analysis")
    enable_pm_analysis = st.checkbox("Enable Benedicks Portfolio Analysis", value=False)
    show_column_inspector = st.checkbox("🔍 Show Column Inspector", value=False)

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

# Column Inspector Section (if enabled and file uploaded)
if show_column_inspector and uploaded_file:
    st.markdown("### 🔍 Excel Column Inspector")
    st.info("This will help you identify which column contains the PM data")
    
    try:
        df = pd.read_excel(uploaded_file, sheet_name='Consolidated Data', header=1)
        
        # Show column headers
        st.markdown("#### 📋 Column Headers:")
        headers_data = []
        for i, col in enumerate(df.columns):
            headers_data.append({'Column Index': i, 'Column Name': str(col)})
        
        headers_df = pd.DataFrame(headers_data)
        st.dataframe(headers_df, use_container_width=True)
        
        # Show sample data for BL16200 entries
        bl16200_sample = df[df.iloc[:, 8].astype(str).str.contains('BL16200', na=False)]
        
        if not bl16200_sample.empty:
            st.markdown("#### 🎯 Sample BL16200 Data (First 5 rows):")
            st.markdown("Look for columns that might contain 'Benedicks' or PM names")
            
            # Show first 5 rows with all columns
            sample_display = bl16200_sample.head().copy()
            
            # Add column numbers as a header row for reference
            col_refs = [f"Col_{i}" for i in range(len(sample_display.columns))]
            
            st.write("**Column Reference Numbers:**")
            col_ref_df = pd.DataFrame([col_refs], columns=sample_display.columns)
            st.dataframe(col_ref_df, use_container_width=True)
            
            st.write("**Sample Data:**")
            st.dataframe(sample_display, use_container_width=True)
            
            # Check each column for potential PM data
            st.markdown("#### 🕵️ PM Detection Analysis:")
            potential_pm_columns = []
            
            for i, col in enumerate(df.columns):
                if i < len(bl16200_sample.columns):
                    col_data = bl16200_sample.iloc[:, i].astype(str).str.lower()
                    benedicks_count = col_data.str.contains('benedicks', na=False).sum()
                    
                    if benedicks_count > 0:
                        potential_pm_columns.append({
                            'Column Index': i,
                            'Column Name': str(col),
                            'Benedicks Matches': benedicks_count,
                            'Sample Values': ', '.join(col_data.dropna().unique()[:3])
                        })
            
            if potential_pm_columns:
                st.success("🎉 Found potential PM columns with 'Benedicks'!")
                pm_df = pd.DataFrame(potential_pm_columns)
                st.dataframe(pm_df, use_container_width=True)
            else:
                st.warning("⚠️ No columns found containing 'Benedicks'. Try expanding the search or check spelling.")
                
                # Show unique values from likely PM columns (columns 5-15)
                st.markdown("#### 🔍 Checking columns 5-15 for PM-like data:")
                for i in range(5, min(16, len(df.columns))):
                    if i < len(bl16200_sample.columns):
                        unique_vals = bl16200_sample.iloc[:, i].dropna().astype(str).unique()[:10]
                        if len(unique_vals) > 0:
                            st.write(f"**Column {i} ({df.columns[i]}):** {', '.join(unique_vals)}")
        else:
            st.warning("No BL16200 data found in the uploaded file.")
            
    except Exception as e:
        st.error(f"Error inspecting file: {str(e)}")

# Benedicks Portfolio Analysis Section (if enabled and file uploaded)
if enable_pm_analysis and uploaded_file:
    st.markdown("### 👨‍💼 Benedicks Portfolio Analysis (Non-BL12200)")
    
    # Analyze Benedicks portfolio data
    benedicks_analysis, benedicks_message, benedicks_projects = analyze_benedicks_portfolio(uploaded_file)
    st.session_state.benedicks_data = benedicks_analysis
    st.session_state.benedicks_projects = benedicks_projects
    
    if benedicks_analysis:
        st.success(benedicks_message)
        
        # Display comprehensive summary
        total_balance = benedicks_analysis['total_balance']
        total_count = benedicks_analysis['total_count']
        summary = benedicks_analysis['summary']
        
        # Main Benedicks Portfolio Card
        benedicks_card_html = (
            f'<div class="pm-analysis-card">'
            f'<h3>🎯 Benedicks Portfolio Analysis (Excluding BL12200)</h3>'
            f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 1rem; margin: 1rem 0; text-align: center;">'
            f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
            f'<h4>Total Projects</h4>'
            f'<h3>{total_count}</h3>'
            f'</div>'
            f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
            f'<h4>Total Portfolio Value</h4>'
            f'<h3>${total_balance:,.0f}</h3>'
            f'</div>'
            f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
            f'<h4>Avg Project Size</h4>'
            f'<h3>${total_balance/total_count:,.0f}</h3>'
            f'</div>'
            f'<div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px;">'
            f'<h4>Personnel Months</h4>'
            f'<h3>{total_balance/(hourly_rate * hours_per_week * 4.3 * (1 + overhead_rate / 100)):,.1f}</h3>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(benedicks_card_html, unsafe_allow_html=True)
        
        # Appropriation breakdown for Benedicks portfolio
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
        
        # Top BL Codes Analysis
        if benedicks_analysis['bl_codes']:
            st.markdown("#### 🏗️ Top BL Codes in Benedicks Portfolio")
            for i, (bl_code, bl_data) in enumerate(benedicks_analysis['bl_codes'][:5]):
                bl_html = (
                    f'<div style="background: linear-gradient(135deg, #2c3e50aa, #34495eaa); '
                    f'color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">'
                    f'<h5>#{i+1}: {bl_code}</h5>'
                    f'<p><strong>Projects:</strong> {bl_data["count"]} | <strong>Total Balance:</strong> ${bl_data["balance"]:,.0f}</p>'
                    f'<div style="display: flex; gap: 1rem; flex-wrap: wrap;">'
                )
                
                # Add type breakdown
                for type_code, type_data in bl_data['types'].items():
                    if type_code.strip():  # Only show non-empty types
                        bl_html += f'<span style="background: rgba(255,255,255,0.2); padding: 0.3rem 0.6rem; border-radius: 5px; font-size: 0.9em;">{type_code}: ${type_data["balance"]:,.0f}</span>'
                
                bl_html += '</div></div>'
                st.markdown(bl_html, unsafe_allow_html=True)
        
        # Top Individual Projects
        if benedicks_projects:
            st.markdown("#### 🎯 Top Benedicks Projects")
            for i, project in enumerate(benedicks_projects[:10]):
                project_html = (
                    f'<div style="background: linear-gradient(135deg, #8e44adaa, #9b59b6aa); '
                    f'color: white; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">'
                    f'<h5>#{i+1}: {project["BL_Code"]}</h5>'
                    f'<p><strong>PM:</strong> {project["PM"]} | <strong>APPN:</strong> {project["APPN"]} | <strong>Type:</strong> {project["Type"]}</p>'
                    f'<p><strong>Balance:</strong> ${project["Balance"]:,.0f}</p>'
                    f'<p><strong>Description:</strong> {project["Description"][:100]}{"..." if len(project["Description"]) > 100 else ""}</p>'
                    f'</div>'
                )
                st.markdown(project_html, unsafe_allow_html=True)
    else:
        st.warning(benedicks_message)

# Data Input Section - Auto-extract when BL code changes
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
        st.markdown('<div class="metric-card"><h4>OMN
