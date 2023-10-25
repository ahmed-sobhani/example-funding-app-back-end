import firebase_admin
from django.conf import settings
from firebase_admin import credentials


def firebase():
    if hasattr(firebase, 'instance'):
        return firebase.instance
    else:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
        inst = firebase.instance = firebase_admin.initialize_app(cred)
        return inst
