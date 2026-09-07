# Helper to convert flight date string to image format: "Sun, 6 Sept"
def format_flight_date(date_val):
    if pd.isna(date_val) or not date_val:
        return "N/A"
    try:
        dt = pd.to_datetime(str(int(date_val)), format="%Y%m%d")
        # Format month as Sept if Sep
        month_str = dt.strftime("%b")
        if month_str == "Sep":
            month_str = "Sept"
        return f"{dt.strftime('%a')}, {dt.day} {month_str}"
    except Exception:
        return str(date_val)

# Helper to render the flight card matching Image 3
def render_flight_card(row, status_type="longest"):
    origin_code = row['ORIGIN']
    origin_city = row['ORIGIN_CITY']
    fl_date_formatted = format_flight_date(row['FL_DATE'])
    
    elapsed_time = safe_int(row['elapsed_time'])
    hours, mins = divmod(elapsed_time, 60)
    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
    
    # Departure & Arrival Timings
    crs_dep = format_time_str(row['crs_dep'])
    dep_time = format_time_str(row['dep_time']) if 'dep_time' in row and not pd.isna(row['dep_time']) else crs_dep
    
    crs_arr = format_time_str(row['crs_arr'])
    actual_arr = format_time_str(row['actual_arr'])
    
    arr_delay = safe_int(row['arr_delay'])
    
    # Green (#137333) for on-time/early, Red (#D93025) for delayed
    is_delayed = arr_delay > 0
    theme_color = "#D93025" if is_delayed else "#137333"
    delay_label = f"+{arr_delay}m delay" if is_delayed else f"{arr_delay}m delay" if arr_delay < 0 else "On Time"

    st.markdown(f"""
    <div style="background-color: #ffffff; border: 1px solid #dadce0; border-radius: 12px; padding: 20px; margin-bottom: 16px; font-family: 'Google Sans', Roboto, sans-serif;">
        <!-- Header Route Line -->
        <div style="display: flex; justify-content: space-between; align-items: center; position: relative;">
            <div style="font-size: 2.4rem; font-weight: 700; color: #202124; line-height: 1;">{origin_code}</div>
            
            <div style="flex-grow: 1; display: flex; flex-direction: column; align-items: center; margin: 0 16px; position: relative;">
                <div style="font-size: 0.85rem; color: #5f6368; font-weight: 500; margin-bottom: 2px;">{time_str}</div>
                
                <!-- Arrival Delay Pill at Center -->
                <div style="font-size: 0.75rem; font-weight: 700; color: {theme_color}; background-color: #f1f3f4; padding: 2px 8px; border-radius: 10px; margin-bottom: 4px;">
                    {delay_label}
                </div>
                
                <div style="width: 100%; height: 2px; background-color: {theme_color}; position: relative; display: flex; justify-content: flex-end; align-items: center;">
                    <span style="color: {theme_color}; font-size: 1rem; background-color: #ffffff; padding-left: 2px; margin-right: -4px;">✈</span>
                </div>
            </div>
            
            <div style="font-size: 2.4rem; font-weight: 700; color: #202124; line-height: 1;">ORD</div>
        </div>
        
        <!-- Airport Links -->
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #70757a; margin-top: 4px; margin-bottom: 16px;">
            <div><a href="#" style="color: #70757a; text-decoration: underline;">Airport info</a></div>
            <div><a href="#" style="color: #70757a; text-decoration: underline;">Airport info</a></div>
        </div>
        
        <!-- Flight Dates & Cities -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 0.95rem; color: #202124; margin-bottom: 12px;">
            <div><strong>{origin_city}</strong> · {fl_date_formatted}</div>
            <div style="border-left: 1px solid #e8eaed; padding-left: 16px;"><strong>Chicago</strong> · {fl_date_formatted}</div>
        </div>
        
        <!-- Timings Section -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div>
                <div style="font-size: 0.8rem; color: #5f6368;">Departed</div>
                <div style="font-size: 1.5rem; font-weight: 600; color: {theme_color}; line-height: 1.2;">{dep_time}</div>
                <div style="font-size: 0.85rem; color: #70757a; text-decoration: line-through;">{crs_dep}</div>
            </div>
            <div style="border-left: 1px solid #e8eaed; padding-left: 16px;">
                <div style="font-size: 0.8rem; color: #5f6368;">Arrived</div>
                <div style="font-size: 1.5rem; font-weight: 600; color: {theme_color}; line-height: 1.2;">{actual_arr}</div>
                <div style="font-size: 0.85rem; color: #70757a; text-decoration: line-through;">{crs_arr}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
