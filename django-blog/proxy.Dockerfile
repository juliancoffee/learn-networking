FROM nginx

COPY staticfiles /data/static

COPY nginx.conf /etc/nginx/nginx.conf
