import os
import shutil
import subprocess
import logging
from time import sleep
from typing import Tuple, Optional
from pathlib import Path
import signal




class TorServer:
    """A managed Tor hidden service instance."""

    def __init__(self,
                 data_dir: str = "tor_data",
                 tor_executable: str = "tor",
                 hs_port: int = 80,
                 local_port: int = 8000,
                 new_onion: bool = False,
                 torrc_params: str = "" ):
        """
        Args:
            data_dir: Directory for Tor data files
            tor_executable: Path to tor binary
            hs_port: Hidden service port
            local_port: Local port to forward
            new_onion: Generate new onion address if True
        """
        self.data_dir = Path(data_dir).absolute()
        self.tor_executable = tor_executable
        self.hs_port = hs_port
        self.local_port = local_port
        self.new_onion = new_onion
        self.process = None
        self.onion_address = None
        self.torrc_params = torrc_params

        self.hidden_service_dir = self.data_dir / "hidden_service"
        self.torrc_path = self.data_dir / "torrc"

        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("TorServer")

    def _prepare_directories(self) -> None:
        """Ensure proper directory structure and permissions."""
        try:
            if self.new_onion and self.hidden_service_dir.exists():
                shutil.rmtree(self.hidden_service_dir)

            self.data_dir.mkdir(exist_ok=True, mode=0o700)
            self.hidden_service_dir.mkdir(exist_ok=True, mode=0o700)

        except Exception as e:
            self.logger.error(f"Directory preparation failed: {e}")
            raise

    def _generate_torrc(self) -> None:
        """Generate Tor configuration file."""
        torrc_content = f"""\
DataDirectory {self.data_dir}
HiddenServiceDir {self.hidden_service_dir}
HiddenServicePort {self.hs_port} 127.0.0.1:{self.local_port}
Log notice stdout
SocksPort 0
ControlPort 0
"""
        # Add additional parameters without extra indentation
        if self.torrc_params:
            torrc_content += self.torrc_params.strip() + "\n"

        try:
            with open(self.torrc_path, "w") as f:
                f.write(torrc_content)
            self.torrc_path.chmod(0o600)
            self.logger.debug(f"Generated torrc at {self.torrc_path}")
            self.logger.debug(f"Torrc content:\n{torrc_content}")
        except Exception as e:
            self.logger.error(f"Failed to create torrc: {e}")
            raise
    def _launch_tor(self) -> subprocess.Popen:
        """Start Tor subprocess."""
        try:
            self.logger.info(f"Starting Tor with config: {self.torrc_path}")
            process = subprocess.Popen(
                [self.tor_executable, "-f", str(self.torrc_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Verify process started
            sleep(1)
            if process.poll() is not None:
                err = process.stderr.read()
                self.logger.error(f"Tor failed to start: {err}")
                raise RuntimeError(f"Tor process died immediately: {err}")

            return process

        except Exception as e:
            self.logger.error(f"Tor launch failed: {e}")
            raise

    def _wait_for_onion(self, timeout: int = 30) -> str:
        """Wait for onion address to be generated."""
        hostname_file = self.hidden_service_dir / "hostname"

        try:
            for _ in range(timeout):
                if hostname_file.exists():
                    with open(hostname_file) as f:
                        return f.read().strip()
                sleep(1)

            raise TimeoutError("Onion address not generated in time")
        except Exception as e:
            self.logger.error(f"Failed to get onion address: {e}")
            raise

    def start(self) -> Tuple[str, subprocess.Popen]:
        """Start the Tor hidden service."""
        try:
            self._prepare_directories()
            self._generate_torrc()
            self.process = self._launch_tor()
            self.onion_address = self._wait_for_onion()

            self.logger.info(f"Hidden service started at: {self.onion_address}")
            return self.onion_address, self.process

        except Exception as e:
            self.stop()
            raise

    def stop(self) -> None:
        """Stop the Tor service and clean up."""
        if self.process and self.process.poll() is None:
            self.logger.info("Stopping Tor process...")
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                self.logger.warning(f"Error stopping Tor: {e}")

        self.process = None
        self.onion_address = None

    def __enter__(self):
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


if __name__ == "__main__":
    try:
        # Example usage
        with TorServer(new_onion=False) as (onion_address, process):
            print(f"Service running at {onion_address}")
            print("Press Ctrl+C to stop...")
            while True:
                sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")