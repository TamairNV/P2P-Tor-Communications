import SQL_manager


def send_message(group_chat_id,message,sender_id):
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

def get_group_chat_messages(user_id,group_chat_id):
    pass

