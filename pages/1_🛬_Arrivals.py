import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

conn = duckdb.connect(database=':memory:')

st.title("🛬 ORD Arrivals Intelligence")
st.caption("Inbound Flight Analytics & Delay Breakdown")

kpi_df = conn.execute("""
    SELECT COUNT(*) AS total_flights,
        AVG(CASE WHEN "ARR_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
        AVG("ARR_DELAY") AS avg_delay, SUM("CANCELLED") AS total_cancelled
    FROM flights WHERE UPPER("DEST") = 'ORD'
""").df()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Arrivals", f"{int(kpi_df.iloc[0]['total_flights']):,}")
c2.metric("On-Time Rate", f"{kpi_df.iloc[0]['on_time_pct']:.1f}%")
c3.metric("Avg Delay", f"{kpi_df.iloc[0]['avg_delay']:.1f} mins")
c4.metric("Cancellations", f"{int(kpi_df.iloc[0]['total_cancelled']):,}")

st.markdown("---")
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("Top Inbound Origins")
    origins = conn.execute("""
        SELECT "ORIGIN", COUNT(*) AS flights 
        FROM flights WHERE UPPER("DEST") = 'ORD' 
        GROUP BY "ORIGIN" ORDER BY flights DESC LIMIT 10
    """).df()
    fig = px.bar(origins, x='flights', y='ORIGIN', orientation='h', color_discrete_sequence=['#0066CC'])
    fig.update_layout(template="plotly_white", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch")

with c_right:
    st.subheader("Arrival Delay Causes")
    delays = conn.execute("""
        SELECT AVG("DELAY_DUE_CARRIER") AS Carrier, AVG("DELAY_DUE_WEATHER") AS Weather,
               AVG("DELAY_DUE_NAS") AS NAS, AVG("DELAY_DUE_SECURITY") AS Security,
               AVG("DELAY_DUE_LATE_AIRCRAFT") AS "Late Aircraft"
        FROM flights WHERE UPPER("DEST") = 'ORD'
    """).df().T.reset_index()
    delays.columns = ['Cause', 'Avg Minutes']
    fig_delay = px.bar(delays, x='Cause', y='Avg Minutes', color_discrete_sequence=['#D00000'])
    fig_delay.update_layout(template="plotly_white")
    st.plotly_chart(fig_delay, width="stretch")
