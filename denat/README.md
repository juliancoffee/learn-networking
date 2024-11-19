# What
A set of programs that allows you to establish peer-to-peer communication
behind NAT

# Run
1) Run `python -m denat.server` on a remote machine with public IP address
2) Copy config_example.toml into config.toml and update the IP (and optionally
a port)
3) Edit your ID and your peer ID (should be reversed on other machine)
4) Run `python -m denat.client` on both machines

# Install (for development) and run
```bash
$ pipx install --editable .
```
Now you'll have these installed globally and you can instead do the following:
1) Run `denat-server` to run the server
2) Run `denat-client` to run the client
