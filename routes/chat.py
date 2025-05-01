


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
chat_bp = Blueprint('chat', __name__)

def get_messages(friend):
    messages = []


    query = """
    SELECT ok.* 
    FROM onion_keys ok
    JOIN users u ON ok.user_id = u.user_id
    WHERE u.username = %s
    ORDER BY ok.last_updated DESC
    LIMIT 1
    """

    session['current_chat_data'] = SQL_manager.execute_query(
        query,
        params=(friend,),
        fetch=True
    )["results"][0]
    session['current_chat_data']['username'] = friend

    waiting_messages = SQL_manager.execute_query(
        "SELECT message,send_at FROM message WHERE receiver_id = %s AND sender_id = %s ORDER BY send_at DESC",
        params=(session["user_id"], session["current_chat_data"]["user_id"]), fetch=True)["results"]
    print(waiting_messages)

    os.makedirs("Data/Chat_data/" + session["username"], exist_ok=True)
    with open("Data/Chat_data/" + session["username"] + "/" + session['current_chat_data']['username'], 'a') as f:
        for message in waiting_messages:
            f.write(message["send_at"].strftime("%I:%M%p on %B %d, %Y") + "\n" + friend + "\n" + str(
                clean_message(message["message"])) + "\n")


    SQL_manager.execute_query("DELETE FROM message WHERE receiver_id = %s AND sender_id = %s",
                              params=(session["user_id"], session["current_chat_data"]["user_id"]))

    with open("Data/Chat_data/" + session["username"] + "/" + session['current_chat_data']['username'], 'r') as f:
        lines = f.readlines()
        for i in range(0, len(lines), 3):
            if lines[i + 1].strip() == session["username"]:
               encrypted_message = lines[i + 2]
               message = Encryption_Manager.decrypt_message_with_symmetric_key(session["sym_key"], encrypted_message)
            else:
                message_line = lines[i+2].strip()
                message = Encryption_Manager.decrypt_with_private_key(Encryption_Manager.read_private_key(session["username"]), message_line[2:len(message_line)-1])

            m = {
                "sent_at": lines[i].strip(),
                "sender": lines[i + 1].strip(),
                "message":message
            }
            messages.append(m)
    print(messages)
    return messages




@chat_bp.route('/chat/<friend>')
def chat(friend):

    if 'username' not in session:
        return redirect(url_for('index'))

    messages = get_messages(friend)

    return render_template('chat.html',
                               friend=friend,
                               messages=messages)

def clean_message(message):
    if message[0] == 'b':
        return message[2:len(message)-2]
    return message


@chat_bp.route('/send-message', methods=['POST'])
def send_message():

    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    print(session['current_chat_data'])

    is_online = SQL_manager.execute_query("SELECT is_online FROM users WHERE user_id = %s", (session['current_chat_data']['user_id'],),fetch=True)["results"][0]
    print(is_online)
    request_message = request.form.get('message')
    print(session['current_chat_data']['public_key'])
    print(request_message)
    encrypted_message = Encryption_Manager.encrypt_with_public_key_pem(session['current_chat_data']['public_key'],request_message)
    print(encrypted_message)
    if is_online and False:
        print("sending data p2p")
        P2P.send_data_to_onion(session['current_chat_data']["onion_address"],encrypted_message)
    else:
        print("sending data to database")
        SQL_manager.execute_query("INSERT INTO message (sender_id, receiver_id, message) VALUES (%s,%s,%s)",params=(session['user_id'],session['current_chat_data']['user_id'],encrypted_message))
        pass
    syKey = session["sym_key"]
    print( "symmetric Key: "+syKey)
    with open("Data/Chat_data/"+ session["username"] +"/"  + session['current_chat_data']['username'], 'a') as f:
        f.write(datetime.now().strftime("%I:%M%p on %B %d, %Y") + "\n" + session['username'] +"\n" +  Encryption_Manager.encrypt_message_with_symmetric_key(syKey,request_message) + "\n")
        print("data written to file")





    print(request_message)
    messages = get_messages(session['current_chat_data']['username'])
    return render_template('chat.html',friend=session['current_chat_data']['username'],messages =messages)

import P2P
@chat_bp.route('/receive', methods=['POST'])
def receive_data():
    data = request.json
    print(f"Received data: {data}")
    return jsonify({"status": "success"}), 200


