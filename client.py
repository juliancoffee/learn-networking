import socket
import sys
import tomllib

def remote() -> tuple[str, int]:
    with open("config.toml", "rb") as f:
        data = tomllib.load(f)

    remote_host = data["remote_host"]
    remote_port = int(data["remote_port"])

    return remote_host, remote_port

try:
    remote_host, remote_port = remote()
except Exception as e:
    print("couldn't read the config.toml")
    print(f"{e=}")


try:
    port = int(sys.argv[1])
    print(f"<> using src port: {port}")
except (ValueError, IndexError):
    port = 9_990
    print("<err> couldn't get the src port from arguments")
    print(f"<> using default src port: {port}")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
while True:
    try:
        host = "0.0.0.0"
        print(f"<> binding to {host}:{port}")
        s.bind((host, port))
        break
    except OSError as e:
        if e.errno == 48:
            print(f"<err> {port=} is taken, trying the next one")
            port += 1
        else:
            raise e

print(f"<> good, ready to connect to {remote_host}:{remote_port}")
s.sendto(b"hi server", (remote_host, remote_port))
print("<> send a message, fetching the response")
peer_addr_string, server_addr = s.recvfrom(100)
peer_host, peer_port_string = peer_addr_string.decode("utf-8").split(":")
peer_port = int(peer_port_string)
print(f"<> server says our peer is {peer_host}:{peer_port}")
s.sendto(b"hi peer", (peer_host, peer_port))
print(f"<> said hello to peer")
msg, addr = s.recvfrom(100)
print(f"<> {msg!r} our peer said")
