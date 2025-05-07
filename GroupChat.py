import Encryption_Manager
import SQL_manager
import json
import uuid
def send_message(group_chat_id,message,sender_id,sym_key):

    #Get all users in group
    sql = """
        SELECT o.public_key, o.user_id 
        FROM groupchatmember gcm
        JOIN onion_keys o ON gcm.user_id = o.user_id 
        WHERE gcm.group_id = %s;
    """
    group_chat_members_data = SQL_manager.execute_query(sql, params=(group_chat_id,),fetch=True)["results"]

    json_data =[]
    #Encrypt the message with each public key
    for data in group_chat_members_data:
        if sender_id == data['user_id']:
            #if self encrypt with sym key
            enc_message = Encryption_Manager.encrypt_message_with_symmetric_key(sym_key,message)

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
    SQL_manager.get_connection().cursor().callproc('send_message', (ID,group_chat_id,sender_id,json_string))



    pass

def get_group_members(group_chat_id):
    sql = """
    SELECT * FROM groupchatmembers WHERE group_chat_id = %s
    """
    members = SQL_manager.execute_query(sql,params = (group_chat_id,))["results"]
    return members


def get_group_chats(user_id):
    sql = """
    SELECT g.ID,g.name,g.created_at,g.last_message FROM groupchatmember m , groupchat g WHERE m.user_id = %s AND m.group_id = g.ID;
    """
    group_chats = SQL_manager.execute_query(sql, params=(user_id,))["results"]
    return group_chats

def get_group_chat_messages(user_id,group_chat_id,username,sym_key):
    sql = """
    SELECT m.sender_id, m.message, m.sent_at, u.username FROM groupchatmessage m, users u WHERE m.group_id = %s AND u.user_id = m.sender_id ORDER BY m.sender_id DESC;
    """
    message_data = SQL_manager.execute_query(sql,(group_chat_id,),fetch=True)['results']
    messages = []
    priv_key = Encryption_Manager.read_private_key(username,sym_key)

    #loop through each message data
    for message in message_data:
        #find message for you
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
                        'username' : message['username'],
                        'message' : dec_message,
                        "sent_at" : message['sent_at'],
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


    return messages


#send_message("8cc4d3aa-cafa-4f44-b5d5-04f7a1645706","wow another message'","c92397c2-a2c1-4ab6-a977-7b7e6fed2a66",'k5zl1v0EzLSNVmbGVon3WnSm/4XzvbyDQ3vd3/OgIj4=')
#send_message("8cc4d3aa-cafa-4f44-b5d5-04f7a1645706","not two messages wow '","10635a59-0a4c-43d6-a128-82902567d17b",'NyOs3vkMBLrJNbbthfIAPIZUGGc1+azyR5tiGynbzEA=')
print(get_group_chat_messages("c92397c2-a2c1-4ab6-a977-7b7e6fed2a66",'8cc4d3aa-cafa-4f44-b5d5-04f7a1645706',"TNV","k5zl1v0EzLSNVmbGVon3WnSm/4XzvbyDQ3vd3/OgIj4="))

