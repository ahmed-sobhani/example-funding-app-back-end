FROM python:3-alpine

ADD https://raw.githubusercontent.com/eficode/wait-for/828386460d138e418c31a1ebf87d9a40f5cedc32/wait-for /wait-for.sh

RUN addgroup -g 10001 www-data1 && adduser -u 10001 -HD -G www-data1 www-data1 && \
    apk add --no-cache \
        postgresql-dev \
        pcre-dev \
        supervisor \
        zlib-dev \
        jpeg-dev \
        tzdata && \
    rm -rf /var/cache/apk/* && \
    chmod 755 /wait-for.sh && \
    mkdir -p /var/www/media && \
    mkdir -p /var/www/static && \
    chown www-data1:www-data -R /var/www/media && \
    chown www-data1:www-data1 -R /var/www/static

COPY [".build/entrypoint.sh", ".build/supervisord.conf", ".build/uwsgi.conf", "requirements.txt", "/"]

RUN apk add --no-cache --virtual .build-deps \
        linux-headers \
        musl-dev \
        gcc && \
    pip install -r requirements.txt && \
    apk del .build-deps && \
    rm -rf /var/cache/apk/* && rm -rf /root/.cache && \
    chmod +x /entrypoint.sh


COPY --chown=www-data:www-data . /var/www
USER www-data
WORKDIR /var/www

RUN DJANGO_SETTINGS_MODULE=abreast.settings \
        python manage.py collectstatic --no-input

ENTRYPOINT ["/entrypoint.sh"]
