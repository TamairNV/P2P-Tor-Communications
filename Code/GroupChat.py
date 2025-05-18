import json
import os
import uuid

from click import DateTime
from datetime import datetime
from utils import Encryption_Manager, SQL_manager
from threading import Thread

def send_message(group_chat_id, message, sender_id, sym_key,username):
    # Get all users in group
    sql = """
        SELECT o.public_key, o.user_id 
        FROM groupchatmember gcm
        JOIN onion_keys o ON gcm.user_id = o.user_id 
        WHERE gcm.group_id = %s;
    """
    group_chat_members_data = SQL_manager.execute_query(sql, params=(group_chat_id,), fetch=True)["results"]

    json_data = []
    # Encrypt the message with each public key
    for data in group_chat_members_data:
        if sender_id == data['user_id']:
            # if self encrypt with sym key
            enc_message = Encryption_Manager.encrypt_message_with_symmetric_key(sym_key, message)

        else:
            enc_message = Encryption_Manager.encrypt_with_public_key_pem(data['public_key'], message)
        # Add messages to json file
        obj = {
            "message": enc_message,
            "user_id": data['user_id'],
        }

        json_data.append(obj)

    json_string = json.dumps(json_data, indent=2)
    ID = uuid.uuid4()
    # Create message in database
    SQL_manager.get_connection().cursor().callproc('send_message', (ID, group_chat_id, sender_id, json_string))

    current_dir = os.path.dirname(__file__)
    data_path = os.path.join(current_dir, '..', 'Data', 'Chat_data', username, f'{group_chat_id}.txt' )
    normalized_path = os.path.normpath(data_path)
    with open(normalized_path, 'a') as f:
        f.write(datetime.now().strftime("%I:%M%p on %B %d, %Y") + '\n')
        f.write(username + '\n')
        f.write(Encryption_Manager.encrypt_message_with_symmetric_key(sym_key,message) + '\n')


    pass


def get_group_members(group_chat_id):
    sql = """
    SELECT groupchatmember.* , u.username FROM groupchatmember,users u WHERE group_id = %s AND u.user_id = groupchatmember.user_id;
    """
    members = SQL_manager.execute_query(sql, params=(group_chat_id,), fetch=True)['results']
    return members


def get_group_chats(user_id):
    sql = """
    SELECT
    g.ID,
    g.name,
    g.created_at,
    g.last_message,
    (
        SELECT JSON_OBJECTAGG(
            g2.name,
            (
                SELECT JSON_ARRAYAGG(u.username)
                FROM groupchatmember m2
                JOIN users u ON m2.user_id = u.user_id
                WHERE m2.group_id = g2.ID
            )
        )
        FROM groupchat g2
        WHERE g2.ID = g.ID
    ) AS members_dict
FROM
    groupchatmember m
JOIN
    groupchat g ON m.group_id = g.ID
WHERE
    m.user_id = %s;

    """
    group_chats = SQL_manager.execute_query(sql, params=(user_id,), fetch=True)["results"]
    return group_chats

def read_all_messages(group_chat_id,username):
    print("updating messages to read")
    sql = """
    UPDATE messageread 
    SET is_read = 1 
    WHERE 
      reader = (SELECT user_id FROM users WHERE username = %s) 
      AND group_chat_id = %s;
    """
    SQL_manager.execute_query(sql, params=(username,group_chat_id,))
    sql = """
        DELETE FROM groupchatmessage
    WHERE group_id = %s
    AND NOT EXISTS (
        SELECT 1 FROM messageread
        WHERE message_id = groupchatmessage.id
        AND is_read = 0
    );
    """
    SQL_manager.execute_query(sql, params=(group_chat_id,))
    print("message read")



def write_messages_to_file(messages,group_chat_id,username,sym_key):
    current_dir = os.path.dirname(__file__)
    data_path = os.path.join(current_dir, '..', 'Data', 'Chat_data', username, f'{group_chat_id}.txt' )
    normalized_path = os.path.normpath(data_path)
    with open(normalized_path, 'a') as f:
        if messages:
            for message in messages:
                f.write(message['sent_at'].strftime("%I:%M%p on %B %d, %Y") + '\n')
                f.write(message['username'] + '\n')
                f.write(Encryption_Manager.encrypt_message_with_symmetric_key(sym_key,message['message']) + '\n')


def get_group_chat_messages(user_id, group_chat_id, username, sym_key):

    sql = """
        SELECT 
            m.id,
            m.sender_id,
            m.message,
            m.sent_at,
            u.username,
            IFNULL(mr.is_read, 0) as is_read_status  -- Default to unread if no record exists
        FROM GroupChatMessage m
        JOIN users u ON u.user_id = m.sender_id
        LEFT JOIN messageRead mr ON mr.message_id = m.id AND mr.reader = %s  -- Your user ID
        WHERE m.group_id = %s  -- The group chat ID
        AND mr.is_read = 0
        ORDER BY m.sent_at;
    """

    message_data = SQL_manager.execute_query(sql, (user_id,group_chat_id,), fetch=True)['results']

    messages = []

    priv_key = Encryption_Manager.read_private_key(username, sym_key)
    if message_data is None:
        return []
    # loop through each message data
    for message in message_data:
        # find message for you
        # check if sender is self

        if message['sender_id'] == user_id:
            data = json.loads(message['message'])
            for m in data:
                # check if sender is self
                if m['user_id'] == user_id:
                    # if self then decrypt with sym key
                    dec_message = Encryption_Manager.decrypt_message_with_symmetric_key(sym_key, m['message'])
                    # append clear message to array
                    messages.append({
                        'username': message['username'],
                        'message': dec_message,
                        "sent_at": message['sent_at'],
                    })
                    break
        else:
            data = json.loads(message['message'])
            for m in data:
                # check if sender is self
                if m['user_id'] == user_id:
                    # else decrypt with acy key
                    dec_message = Encryption_Manager.decrypt_with_private_key(priv_key, m['message'])
                    # append clear message to array
                    messages.append({
                        'username': message['username'],
                        'message': dec_message,
                        "sent_at": message['sent_at'],
                    })
                    break
    print(messages)
    update_read = Thread(target=read_all_messages, args=(group_chat_id,username,))
    update_read.start()
    write_messages_to_file(messages,group_chat_id,username,sym_key)

    return read_messages_from_file(username,group_chat_id,sym_key)

def read_messages_from_file(username,group_chat_id,sym_key):
    current_dir = os.path.dirname(__file__)
    data_path = os.path.join(current_dir, '..', 'Data', 'Chat_data', username, f'{group_chat_id}.txt' )
    normalized_path = os.path.normpath(data_path)
    messages = []
    with open(normalized_path,'r') as f:
        lines = f.readlines()
        for i in range(0, len(lines), 3):
            encrypted_message = lines[i + 2]
            message = Encryption_Manager.decrypt_message_with_symmetric_key(sym_key, encrypted_message)
            m = {
                "sent_at": lines[i].strip(),
                "username": lines[i + 1].strip(),
                "message": message
            }
            messages.append(m)
    return messages

# send_message("8cc4d3aa-cafa-4f44-b5d5-04f7a1645706","wow another message'","c92397c2-a2c1-4ab6-a977-7b7e6fed2a66",'k5zl1v0EzLSNVmbGVon3WnSm/4XzvbyDQ3vd3/OgIj4=')
# send_message("8cc4d3aa-cafa-4f44-b5d5-04f7a1645706","not two messages wow '","10635a59-0a4c-43d6-a128-82902567d17b",'NyOs3vkMBLrJNbbthfIAPIZUGGc1+azyR5tiGynbzEA=')
#print(get_group_chat_messages("c92397c2-a2c1-4ab6-a977-7b7e6fed2a66",'1c1b5142-9797-4d0a-93a1-6d0796009781',"TNV","k5zl1v0EzLSNVmbGVon3WnSm/4XzvbyDQ3vd3/OgIj4="))
# print(get_group_chats('c92397c2-a2c1-4ab6-a977-7b7e6fed2a66'))
# print(get_group_members('1c1b5142-9797-4d0a-93a1-6d0796009781'))
