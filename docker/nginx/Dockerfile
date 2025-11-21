FROM alpine:latest

RUN apk update && apk add nginx

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf


RUN mkdir -p /usr/share/nginx/html && chmod 755 /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
