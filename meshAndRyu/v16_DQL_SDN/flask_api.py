from flask import Flask, request, jsonify
from dql_model import agent
import numpy as np

app = Flask(__name__)

@app.route('/get_action', methods=['POST'])
def get_action():
    data = request.json
    state = np.array([
        data['dpid'],
        int(data['src'].replace(':', ''), 16),
        int(data['dst'].replace(':', ''), 16),
        data['in_port']
    ]).reshape(1, -1)
    
    action = agent.act(state)
    return jsonify({'out_port': action})

@app.route('/update_model', methods=['POST'])
def update_model():
    data = request.json
    state = np.array(data['state']).reshape(1, -1)
    next_state = np.array(data['next_state']).reshape(1, -1)
    agent.remember(state, data['action'], data['reward'], next_state, data['done'])
    
    if len(agent.memory) > 32:
        agent.replay(32)
    
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)