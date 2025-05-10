import subprocess

subprocess.run([
    './windows-tor/tor.exe',
    '-f',
    "./torrc"
])