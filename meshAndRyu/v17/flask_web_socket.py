from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import eventlet

# Patch standard library for compatibility with Eventlet
eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')  # Ensure this file exists in the templates folder

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def send_topology_update(data):
    """Emit the data to the web client."""
    socketio.emit('topology_update', data)

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000)