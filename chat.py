from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, disconnect
from flask_session import Session
import uuid

app = Flask(__name__)
app.secret_key = 'archovia_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Setup Flask-SocketIO
socketio = SocketIO(app, async_mode='threading', manage_session=False)

# Store active users and messages in memory
online_users = set()
chat_history = []

# Admin configuration
admin_usernames = {'khatem', 'khatem_archone', 'czar'}
muted_users = set()

# Allowed users
allowed_users = {
    'khatem',
    'khatem_archone',
    'czar',
    'spector',
    'lucian'
}

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if username and username.lower() in allowed_users:
            session['username'] = username
            session['uid'] = str(uuid.uuid4())
            session['is_admin'] = username.lower() in admin_usernames
            return redirect(url_for('chat'))
        return render_template('login.html', error="Access denied or invalid username")
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', username=session['username'], is_admin=session.get('is_admin', False))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- WebSocket Events ---

@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    if not username:
        return disconnect()

    online_users.add(username)
    emit('chat_history', chat_history)
    emit('user_list', list(online_users), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username in online_users:
        online_users.remove(username)
        emit('user_list', list(online_users), broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username', 'anon')
    message = data.get('message', '').strip()

    # Admin commands: kick and mute
    if session.get('is_admin'):
        if message.startswith('/kick '):
            target = message.split('/kick ', 1)[1].strip()
            if target in online_users:
                emit('force_disconnect', {'target': target}, broadcast=True)
            return
        if message.startswith('/mute '):
            target = message.split('/mute ', 1)[1].strip()
            muted_users.add(target)
            return

    # Ignore messages from muted users
    if username in muted_users:
        return

    if message:
        msg_obj = {
            'username': username,
            'message': message,
            'is_admin': session.get('is_admin', False)
        }
        chat_history.append(msg_obj)
        emit('new_message', msg_obj, broadcast=True)

# --- Main Entrypoint ---
if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5500, debug=True)
