
# Abreast
a donating/funding backend web application code example with Django

Abreast Project. www.website.com
- python 3.6
- django 1.11.16
- postgresql
- celery
- redis

## Requirements

- python 3.6
- amqp 2.4.1
- backports.csv 1.0.7
- billiard 3.5.0.5
- CacheControl 0.12.5
- cachetools 3.1.1
- celery 4.2.1
- certifi 2018.11.29
- chardet 3.0.4
- coreapi 2.3.3
- coreschema 0.0.4
- coverage 4.5.3
- django-ckeditor 5.6.1
- defusedxml 0.6.0
- diff-match-patch 20181111
- Django 1.11.16
- django-constance 2.4.0
- django-cors-headers 2.5.0
- django-filter 2.1.0
- django-import-export 1.2.0
- django-picklefield 2.0
- django-rosetta 0.9.3
- djangorestframework 3.9.1
- djangorestframework-jwt 1.11.0
- et-xmlfile 1.0.1
- firebase-admin 2.17.0
- google-api-core 1.11.1
- google-api-python-client 1.7.9
- google-auth 1.6.3
- google-auth-httplib2 0.0.3
- google-cloud-core 1.0.1
- google-cloud-firestore 1.2.0
- google-cloud-storage 1.16.0
- google-resumable-media 0.3.2
- googleapis-common-protos 1.6.0
- grpcio 1.37.1
- httplib2 0.12.3
- idna 2.8
- itypes 1.1.0
- jdcal 1.4.1
- Jinja2 2.10.1
- kavenegar 1.1.2
- Khayyam 3.0.17
- kombu 4.3.0
- MarkupSafe 1.1.1
- mongoengine 0.18.0
- msgpack 0.6.1
- odfpy 1.4.0
- openpyxl 2.6.2
- Pillow 5.4.1
- polib 1.1.0
- protobuf 3.8.0
- psycopg2 2.7.7
- psycopg2-binary 2.7.7
- pyasn1 0.4.5
- pyasn1-modules 0.2.5
- pycrypto 2.6.1
- PyJWT 1.7.1
- pymongo 3.8.0
- pytz 2018.9
- PyYAML 5.1.1
- redis 3.2.1
- requests 2.21.0
- rsa 4.0
- six 1.12.0
- sorl-thumbnail 12.5.0
- suds-jurko 0.6
- django-schema-graph
- tablib 0.13.0
- uritemplate 3.0.0
- urllib3 1.24.1
- vine 1.2.0
- xlrd 1.2.0
- xlwt 1.3.0


## Logging
  - django.log
  - celery.log

## Email Backend (500 error)
  - email-host-user: 'ahmad.sobhani@hotmail.com'

## Database Graph
  - http://website.com:8010/schema/

## Create Subscription Transaction:
### Manually Create Subscription Transaction in django Shell at "abreast" server:
  1. `python manage.py shell`
  2. `from subscription.tasks import get_specific_date_subscription_charges`
  3. `from datetime import timedelta`
  4. `from django.utils import timezone`
  5. `get_specific_date_subscription_charges(timezone.now() - timedelta(days=*))`
     * days = day difference between today's date and a specified date (edited) 
