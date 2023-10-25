from urllib.parse import urlparse

import requests


def make_short(url):
    parse = urlparse(url)
    if parse.netloc == 'website.com':
        try:
            short_link = requests.post('https://ham3.ir', json={'url': url})
            url = short_link.json()['url']
        except:
            pass
    return url
