import streamlit as st
import duckdb
import plotly.express as px

conn = duckdb.connect(database=':memory:')

st.title("🛫 ORD Departures Intelligence")
st.caption("Outbound Operational Insights")

kpi_df = conn.execute("""
    SELECT COUNT(*) AS total_flights,
        AVG(CASE WHEN "DEP_DELAY" <= 15 THEN 1 ELSE 0 END) * 100 AS on_time_pct,
        AVG("DEP_DELAY") AS avg_delay, SUM("CANCELLED") AS total_cancelled
    FROM flights WHERE UPPER("ORIGIN") = 'ORD'
""").df()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Departures", f"{int(kpi_df.iloc[0]['total_flights']):,}")
c2.metric("On-Time Rate", f"{kpi_df.iloc[0]['on_time_pct']:.1f}%")
c3.metric("Avg Delay", f"{kpi_df.iloc[0]['avg_delay']:.1f} mins")
c4.metric("Cancellations", f"{int(kpi_df.iloc[0]['total_cancelled']):,}")

st.markdown("---")
st.subheader("Top Destination Hubs")
dests = conn.execute("""
    SELECT "DEST", COUNT(*) AS flights, AVG("DEP_DELAY") AS avg_delay
    FROM flights WHERE UPPER("ORIGIN") = 'ORD' 
    GROUP BY "DEST" ORDER BY flights DESC LIMIT 10
""").df()

fig = px.scatter(dests, x='flights', y='avg_delay', size='flights', text='DEST', color='avg_delay', color_continuous_scale='Reds')
fig.update_layout(template="plotly_white", xaxis_title="Total Flights", yaxis_title="Average Delay (mins)")
st.plotly_chart(fig, width="stretch")
