from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import secrets
import SQL_manager
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.friend import friend_bp
from tor import get_onion_address
import Encryption_Manager

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('auth.dashboard'))
    return render_template('index.html',onion_address = get_onion_address())


#@app.teardown_appcontext
#def teardown(exception=None):
#    SQL_manager.execute_query("UPDATE users SET is_online = FALSE WHERE user_id = %s", (session['user_id'],))

if __name__ == '__main__':

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(friend_bp, url_prefix='/friend')


    app.run(port=8000, debug=True)
