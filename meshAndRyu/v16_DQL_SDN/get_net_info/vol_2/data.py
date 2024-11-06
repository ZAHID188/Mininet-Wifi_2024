# data_sender.py
import socketio
import time
import random
import json

sio = socketio.Client()

@sio.event
def connect():
    print('Connection established')

@sio.event
def disconnect():
    print('Disconnected from server')

@sio.event
def data_update(data):
    print('Received data update:', data)

def generate_data():
    return {
        "temperature": round(random.uniform(20, 30), 2),
        "humidity": round(random.uniform(40, 60), 2),
        "pressure": round(random.uniform(980, 1020), 2)
    }

def send_data():
    while True:
        data = generate_data()
        sio.emit('data', data)
        print(f"Sent: {data}")
        time.sleep(5)

if __name__ == '__main__':
    sio.connect('http://127.0.0.1:5000')
    send_data()