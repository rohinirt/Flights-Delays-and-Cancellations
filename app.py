import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import urllib.request

# Page Configuration
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Flight Intelligence",
    page_icon="✈️",
    layout="wide"
)

# Core Styling to visually unify components into card layouts
st.markdown("""
<style>
    .stApp {
        background-color: #F8FAFC !important;
    }
    
    /* Single Box KPI Card Container */
    .kpi-card-unified {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 12px 12px 4px 12px !important;
        text-align: center;
    }
    
    .kpi-sparkline-container {
        background-color: #FFFFFF !important;
        border-left: 1px solid #CBD5E1 !important;
        border-right: 1px solid #CBD5E1 !important;
        border-bottom: 1px solid #CBD5E1 !important;
        border-radius: 0 0 10px 10px !important;
        padding: 0px 4px 6px 4px !important;
        margin-bottom: 12px;
    }
    
    /* Unified White Card Container Fix for Streamlit Blocks */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #CBD5E1 !important;
    }
    
    /* Segmented Control Styling inside Card Containers */
    div[data-testid="stSegmentedControl"] {
        background-color: #F1F5F9 !important;
        padding: 3px !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_connection():
    return duckdb.connect(database=':memory:')

@st.cache_data
def load_data():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flights AS 
        SELECT * FROM read_csv_auto('flights_2022.csv')
    """)
    return True

try:
    load_data()
    conn = get_db_connection()
except Exception as e:
    st.error(f"Error loading CSV dataset: {e}. Ensure 'flights_2022.csv' is in root directory.")
    st.stop()

# Helper function to generate KPI sparklines
def build_sparkline(df, y_col, bar_color):
    data = df.copy()
    month_map = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    data['month_code'] = data['month'].map(month_map)
    
    fig = px.bar(data, x='month_code', y=y_col)
    fig.update_traces(marker_color=bar_color, hovertemplate="%{x}: %{y:,.1f}<extra></extra>")
    fig.update_layout(
        margin=dict(l=2, r=2, t=4, b=12),
        height=65,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            tickfont=dict(size=8, color='#475569', weight='bold'),
            showgrid=False, zeroline=False, fixedrange=True, title="", showline=False
        ),
        yaxis=dict(visible=False, showgrid=False, fixedrange=True)
    )
    return fig

# Sidebar Filters
st.sidebar.title("✈️ ORD Analytics")
airlines = conn.execute('SELECT DISTINCT "AIRLINE_CODE" FROM flights WHERE "AIRLINE_CODE" IS NOT NULL').df().iloc[:, 0].dropna().tolist()
selected_airline = st.sidebar.multiselect("Select Airline", options=airlines, default=[])

where_clause = "WHERE \"DEST\" = 'ORD'"
params = []
if selected_airline:
    placeholders = ", ".join(["?"] * len(selected_airline))
    where_clause += f" AND \"AIRLINE_CODE\" IN ({placeholders})"
    params.extend(selected_airline)

st.title("🛬 ORD Arrivals Intelligence")

# 1. Fetch KPI Metrics
kpi_query = f"""
    SELECT 
        COUNT(*) AS total_flights,
        AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
        AVG("ARR_DELAY") AS avg_delay,
        SUM("CANCELLED") AS total_cancelled,
        SUM("DIVERTED") AS total_diverted
    FROM flights {where_clause}
"""
kpi_df = conn.execute(kpi_query, params).df()
tot_f, on_t, avg_d, tot_c, tot_div = kpi_df.iloc[0]

# 2. Fetch Monthly Trend Data for Sparklines
monthly_trend = conn.execute(f"""
    SELECT 
        MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS month,
        COUNT(*) AS flights,
        AVG("ARR_DELAY") AS delay,
        AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time,
        SUM("CANCELLED") AS cancelled,
        SUM("DIVERTED") AS diverted
    FROM flights {where_clause}
    GROUP BY month HAVING month IS NOT NULL ORDER BY month
""", params).df()

# 3. Build Sparkline Figures
fig_total = build_sparkline(monthly_trend, 'flights', '#0066CC')
fig_ontime = build_sparkline(monthly_trend, 'on_time', '#10B981')
fig_delay = build_sparkline(monthly_trend, 'delay', '#D00000')
fig_cancelled = build_sparkline(monthly_trend, 'cancelled', '#64748B')
fig_diverted = build_sparkline(monthly_trend, 'diverted', '#38BDF8')

# Helper function to render a single merged KPI Card
def render_kpi_card(title, value, value_color, fig):
    st.markdown(f"""
        <div class="kpi-card-unified">
            <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase;">{title}</div>
            <div style="font-size: 1.4rem; font-weight: 800; color: {value_color}; margin-top: 2px;">{value}</div>
        </div>
    """, unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="kpi-sparkline-container">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

# Render Unified KPI Row
c1, c2, c3, c4, c5 = st.columns(5)
with c1: render_kpi_card("TOTAL ARRIVALS", f"{int(tot_f or 0):,}", "#0A192F", fig_total)
with c2: render_kpi_card("ON-TIME % (≤15M)", f"{(on_t or 0):.1f}%", "#10B981", fig_ontime)
with c3: render_kpi_card("AVG DELAY", f"{(avg_d or 0):.1f}m", "#D00000", fig_delay)
with c4: render_kpi_card("CANCELLED", f"{int(tot_c or 0):,}", "#0A192F", fig_cancelled)
with c5: render_kpi_card("DIVERTED", f"{int(tot_div or 0):,}", "#0A192F", fig_diverted)

st.markdown("<br>", unsafe_allow_html=True)

# Bar Charts Container Section
col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    with st.container(border=True):
        st.write("**Select Metric for Charts Below:**")
        measure = st.segmented_control(
            "",
            ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"],
            default="Avg Delay (min)",
            label_visibility="collapsed"
        )

        measure_map = {
            "Flights Count": ("COUNT(*)", "DESC"),
            "On-Time %": ('AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100', "DESC"),
            "Cancellations": ('SUM("CANCELLED")', "DESC"),
            "Avg Delay (min)": ('AVG("ARR_DELAY")', "DESC")
        }
        sql_val, sql_ord = measure_map[measure]

        airlines_df = conn.execute(f"""
            SELECT "AIRLINE_CODE" AS code, {sql_val} AS val
            FROM flights {where_clause}
            GROUP BY code ORDER BY val {sql_ord} LIMIT 5
        """, params).df()

        fig_air = px.bar(airlines_df, y='code', x='val', orientation='h', title=f"Top 5 Airlines by {measure}")
        fig_air.update_traces(marker_color="#0066CC")
        fig_air.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure),
            margin=dict(l=10, r=10, t=35, b=10), height=210
        )
        st.plotly_chart(fig_air, use_container_width=True)

        origins_df = conn.execute(f"""
            SELECT "ORIGIN" AS code, {sql_val} AS val
            FROM flights {where_clause}
            GROUP BY code ORDER BY val {sql_ord} LIMIT 5
        """, params).df()

        fig_orig = px.bar(origins_df, y='code', x='val', orientation='h', title=f"Top 5 Origin Destinations by {measure}")
        fig_orig.update_traces(marker_color="#0066CC")
        fig_orig.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            yaxis=dict(autorange="reversed", title=""), xaxis=dict(title=measure),
            margin=dict(l=10, r=10, t=35, b=10), height=210
        )
        st.plotly_chart(fig_orig, use_container_width=True)

# Heatmap Section
with st.container(border=True):
    st.subheader("Arrival Volume Heatmap")
    heat_dim = st.segmented_control("Perspective:", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour")
    
    heat_df = conn.execute(f"""
        SELECT 
            MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS row_dim,
            CAST("CRS_ARR_TIME" / 100 AS INT) AS hour,
            COUNT(*) AS flights
        FROM flights {where_clause}
        GROUP BY row_dim, hour ORDER BY row_dim, hour
    """, params).df()
    
    month_names = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    heat_df['row_dim'] = heat_df['row_dim'].map(month_names)
    pivot_heat = heat_df.pivot(index='row_dim', columns='hour', values='flights').fillna(0)

    fig_heat = px.imshow(
        pivot_heat,
        labels=dict(x="Hour of Day (24h)", y="Month", color="Flights"),
        color_continuous_scale="Blues",
        title=None
    )
    fig_heat.update_traces(xgap=2, ygap=2)
    fig_heat.update_layout(
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=10, b=10), height=260
    )
    st.plotly_chart(fig_heat, use_container_width=True)
