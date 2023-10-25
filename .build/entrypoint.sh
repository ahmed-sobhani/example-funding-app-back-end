#!/bin/sh

set -e

wait_for() {
    /wait-for.sh ${DB_HOST}:${DB_PORT}
    /wait-for.sh ${REDIS_HOST}:${REDIS_PORT}
    /wait-for.sh ${MONGO_HOST}:${MONGO_PORT}
    /wait-for.sh ${EMQ_DASHBOARD_URL}:${EMQ_DASHBOARD_PORT}
}


if [ "$1" == "socket" ]
then
    wait_for && exec uwsgi --ini /uwsgi.conf
elif [ "$1" == "rest" ]
then
    wait_for && exec DJANGO_SETTINGS_MODULE=abreast.settings python manage.py runserver
else
elif [ "$1" == "celery" ]
then
    wait_for &&  exec /usr/bin/supervisord -c /supervisord.conf
else
    exec $1
fi
