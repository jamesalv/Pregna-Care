import os
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()
app = Flask(__name__)
genai.configure(api_key=os.getenv("API_KEY"))

model = genai.GenerativeModel("gemini-pro")
initial_prompt = """
    You are a chatbot for maternal pregnancy support application named 'PregnaCare'. Your task is to help mother to get suggestion to maintain and improve their own health and also the fetal health. 
    You also provide consultation service so the mothers can ask anything related about pregnancy care and give them solution for their problems. Your personality is friendly, informative, and supportive.
    
    If the user question does not relate with the pregnancy care, you just answer that it is not related to your function and ask them to contact other department or services.
    Here is the first question from the user:
    """
conversation_history = [{"role": "user", "content": initial_prompt}]
chat = model.start_chat(history=[])
res = chat.send_message(initial_prompt)
conversation_history.append({"role": "model", "content": res.text})

@app.route("/chat", methods=["POST"])
def generate_response():
    prompt = request.get_json(force=True)["prompt"]
    response = chat.send_message(prompt)
    conversation_history.append({"role": "user", "content": prompt})
    conversation_history.append({"role": "model", "content": response.text})
    return jsonify({"response": response.text})


@app.route("/chat", methods=["GET"])
def get_conversation_history():
    return jsonify(conversation_history)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
