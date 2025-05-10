
import uuid

from flask import Blueprint

from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import secrets

import Encryption_Manager
import SQL_manager
from utils.tor import get_onion_address
friend_bp = Blueprint('friend', __name__)




@friend_bp.route('/handle-friend-request', methods=['POST'])
def handle_friend_request():
    if 'user_id' not in session:
        return redirect(url_for('auth.dashboard'))

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


    return redirect(url_for('auth.dashboard'))


@friend_bp.route('/add-friend', methods=['GET', 'POST'])
def add_friend():
    if 'username' not in session:
        return redirect(url_for('index'))
    possible_users = []
    if request.method == 'POST':
        friend_username = request.form.get('username')
        friend_user_data = SQL_manager.execute_query("SELECT * FROM users WHERE username = %s", params=(friend_username,),fetch=True)["results"][0]
        SQL_manager.execute_query('INSERT INTO FriendRequest (request_id, sender_id, recipient_id) VALUES (%s,%s,%s)',params=(str(uuid.uuid4()),session["user_id"],friend_user_data["user_id"]))
        return redirect(url_for('auth.dashboard'))
    else:
        possible_users = SQL_manager.execute_query("SELECT username FROM users" , fetch=True)["results"]

    usernames = [user['username'] for user in possible_users]
    return render_template('add_friend.html', users=usernames)
