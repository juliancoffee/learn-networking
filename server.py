import socket
import sys

try:
    port = int(sys.argv[1])
    print(f"using port: {port}")
except (ValueError, IndexError):
    port = 11_111
    print("(couldn't get the port)")
    print(f"using default port: {port}")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", port))
print("bound and ready to receive messages")

msg, addr1 = s.recvfrom(100)
addr1_string = ":".join(map(str, addr1))
print(f"[{addr1_string}] send us a message. <{msg.decode('utf-8')}> they said")

msg, addr2 = s.recvfrom(100)
addr2_string = ":".join(map(str, addr2))
print(f"[{addr2_string}] send us a message. <{msg.decode('utf-8')}> they said")

s.sendto(addr1_string.encode('utf-8'), addr2)
s.sendto(addr2_string.encode('utf-8'), addr1)
