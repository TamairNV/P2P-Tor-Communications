from pathlib import Path


def get_onion_address():
    hostname_file = Path("tor_data").absolute() / "hidden_service" / "hostname"
    with open(hostname_file) as f:
        return str(f.read().strip())
