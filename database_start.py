from time import sleep

import Server_Start

if __name__ == "__main__":
    try:
        # Start Tor with MySQL config
        with Server_Start.TorServer(
                new_onion=False,
                hs_port=3306,
                local_port=3306,
                data_dir="tor_mysql",
                torrc_params="""\
          
                """
        ) as (onion_address, _):

            print(f"MySQL accessible at: {onion_address}")


            while True:
                sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {str(e)[:200]}")  # Truncate long errors