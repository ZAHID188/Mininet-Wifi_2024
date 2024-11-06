# flask_server.py
from flask import Flask, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)

latest_data = {}

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('data')
def handle_data(data):
    global latest_data
    latest_data = data
    print(f"Received data: {latest_data}")
    emit('data_update', latest_data, broadcast=True)

@app.route('/get_latest_data', methods=['GET'])
def get_latest_data():
    return jsonify(latest_data)

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)