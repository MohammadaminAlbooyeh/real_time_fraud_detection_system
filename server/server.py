from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

game_rooms = {}

@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.json
    room_id = data.get('room_id')
    if room_id in game_rooms:
        return jsonify({'error': 'Room already exists'}), 400
    game_rooms[room_id] = {'players': [], 'chat': []}
    return jsonify({'message': 'Room created successfully'})

@app.route('/join_room', methods=['POST'])
def join_room_endpoint():
    data = request.json
    room_id = data.get('room_id')
    player_name = data.get('player_name')
    if room_id not in game_rooms:
        return jsonify({'error': 'Room does not exist'}), 404
    game_rooms[room_id]['players'].append(player_name)
    return jsonify({'message': f'{player_name} joined the room'})

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('message', {'msg': f"{data['username']} has joined the room."}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('message', {'msg': f"{data['username']} has left the room."}, room=room)

@socketio.on('chat')
def handle_chat(data):
    room = data['room']
    message = {'username': data['username'], 'msg': data['msg']}
    game_rooms[room]['chat'].append(message)
    emit('chat', message, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)