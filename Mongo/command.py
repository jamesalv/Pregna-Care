from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
    
uri = "mongodb+srv://jamesdhanardi:QfXaJU7vuBX7GA1o@pregnacare.6axog6l.mongodb.net/?retryWrites=true&w=majority&appName=PregnaCare"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['pregnacare_db']
collection = db['sensor_data']

# Delete all data
collection.delete_many({})