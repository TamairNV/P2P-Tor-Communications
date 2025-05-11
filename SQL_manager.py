import pymysql
import socks
import socket
from stem import Signal
from stem.control import Controller

connections = []
onion_link = 'loqsfaq44mnyvvjkzggrnhtajg7napunrpmq7etnfg73p7o7qnzh72qd.onion'
# Configure Tor proxy
def setup_tor_proxy():
    socks.set_default_proxy(
        socks.SOCKS5,
        addr="127.0.0.1",
        port=9050  # Default Tor SOCKS port
    )
    socket.socket = socks.socksocket

    # Force DNS requests through Tor
    def getaddrinfo(*args):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]

    socket.getaddrinfo = getaddrinfo


def renew_tor_identity():
    """Renew Tor circuit to get a new exit node"""
    with Controller.from_port(port=9051) as controller:  # Tor control port
        controller.authenticate()
        controller.signal(Signal.NEWNYM)


def get_connection():
    setup_tor_proxy()
    try:
        return pymysql.connect(
            host=onion_link,
            user="root",
            password="Tamer2006",
            database="p2p_communication",
            port=3306,
            connect_timeout=30,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.Error as e:
        print(f"Connection failed: {e}")
        # Try renewing Tor circuit and retry once
        renew_tor_identity()
        return pymysql.connect(
            host=onion_link,
            user="root",
            password="Tamer2006",
            database="p2p_communication",
            port=3306,
            connect_timeout=30,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )


def test_connection():
    try:
        conn = get_connection()
        print("✅ Connected successfully!")
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Basic query executed:", cursor.fetchone())
        conn.close()
    except Exception as e:
        print("❌ Connection failed:", str(e))


# Test the connection

def release_connection(conn):
    connections.append(conn)


def execute_query(query, params=None, fetch=False):
    result = {
        'success': False,
        'results': None,
        'lastrowid': None,
        'rowcount': 0,
        'error': None
    }
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())

            if fetch:
                result['results'] = cursor.fetchall()
            result['lastrowid'] = cursor.lastrowid
            result['rowcount'] = cursor.rowcount

            conn.commit()
            result['success'] = True

    except Exception as err:
        if conn:
            conn.rollback()
        result['error'] = str(err)
    finally:
        if conn:
            release_connection(conn)

    return result

