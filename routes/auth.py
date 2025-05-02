import base64
import uuid

from flask import Blueprint

from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session, redirect, url_for,flash
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

            with open(f"Data/Keys/" + session["username"] + "/" + "sym_key.pem", 'r') as f:
                session['sym_key'] = f.readline().strip()
            print(session['sym_key'])
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


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']


        output = SQL_manager.execute_query("SELECT p.salt,o.public_key FROM password p,users u,onion_keys o WHERE  u.username = %s AND u.user_id = p.user_id AND o.user_id = u.user_id", params=[username], fetch=True)["results"]
        print(output)
        if not output:
            return redirect(url_for('auth.login'))

        salt,pub_key = output[0]["salt"], output[0]["public_key"]

        sym_key = Encryption_Manager.hash_password(password, salt.encode())


        with open(f"Data/Keys/" + username + "/" + "priv_key.pem", 'r') as f:
            enc_key = f.readline().strip()
            try:
                Encryption_Manager.decrypt_message_with_symmetric_key(sym_key, enc_key)
            except:
                flash("Username or password incorrect")
                return redirect(url_for('auth.login'))

        userData = \
        SQL_manager.execute_query("SELECT * FROM users WHERE username = %s", params=[username, ], fetch=True)["results"]
        if userData:
            userData = userData[0]
            key_data = \
            SQL_manager.execute_query("SELECT * FROM onion_keys WHERE user_id = %s", params=[userData["user_id"]],
                                      fetch=True)["results"][0]
            session['username'] = username
            session['onion_address'] = key_data["onion_address"]
            session['public_key'] = key_data["public_key"]
            session['user_id'] = userData["user_id"]
            return redirect(url_for('auth.dashboard'))

    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('auth.signup'))


        is_name_taken= SQL_manager.execute_query("SELECT 1 FROM users WHERE username = %s LIMIT 1", params = (username,),fetch=True)['results']

        if is_name_taken:
            flash('Username is already taken!', 'error')
            return redirect(url_for('auth.signup'))

        onion_address = get_onion_address()
        random_uuid = str(uuid.uuid4())
        keys = Encryption_Manager.generate_rsa_key_pair()

        sym_key,salt = Encryption_Manager.create_key_from_password(password)


        session['username'] = username
        session['onion_address'] = onion_address
        session['user_id'] = random_uuid

        os.makedirs("Data/Keys/" + session["username"], exist_ok=True)

        str_prv, str_pub = Encryption_Manager.keys_to_strings(keys[0], keys[1])
        with open("Data/Keys/" + session["username"] + "/" + "priv_key.pem", 'wb') as f:
            key =  Encryption_Manager.encrypt_message_with_symmetric_key(sym_key, str_prv)
            f.write(key.encode())

        symmetric_key = Encryption_Manager.create_symmetric_key()
        with open(f"Data/Keys/" + session["username"] + "/" + "sym_key.pem", 'wb') as f:
            f.write(symmetric_key.encode())


        session['public_key'] = str_pub
        session['sym_key'] = symmetric_key

        SQL_manager.get_connection().cursor().callproc('register_user', (
            random_uuid, username,
            onion_address, str_pub,
            salt
        ))
        print("key added")
        return redirect(url_for('auth.dashboard'))


    return render_template('signup.html')