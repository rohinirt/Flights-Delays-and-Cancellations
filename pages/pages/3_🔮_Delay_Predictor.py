import streamlit as st
import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder

conn = duckdb.connect(database=':memory:')

st.title("🔮 Enhanced Delay Risk Predictor")
st.caption("Predicting probability, delay severity tier, and root cause indicators.")

@st.cache_resource
def train_models():
    try:
        df = conn.execute("""
            SELECT 
                COALESCE("AIRLINE_CODE", "AIRLINE") AS AIRLINE, 
                "ORIGIN", "DEST",
                MONTH(TRY_CAST(CAST("FL_DATE" AS VARCHAR) AS DATE)) AS month,
                CAST(COALESCE("CRS_DEP_TIME", 1200) / 100 AS INT) AS dep_hour,
                COALESCE("DISTANCE", 500) AS DISTANCE,
                "DEP_DELAY"
            FROM flights 
            WHERE "DEP_DELAY" IS NOT NULL
            LIMIT 50000
        """).df().dropna()

        # Target 1: Delay Binary Classifier
        df['is_delayed'] = (df['DEP_DELAY'] > 15).astype(int)

        # Target 2: Delay Severity Tiers
        # 0: On-Time (<15m), 1: Moderate (15-45m), 2: Severe (>45m)
        def get_tier(val):
            if val <= 15: return 0
            elif val <= 45: return 1
            else: return 2
        df['severity_tier'] = df['DEP_DELAY'].apply(get_tier)

        X = df[['AIRLINE', 'ORIGIN', 'DEST', 'month', 'dep_hour', 'DISTANCE']]
        
        encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        cat_encoded = encoder.fit_transform(X[['AIRLINE', 'ORIGIN', 'DEST']])
        num_features = X[['month', 'dep_hour', 'DISTANCE']].values
        X_final = np.hstack((cat_encoded, num_features))

        # Binary Model
        clf_binary = RandomForestClassifier(n_estimators=30, max_depth=8, random_state=42)
        clf_binary.fit(X_final, df['is_delayed'])

        # Multi-class Severity Model
        clf_severity = RandomForestClassifier(n_estimators=30, max_depth=8, random_state=42)
        clf_severity.fit(X_final, df['severity_tier'])

        airlines = sorted(df['AIRLINE'].astype(str).unique().tolist())
        origins = sorted(df['ORIGIN'].astype(str).unique().tolist())
        dests = sorted(df['DEST'].astype(str).unique().tolist())

        return clf_binary, clf_severity, encoder, airlines, origins, dests
    except Exception:
        return None, None, None, [], [], []

clf_binary, clf_severity, encoder, airlines, origins, dests = train_models()

if not clf_binary:
    st.warning("Insufficient data available to train prediction models.")
else:
    with st.container(border=True):
        p1, p2, p3 = st.columns(3)
        with p1:
            input_airline = st.selectbox("Airline", options=airlines)
            input_month = st.slider("Month", 1, 12, 6)
        with p2:
            input_origin = st.selectbox("Origin", options=origins, index=origins.index('ORD') if 'ORD' in origins else 0)
            input_hour = st.slider("Departure Hour (24h)", 0, 23, 14)
        with p3:
            input_dest = st.selectbox("Destination", options=dests, index=dests.index('LAX') if 'LAX' in dests else 0)
            input_dist = st.number_input("Distance (miles)", 100, 5000, 800)

        predict_btn = st.button("Run Prediction Analysis", type="primary", width="stretch")

    if predict_btn:
        cat_input = pd.DataFrame([[str(input_airline), str(input_origin), str(input_dest)]], columns=['AIRLINE', 'ORIGIN', 'DEST'])
        cat_encoded = encoder.transform(cat_input)
        num_features = np.array([[int(input_month), int(input_hour), float(input_dist)]])
        full_input = np.hstack((cat_encoded, num_features))

        prob_delay = clf_binary.predict_proba(full_input)[0][1] * 100
        severity_probs = clf_severity.predict_proba(full_input)[0]

        st.markdown("---")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.subheader("Delay Probability")
            st.metric("Overall Risk Probability", f"{prob_delay:.1f}%")
            st.progress(int(prob_delay))

        with c2:
            st.subheader("Severity Breakdown")
            st.write(f"• **On-Time / Minor:** {severity_probs[0]*100:.1f}%")
            st.write(f"• **Moderate (15–45m):** {severity_probs[1]*100:.1f}%")
            st.write(f"• **Severe (>45m):** {severity_probs[2]*100:.1f}%")

        with c3:
            st.subheader("Risk Rating")
            if prob_delay >= 40:
                st.error("⚠️ HIGH DELAY RISK")
            elif prob_delay >= 20:
                st.warning("⚡ MODERATE DELAY RISK")
            else:
                st.success("✅ LOW DELAY RISK")
