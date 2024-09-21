# What
A set of programs that allows you to establish peer-to-peer communication
behind NAT

# Run
1) Run server.py on a remote machine with public IP address
2) Copy config_example.toml into config.toml and update the IP (and optionally
a port)
3) Edit your ID and your peer ID (should be reversed on other machine)
4) Run client.py on both machines
