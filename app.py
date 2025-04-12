from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import secrets
import SQL_manager

import Encryption_Manager
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
import uuid
# Mock database - replace with real database
users_db = {}
friends_db = {}
messages_db = {}


def get_onion_address():
     hostname_file = Path("tor_data").absolute() / "hidden_service" / "hostname"
     with open(hostname_file) as f:
         return str(f.read().strip())



@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html',onion_address = get_onion_address())


@app.route('/profile-setup', methods=['GET', 'POST'])
def profile_setup():
    if request.method == 'POST':
        username = request.form.get('username')
        profile_pic = request.form.get('profile_pic', '')
        bio = request.form.get('bio', '')

        userData = SQL_manager.execute_query("SELECT * FROM users WHERE username = %s",params=[username,], fetch=True)["results"]
        print(userData)
        if userData:
            userData = userData[0]
            key_data = SQL_manager.execute_query("SELECT * FROM onion_keys WHERE user_id = %s",params=[userData["user_id"]], fetch=True)["results"][0]
            session['username'] = username
            session['onion_address'] = key_data["onion_address"]
            session['public_key'] = key_data["public_key"]
            session['user_id'] = userData["user_id"]
            return redirect(url_for('dashboard'))



        onion_address = get_onion_address()
        random_uuid = str(uuid.uuid4())
        keys = Encryption_Manager.generate_key_pair()
        public_key = keys[1]

        private_key = keys[0]

        SQL_manager.execute_query("INSERT INTO users (user_id,username) VALUES (%s,%s)",params=(random_uuid,username,))
        SQL_manager.execute_query("INSERT INTO onion_keys (user_id,onion_address,public_key) VALUES (%s,%s,%s)" , params=(random_uuid,onion_address,public_key,))
        session['username'] = username
        session['onion_address'] = onion_address
        session['public_key'] = public_key
        session['private_key'] = private_key
        session['user_id'] = random_uuid

        return redirect(url_for('dashboard'))

    return render_template('profile_setup.html')




@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('profile_setup'))

    user_id = session['user_id']

    friends = SQL_manager.execute_query(
        """
        SELECT u.username 
        FROM (
            SELECT friend_id as id FROM Friend WHERE user_id = %s
            UNION
            SELECT user_id as id FROM Friend WHERE friend_id = %s
        ) combined
        JOIN users u ON combined.id = u.user_id
        """,
        params=(user_id, user_id),
        fetch=True
    )["results"]

    friend_requests = SQL_manager.execute_query(
    """
    SELECT u.username ,created_at
    FROM FriendRequest fr
    JOIN users u ON fr.sender_id = u.user_id
    WHERE fr.recipient_id = %s AND fr.status = 'pending'
    """,
    params=(user_id,),
    fetch=True
    )["results"]

    print(friend_requests)
    print(friends)
    return render_template('dashboard.html',
                           username=session['username'],
                           onion_address=session.get('onion_address', ''),
                           friends=friends,
                           friend_requests=friend_requests)


@app.route('/handle-friend-request', methods=['POST'])
def handle_friend_request():
    if 'user_id' not in session:
        return redirect(url_for('dashboard'))

    request_username = request.form.get('request_username')
    action = request.form.get('action')
    if action == 'accept':
        # Accept the friend request
        SQL_manager.execute_query(
            "CALL AcceptFriendRequest(%s, %s)",
            params=(session["user_id"], request_username),
            fetch=False
        )
        pass

    elif action == 'reject':
        SQL_manager.execute_query(
            "CALL RejectFriendRequest(%s, %s)",
            params=(session["user_id"], request_username),
            fetch=False
        )


    return redirect(url_for('dashboard'))


@app.route('/add-friend', methods=['GET', 'POST'])
def add_friend():
    if 'username' not in session:
        return redirect(url_for('index'))
    possible_users = []
    if request.method == 'POST':
        friend_username = request.form.get('username')
        friend_user_data = SQL_manager.execute_query("SELECT * FROM users WHERE username = %s", params=(friend_username,),fetch=True)["results"][0]
        print(friend_user_data)
        SQL_manager.execute_query('INSERT INTO FriendRequest (request_id, sender_id, recipient_id) VALUES (%s,%s,%s)',params=(str(uuid.uuid4()),session["user_id"],friend_user_data["user_id"]))
        return redirect(url_for('dashboard'))
    else:
        possible_users = SQL_manager.execute_query("SELECT username FROM users" , fetch=True)["results"]

    usernames = [user['username'] for user in possible_users]
    return render_template('add_friend.html', users=usernames)


@app.route('/chat/<friend>')
def chat(friend):
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']
    chat_id = f"{username}_{friend}" if username < friend else f"{friend}_{username}"

    messages = messages_db.get(chat_id, [])

    return render_template('chat.html',
                           friend=friend,
                           messages=messages)


@app.route('/api/send-message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    data = request.json
    friend = data.get('friend')
    message = data.get('message')

    if not friend or not message:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    username = session['username']
    chat_id = f"{username}_{friend}" if username < friend else f"{friend}_{username}"

    if chat_id not in messages_db:
        messages_db[chat_id] = []

    messages_db[chat_id].append({
        'sender': username,
        'message': message,
        'timestamp': datetime.datetime.now().isoformat()
    })

    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(port=8000, debug=True)