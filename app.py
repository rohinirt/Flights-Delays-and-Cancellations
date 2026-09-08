import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Chicago O'Hare (ORD) Flight Intelligence",
    page_icon="✈️",
    layout="wide"
)

# Global CSS Adjustments
st.markdown("""
<style>
    /* Force Light Gray Canvas Background */
    .stApp {
        background-color: #F8FAFC !important;
    }
    
    /* Consolidated KPI Card Container */
    .kpi-card-unified {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
        padding: 12px 12px 0px 12px !important;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Clean Up Segmented Control Inside Card Containers */
    div[data-testid="stSegmentedControl"] {
        background-color: #F1F5F9 !important;
        padding: 4px !important;
        border-radius: 8px !important;
    }

    /* Style Streamlit Containers to act as Unified White Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper Function: Single KPI Card Component (HTML Number + Plotly Sparkline)
def render_unified_kpi_card(title, value, value_color, fig):
    st.markdown(f"""
        <div class="kpi-card-unified">
            <div style="font-size: 0.75rem; font-weight: 700; color: #475569; text-transform: uppercase;">{title}</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {value_color}; margin-top: 2px;">{value}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Render Sparkline flush inside the same visual card
    fig.update_layout(
        margin=dict(l=0, r=0, t=5, b=0),
        height=65,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False)
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==================== KPI ROW SECTION ====================
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    render_unified_kpi_card("TOTAL ARRIVALS", f"{26685:,}", "#0A192F", fig_total)

with c2:
    render_unified_kpi_card("ON-TIME % (≤15M)", "80.1%", "#10B981", fig_ontime)

with c3:
    render_unified_kpi_card("AVG DELAY", "4.8m", "#D00000", fig_delay)

with c4:
    render_unified_kpi_card("CANCELLED", "764", "#0A192F", fig_cancelled)

with c5:
    render_unified_kpi_card("DIVERTED", "67", "#0A192F", fig_diverted)


# ==================== BAR CHARTS & BUTTON SECTION ====================
col_left, col_right = st.columns([1, 1])

with col_left:
    # Wrapping controls & charts in a native bordered container visually unites them
    with st.container(border=True):
        st.write("**Select Metric for Charts Below:**")
        measure = st.segmented_control(
            "",
            ["Flights Count", "On-Time %", "Cancellations", "Avg Delay (min)"],
            default="Avg Delay (min)",
            label_visibility="collapsed"
        )

        # Top 5 Airlines Chart
        fig_air = px.bar(airlines_df, y='label', x='val', orientation='h', title=f"Top 5 Airlines by {measure}")
        fig_air.update_layout(
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            margin=dict(l=0, r=10, t=30, b=10),
            height=220
        )
        st.plotly_chart(fig_air, use_container_width=True)

        # Top 5 Origins Chart
        fig_orig = px.bar(origins_df, y='label', x='val', orientation='h', title=f"Top 5 Origin Destinations by {measure}")
        fig_orig.update_layout(
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            margin=dict(l=0, r=10, t=30, b=10),
            height=220
        )
        st.plotly_chart(fig_orig, use_container_width=True)


# ==================== HEATMAP SECTION ====================
with st.container(border=True):
    st.subheader("Arrival Volume Heatmap")
    heat_dim = st.segmented_control("Perspective:", ["Month vs. Hour", "Day of Week vs. Hour"], default="Month vs. Hour")
    
    fig_heat = px.imshow(
        pivot_heat,
        labels=dict(x="Hour of Day (24h)", y="Month", color="Flights"),
        color_continuous_scale="Blues",
        title=None  # Explicitly set to None to remove "undefined" text
    )
    fig_heat.update_traces(xgap=2, ygap=2)
    fig_heat.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=10, b=10),
        height=280
    )
    st.plotly_chart(fig_heat, use_container_width=True)
