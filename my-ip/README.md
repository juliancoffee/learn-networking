# What's this
Simple web server that shows your IP address, port and maybe some other stuff.

# Build
That's a simple python program that uses FastAPI.

# Deploy
This service was created to be deployed on Render.

Go to render.com docs for more.

# Why?
Well, as an experiment to play with NAT.<br>
Spoiler, it didn't work out in my case, probably because Render uses
(reverse) proxies and I couldn't figure out how to make them forward a client port to my application.
