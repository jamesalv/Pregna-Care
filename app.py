import streamlit as st
import requests
import time
from dotenv import load_dotenv
import os
import plotly.graph_objects as go

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

# Maternal Risk Detection
def main(age):
    st.title('Maternal Risk Detection')
    st.write('This is a simple web application to detect the risk level of maternal health.')
    st.write(f'Age: {age}')

    while True:
        data = fetch_data()
        # Convert body temperature to Celsius and bs to mg/dL
        if data:
            data['body_temperature'] = (data['body_temperature'] - 32) * 5/9
            data['bs'] = data['bs'] * 18
        if data:
            st.plotly_chart(create_gauge('Body Temperature', data['body_temperature'], 35, 42, 37.5))
            st.plotly_chart(create_gauge('SpO2', data['spo2'], 70, 100, 90))
            st.plotly_chart(create_gauge('Heart Rate', data['heart_rate'], 40, 180, 100))
            st.plotly_chart(create_gauge('Blood Glucose', data['bs'], 50, 200, 150))
        
        time.sleep(5)
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
