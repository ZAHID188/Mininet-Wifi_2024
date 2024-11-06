# flask_api.py
from flask import Flask, jsonify
from simple_websocket_server import WebSocketServer, WebSocket
import threading
import json

app = Flask(__name__)
network_info = {}

class SimpleWebSocket(WebSocket):
    def handle(self):
        global network_info
        try:
            data = json.loads(self.data)
            network_info = data
            print(f"Received network info: {network_info}")
            self.send_message(json.dumps({"status": "received"}))
        except json.JSONDecodeError:
            print(f"Received invalid JSON: {self.data}")

    def connected(self):
        print(self.address, 'connected')

    def handle_close(self):
        print(self.address, 'closed')

@app.route('/get_network_info', methods=['GET'])
def get_network_info():
    return jsonify(network_info)

def run_websocket_server():
    server = WebSocketServer('127.0.0.1', 8000, SimpleWebSocket)
    server.serve_forever()

if __name__ == '__main__':
    websocket_thread = threading.Thread(target=run_websocket_server)
    websocket_thread.daemon = True
    websocket_thread.start()
    app.run(host='127.0.0.1', port=5000, debug=True)