import streamlit as st
import duckdb
import plotly.express as px

conn = duckdb.connect(database=':memory:')

st.title("🔍 Route & Carrier Deep-Dive Analytics")
st.caption("Custom Head-to-Head Comparisons & Time Dynamics")

# Dynamic Route Selector
routes = conn.execute("""
    SELECT DISTINCT "ORIGIN" || ' ➔ ' || "DEST" AS route 
    FROM flights 
    WHERE "ORIGIN" = 'ORD' OR "DEST" = 'ORD'
    ORDER BY route
""").df()['route'].tolist()

if not routes:
    st.info("No route data found.")
    st.stop()

selected_route = st.selectbox("Select Route Segment", options=routes)
orig, dest = selected_route.split(' ➔ ')

st.markdown("---")

# 1. Optimal Time Window
st.subheader(f"⏰ Optimal Departure Hour for {selected_route}")
hourly = conn.execute("""
    SELECT CAST(COALESCE("CRS_DEP_TIME", 1200) / 100 AS INT) AS dep_hour,
           AVG("DEP_DELAY") AS avg_delay,
           COUNT(*) AS total_flights
    FROM flights
    WHERE "ORIGIN" = ? AND "DEST" = ?
    GROUP BY dep_hour ORDER BY dep_hour
""", [orig, dest]).df()

if not hourly.empty:
    fig_hourly = px.bar(hourly, x='dep_hour', y='avg_delay', color='avg_delay',
                        color_continuous_scale='RdYlGn_r',
                        labels={'dep_hour': 'Hour of Day (24h)', 'avg_delay': 'Avg Delay (mins)'})
    fig_hourly.update_layout(template="plotly_white")
    st.plotly_chart(fig_hourly, width="stretch")

# 2. Carrier Comparison
st.subheader(f"✈️ Airline Performance Comparison on {selected_route}")
carrier = conn.execute("""
    SELECT COALESCE("AIRLINE_CODE", "AIRLINE") AS carrier,
           COUNT(*) AS total_flights,
           AVG("DEP_DELAY") AS avg_dep_delay,
           AVG("ARR_DELAY") AS avg_arr_delay,
           AVG(CASE WHEN "DEP_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_rate
    FROM flights
    WHERE "ORIGIN" = ? AND "DEST" = ?
    GROUP BY carrier ORDER BY total_flights DESC
""", [orig, dest]).df()

if not carrier.empty:
    st.dataframe(carrier, width="stretch")
