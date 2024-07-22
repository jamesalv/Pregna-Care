import streamlit as st
import requests
import time
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
import pandas as pd
import numpy as np

load_dotenv()

# API URLs
predict_url = os.getenv('PREDICT_API') 
upload_url = os.getenv('UPLOAD_API')
get_data_url = os.getenv('GET_DATA_API')
chat_url = os.getenv('CHAT_API')

# Function to fetch the latest data
def fetch_data():
    response = requests.get(get_data_url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f'Error: Unable to fetch data {response}')
        return None

# Function to create a gauge chart with conditional coloring
def create_gauge(title, value, min_value, max_value, threshold):
    color = "green" if value < threshold else "red"
    
    fig = go.Figure(
        go.Indicator(
            domain={"x": [0, 1], "y": [0, 1]},
            value=value,
            mode="gauge+number",
            title={"text": title},
            gauge={
                "axis": {"range": [min_value, max_value]},
                "bar": {"color": color}
            },
        )
    )
    return fig

def display_data(data, label, metric, threshold=[0, 100]):
    # Display min, max, avg, and line chart for each data
    min_value = min(data)
    max_value = max(data)
    avg_value = np.mean(data)
    latest_value = data[-1]
    
    col1, col2 = st.columns([0.25, 0.75])
    with col1:
        create_gauge(label, latest_value, threshold[0], threshold[-1], avg_value).show()
        st.metric(label, value = f"{latest_value:.2f} {metric}", delta=f"{(latest_value - data[-2]):.2f} {metric}", delta_color="normal")    
    with col2:
        st.write("test")
    col1, col2, col3 = st.columns(3)
    col1.metric('Min', value=f"{min_value:.1f} {metric}")
    col2.metric('Max', value=f"{max_value:.1f} {metric}")
    col3.metric('Avg', value=f"{avg_value:.1f} {metric}")
        
    # st.line_chart(data)

# Maternal Risk Detection
def main(age):
    st.title('Maternal Risk Detection')
    st.write('This is a simple web application to detect the risk level of maternal health.')
    st.write(f'Age: {age}')

    while True:
        data = fetch_data()
        if len(data) == 0:
            st.write('No data available. Please check the sensor connection.')
        else:
            df = pd.DataFrame(data)
            display_data(list(df['body_temperature']), "Body Temperature", "°F")
            # display_data(list(df['spo2']), "SP02", "%")
            # display_data(list(df['heart_rate']), "Heart Rate", "bpm")
            # display_data(list(df['bs']), "Blood Sugar", "mg/dL")
            
        
        time.sleep(10)
        st.rerun()

if __name__ == '__main__':
    if 'age' not in st.session_state:
        st.session_state.age = None

    if st.session_state.age is None:
        st.title('Welcome to Maternal Risk Detection')
        st.write('Please enter your age to continue.')
        age = st.number_input('Age:', min_value=1, max_value=120, step=1)
        if st.button('Submit'):
            st.session_state.age = age
            st.rerun()  # Rerun to update the state and proceed to main app
    else:
        main(st.session_state.age)
