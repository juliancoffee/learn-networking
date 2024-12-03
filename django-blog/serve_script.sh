# Dockerfile entry point

# empty .env file, because I just can't get rid of it
# it won't do much at this point, but at least it won't interfere with the app
echo "" > .env

# run Django in the background
echo "<> static root is: $STATIC_ROOT"
# I have zero idea why this command is needed
# I'd expect docker to spin a fresh new image without old data, but idk
# so I do this just in case
if [ -d "$STATIC_ROOT" ]
then
    echo "<> $STATIC_ROOT is dirty, cleaning it"
    rm -rf "$STATIC_ROOT"
fi
uv run manage.py collectstatic

echo "<> running migrations"
uv run manage.py migrate

echo "<> running the server"
uv run manage.py runserver &

# run nginx
echo "<> run nginx"
nginx -g 'daemon off;'
