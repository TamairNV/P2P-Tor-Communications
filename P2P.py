
import requests


def send_data_to_onion(target_onion, data):
    # The .onion address should include the port if not 80
    url = f"http://{target_onion}/receive"

    try:
        # Use Tor's SOCKS proxy (assuming default Tor configuration)
        session = requests.session()
        session.proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }

        response = session.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


