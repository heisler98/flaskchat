# github.com/colingoodman

import flask_jwt_extended
import jwt
import time
import json
from hyper import HTTPConnection, HTTP20Connection

APNS_DEVELOPMENT_SERVER = 'api.sandbox.push.apple.com:443'
APNS_PRODUCTION_SERVER = 'api.push.apple.com:443'

APNS_AUTH_KEY = open('/tiny/flaskchat/key.p8')
APNS_KEY_ID = open('/tiny/flaskchat/key_id').read().strip()
print(APNS_KEY_ID)
secret = APNS_AUTH_KEY.read()
print(secret)

APP_ID = open('/tiny/flaskchat/apn_hunter').read()
print(APP_ID)

TEAM_ID = 'TN69P7NFS6'
BUNDLE_ID = 'com.squidsquad.Squidchat'

print('oooh')

token = jwt.encode(
    {
        'iss': TEAM_ID,
        'iat': time.time()
    },
    secret,
    algorithm='ES256',
    headers={
        'alg': 'ES256',
        'kid': APNS_KEY_ID
    }
)

path = '/3/device/{0}'.format(APP_ID)
request_headers = {
    'apns-expiration': '0',
    'apns-priority': '10',
    'apns-topic': BUNDLE_ID,
    'authorization': 'bearer {0}'.format(token)
}

conn = HTTP20Connection('api.development.push.apple.com:443', force_proto='h2')

payload_data = {
    'aps': {
        'alert': '????!!!',
        'sound': '',
        'content-available': 1
    }
}
payload = json.dumps(payload_data).encode('utf-8')

# Send our request
conn.request(
    'POST',
    path,
    payload,
    headers=request_headers
)

resp = conn.get_response()
print(resp.status)
print(resp.read())



