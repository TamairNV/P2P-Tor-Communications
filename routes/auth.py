import uuid

from flask import Blueprint

from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import secrets

import Encryption_Manager
import SQL_manager

from tor import get_onion_address
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/profile-setup', methods=['GET', 'POST'])
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
            return redirect(url_for('auth.dashboard'))



        onion_address = get_onion_address()
        random_uuid = str(uuid.uuid4())
        keys = Encryption_Manager.generate_rsa_key_pair()



        session['username'] = username
        session['onion_address'] = onion_address
        session['user_id'] = random_uuid

        os.makedirs("Data/Keys/" + session["username"], exist_ok=True)

        str_prv, str_pub = Encryption_Manager.keys_to_strings(keys[0], keys[1])
        with open("Data/Keys/" + session["username"] + "/" + "priv_key.pem", 'wb') as f:
            f.write(str_prv.encode())

        session['public_key'] = str_pub


        SQL_manager.execute_query("INSERT INTO users (user_id,username) VALUES (%s,%s)",params=(random_uuid,username,))

        SQL_manager.execute_query("INSERT INTO onion_keys (user_id,onion_address,public_key) VALUES (%s,%s,%s)",
                                  params=(random_uuid, onion_address, str_pub,))
        print("key added")
        return redirect(url_for('auth.dashboard'))

    return render_template('profile_setup.html')


@auth_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.profile_setup'))
    SQL_manager.execute_query("UPDATE users SET is_online = TRUE WHERE user_id = %s", (session['user_id'],))

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

