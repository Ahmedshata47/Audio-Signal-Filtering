import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time

st.set_page_config(page_title="Sensor Mission Control", layout="wide")

st.markdown("""
    <style>
    .title {
        font-size: 3em;
        font-weight: bold;
        color: #FF6F00;
        text-align: center;
        margin-top: 20px;
        margin-bottom: 10px;
        text-shadow: 1px 1px 2px #000000;
    }
    .subtitle {
        text-align: center;
        font-size: 1.5em;
        color: #ffffffaa;
        margin-bottom: 30px;
    }
    .launch-button-container {
        display: flex;
        justify-content: center;
        margin-bottom: 40px;
    }
    .launch-button > button {
        font-size: 2.5em;
        padding: 1em 3em;
        background-color: #00b894;
        border: none;
        border-radius: 15px;
        color: white;
        transition: 0.3s ease-in-out;
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        cursor: pointer;
    }
    .launch-button > button:hover {
        background-color: #019875;
        transform: scale(1.05);
    }
    </style>

    <div class='title'>🛰️ SENSOR MISSION CONTROL</div>
    <div class='subtitle'>Real-time Insight Console</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("📤 Upload your sensor data CSV file", type="csv")

if "launched" not in st.session_state:
    st.session_state.launched = False
if uploaded_file and not st.session_state.launched:
    st.markdown("<div class='launch-button-container'>", unsafe_allow_html=True)
    if st.button("🚀 Launch Data Visualizer", key="launch", use_container_width=False):
        st.session_state.launched = True
        with st.spinner("Initializing sensors..."):
            time.sleep(1.5)
        with st.spinner("Analyzing atmospheric data..."):
            time.sleep(1.5)
        with st.spinner("Loading visuals..."):
            time.sleep(1.5)
    st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file and st.session_state.launched:
    df = pd.read_csv(uploaded_file)

    st.subheader("📊 Data Preview")
    st.dataframe(df[["Time(s)", "MQ2(ppm)", "MQ7(ppm)", "Temperature(°C)", "Humidity(%)", "Fire_Alert"]])

    st.subheader("📈 Sensor Readings Over Time")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**MQ2 and MQ7 (Gas Sensors)**")
        st.line_chart(df.set_index('Timestamp(ms)')[['MQ2(ppm)', 'MQ7(ppm)']])

    with col2:
        st.write("**Temperature and Humidity**")
        st.line_chart(df.set_index('Timestamp(ms)')[['Temperature(°C)', 'Humidity(%)']])

    st.subheader("🚨 Fire Alerts Over Time")
    alert_times = df[df['Fire_Alert'] == 1]['Time(s)']
    fig, ax = plt.subplots(figsize=(10, 2))
    ax.eventplot(alert_times, colors='red')
    ax.set_title("Fire Alerts Over Time")
    ax.set_xlabel("Time(s)")
    st.pyplot(fig)

elif not uploaded_file:
    st.info("📤 Please upload your sensor data CSV file.")
