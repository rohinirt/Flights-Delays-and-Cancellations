import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd

# 1. Page Configuration
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Flight Intelligence",
    page_icon="✈️",
    layout="wide"
)

# 2. CSS Rules for Card Styling & Unified Containers
st.markdown("""
<style>
    /* Force Light Gray Canvas Background */
    .stApp {
        background-color: #F8FAFC !important;
    }
    
    /* Consolidated Single-Box KPI Card Outer Style */
    .kpi-card-unified {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px 12px 0 0 !important;
        padding: 12px 12px 0px 12px !important;
        text-align: center;
    }

    /* Target Streamlit Bordered Containers to act as Seamless White Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 16px !important;
    }
    
    /* Clean Up Segmented Controls */
    div[data-testid="stSegmentedControl"] {
        background-color: #F1F5F9 !important;
        padding: 4px !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. Database Connection & Sample Data Setup
@st.cache_resource
def get_db_connection():
    conn = duckdb.connect(database=':memory:')
    # Generate mock 2022 monthly flight data for demonstration
    conn.execute("""
        CREATE TABLE flights AS 
        SELECT 
            range % 12 + 1 AS month,
            'AA' AS AIRLINE_CODE,
            'ORD' AS DEST,
            'LAX' AS ORIGIN,
            20 + (range % 5) AS ARR_DELAY,
            CASE WHEN range % 10 = 0 THEN 1 ELSE 0 END AS CANCELLED,
            CASE WHEN range % 20 = 0 THEN 1 ELSE 0 END AS DIVERTED
        FROM range(1000)
    """)
    return conn

conn = get_db_connection()

# 4. Helper Function: Sparkline Generator
def create_sparkline(df, y_col, bar_color):
    month_map = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
                 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    data = df.copy()
    data['month_code'] = data['month'].map(month_map)

    fig = px.bar(data, x='month_code', y=y_col)
    fig.update_traces(marker_color=bar_color, hovertemplate="%{x}: %{y:,.1f}<extra></extra>")
    fig.update_layout(
        margin=dict(l=2, r=2, t=2, b=15),
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

# Helper Function: Render Single Box KPI
def render_kpi(column, title, value, value_color, fig):
    with column:
        st.markdown(f"""
            <div class="kpi-card-unified">
                <div style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase;">{title}</div>
                <div style="font-size: 1.4rem; font-weight: 800; color: {value_color}; margin-top: 2px;">{value}</div>
            </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# ==================== DATA QUERIES ====================
kpi_df = conn.execute("""
    SELECT 
        COUNT(*) AS total_flights,
        AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
        AVG("ARR_DELAY") AS avg_delay,
        SUM("CANCELLED") AS total_cancelled,
        SUM("DIVERTED") AS total_diverted
    FROM flights
""").df()

monthly_trend = conn.execute("""
    SELECT 
        month,
        COUNT(*) AS flights,
        AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time,
        AVG("ARR_DELAY") AS delay,
        SUM("CANCELLED") AS cancelled,
        SUM("DIVERTED") AS diverted
    FROM flights
    GROUP BY month ORDER BY month
""").df()

total_flights, on_time_pct, avg_delay, total_cancelled, total_diverted = kpi_df.iloc[0]


# ==================== 1. UNIFIED KPI CARDS ROW ====================
c1, c2, c3, c4, c5 = st.columns(5)

fig_total = create_sparkline(monthly_trend, 'flights', '#0066CC')
fig_ontime = create_sparkline(monthly_trend, 'on_time', '#10B981')
fig_delay = create_sparkline(monthly_trend, 'delay', '#D00000')
fig_cancelled = create_sparkline(monthly_trend, 'cancelled', '#64748B')
fig_diverted = create_sparkline(monthly_trend, 'diverted', '#38BDF8')

render_kpi(c1, "TOTAL ARRIVALS", f"{int(total_flights):,}", "#0A192F", fig_total)
render_kpi(c2, "ON-TIME % (≤15M)", f"{on_time_pct:.1f}%", "#10B981", fig_ontime)
render_kpi(c3, "AVG DELAY", f"{avg_delay:.1f}m", "#D00000", fig_delay)
render_kpi(c4, "CANCELLED", f"{int(total_cancelled):,}", "#0A192F", fig_cancelled)
render_kpi(c5, "DIVERTED", f"{int(total_diverted):,}", "#0A192F", fig_diverted)


# ==================== 2. BAR CHARTS IN SINGLE CONTAINER ====================
st.markdown("<br>", unsafe_allow_html=True)
col_left, col_right = st.columns([1, 1])

with col_left:
    # Single container encapsulates buttons and both charts into one white card
    with st.container(border=True):
        st.write("**Select Metric for Charts Below:**")
        measure = st.segmented_control(
            "Select Metric",
            ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"],
            default="Avg Delay (min)",
            label_visibility="collapsed"
        )

        mock_bar_data = pd.DataFrame({
            'label': ['F9 (Frontier)', 'B6 (JetBlue)', 'NK (Spirit)', 'WN (Southwest)', 'AA (American)'],
            'val': [27, 20, 12, 11, 9]
        })

        fig_air = px.bar(mock_bar_data, y='label', x='val', orientation='h', title=f"Top 5 Airlines by {measure}")
        fig_air.update_traces(marker_color="#0066CC")
        fig_air.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            margin=dict(l=0, r=10, t=30, b=10), height=200,
            yaxis=dict(autorange="reversed", title="")
        )
        st.plotly_chart(fig_air, use_container_width=True)

        fig_orig = px.bar(mock_bar_data, y='label', x='val', orientation='h', title=f"Top 5 Origin Destinations by {measure}")
        fig_orig.update_traces(marker_color="#0066CC")
        fig_orig.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            margin=dict(l=0, r=10, t=30, b=10), height=200,
            yaxis=dict(autorange="reversed", title="")
        )
        st.plotly_chart(fig_orig, use_container_width=True)


# ==================== 3. HEATMAP IN SINGLE CONTAINER ====================
with col_right:
    with st.container(border=True):
        st.subheader("Arrival Volume Heatmap")
        st.segmented_control("Perspective:", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour")

        # Sample matrix data
        mock_heatmap = pd.DataFrame(
            [[10, 20, 30], [20, 40, 60], [15, 25, 35]],
            index=['Jan', 'Feb', 'Mar'],
            columns=[8, 12, 16]
        )

        fig_heat = px.imshow(
            mock_heatmap,
            labels=dict(x="Hour of Day (24h)", y="Month", color="Flights"),
            color_continuous_scale="Blues",
            title=None  # Explicitly None to prevent "undefined" title text
        )
        fig_heat.update_traces(xgap=2, ygap=2)
        fig_heat.update_layout(
            paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
            margin=dict(l=10, r=10, t=10, b=10), height=380
        )
        st.plotly_chart(fig_heat, use_container_width=True)
