from flask import Flask, request, jsonify
import numpy as np
import pickle
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import datetime
import xgboost as xgb
from dotenv import load_dotenv
import os

load_dotenv()
uri = os.getenv('MONGO_URI')
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['pregnacare_db']
collection = db['sensor_data']

model = pickle.load(open('xgb_model.pkl', 'rb'))
app = Flask(__name__)

latest_data = {}

# Upload Data
def upload_to_db(data):
    collection.insert_one(data)

def get_blood_glucose(spo2, heart_rate):
    # Credit: 
    """
    Bhashyam, Shubha & M G, Anuradha & N, Poornima & S, Suprada & V, Prathiksha. (2023). 
    An Implementation of blood Glucose and cholesterol monitoring device using non-invasive technique. 
    EMITTER International Journal of Engineering Technology. 76-88. 10.24003/emitter.v11i1.766. 
    """
    
    # Why not do your own regression -> the author doesn't provide the real dataset they use from invasive technique
    # However, they provide their regression constants that is fitted to their dataset
    # In the end, it is admitted that the conversion is not accurate because the subjects condition is not the same with our case which is pregnant mothers
    bs = 16714.61 + 0.47 * heart_rate - 351.045 * spo2 + 1.85 * spo2**2
    # The metrics is still in mg/dL we need to convert it to mmol/L
    return bs / 18

def convert_to_fahrenheit(celsius):
    # Original dataset is in fahrenheit while sensor data is in celsius
    return celsius * 9/5 + 32

@app.route('/upload', methods=['POST'])
def upload():
    latest_data = request.get_json(force=True)
    db_data = {
        "timestamp": datetime.datetime.now(),
        "bs": get_blood_glucose(latest_data['spo2'], latest_data['heart_rate']),
        "body_temperature": convert_to_fahrenheit(latest_data['body_temperature']),
        "heart_rate": latest_data['heart_rate'],
        "spo2": latest_data['spo2'],
    }
    upload_to_db(db_data)
    return jsonify({"status": "Data received"}), 200

# Get Data
def get_latest_5_minutes_data():
    curr_time = datetime.datetime.now()
    five_minutes_ago = curr_time - datetime.timedelta(minutes=5)
    collection.find({"timestamp": {"$gte": five_minutes_ago, "$lt": curr_time}})
    return list(collection.find({"timestamp": {"$gte": five_minutes_ago, "$lt": curr_time}}))

def average_data(data):
    if len(data) == 0:
        return None
    avg_data = {}
    for key in data[0]:
        if key == "_id" or key == "timestamp":
            continue
        avg_data[key] = sum([d[key] for d in data]) / len(data)
    return avg_data

@app.route('/get_avg_data', methods=['GET'])
def get_avg_data():
    return jsonify(average_data(get_latest_5_minutes_data()))

@app.route('/get_latest_data', methods=['GET'])
def get_latest_data():
    latest_data = collection.find_one(sort=[("timestamp", -1)])
    latest_data.pop("_id")
    return jsonify(latest_data)

@app.route('/get_all_data', methods=['GET'])
def get_all_data():
    data = list(collection.find())
    for d in data:
        d.pop("_id")
    return jsonify(data)

@app.route('/get_5_minutes_data', methods=['GET'])
def get_5_minutes_data():
    data = get_latest_5_minutes_data()
    for d in data:
        d.pop("_id")
    return jsonify(data)

# Predict
@app.route('/predict', methods=['POST'])
def predict():
    features = average_data(get_latest_5_minutes_data())
    # Handle if there is no data in the last 5 minutes
    if features is None:
        return jsonify({"error": "No data in the last 5 minutes"}), 404
    
    # Get age from user input
    age = request.get_json(force=True)['age']
    features['age'] = age
    print(features) 
    
    # Predict the risk level
    np_features = np.array([features['age'], features['bs'], features['body_temperature'], features['heart_rate']]).reshape(1, -1)
    prediction = model.predict(np_features)
    output = int(prediction[0])
    
    # Map the output to the risk level
    risk_levels = {0: 'Low Risk', 1: 'Medium Risk', 2: 'High Risk'}
    risk_output = risk_levels.get(output, "Unknown Risk Level")
    
    return jsonify({"risk_level": risk_output, "features": features}), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
