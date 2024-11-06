# flask_api.py
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

network_info = {}

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(message):
    global network_info
    network_info = message
    print(f"Received network info: {network_info}")
    emit('network_update', network_info, broadcast=True)

@app.route('/get_network_info', methods=['GET'])
def get_network_info():
    return jsonify(network_info)

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)