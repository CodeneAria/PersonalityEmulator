from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory message store for testing
messages = [
    {"id": 1, "sender": "System", "text": "Welcome"},
    {"id": 2, "sender": "Tester", "text": "Initial message"},
]
next_id = 3


@app.route('/messages', methods=['GET'])
def get_messages():
    return jsonify(messages), 200


@app.route('/messages', methods=['POST'])
def post_message():
    global next_id
    data = request.get_json() or {}
    sender = data.get('sender', '')
    text = data.get('text', '')
    new_msg = {"id": next_id, "sender": sender, "text": text}
    messages.append(new_msg)
    next_id += 1
    return jsonify(new_msg), 201


if __name__ == '__main__':
    # Listen on localhost:50050 to match `test_sender.py`
    app.run(host='127.0.0.1', port=50050)
