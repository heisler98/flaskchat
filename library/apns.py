# github.com/colingoodman

import jwt
import time
import json
from hyper import HTTPConnection, HTTP20Connection

APNS_DEVELOPMENT_SERVER = 'api.sandbox.push.apple.com:443'
APNS_PRODUCTION_SERVER = 'api.push.apple.com:443'

APNS_AUTH_KEY = open('/tiny/flaskchat/key.p8')
APNS_KEY_ID = open('/tiny/flaskchat/key_id').read().strip()
secret = APNS_AUTH_KEY.read()

TEAM_ID = 'TN69P7NFS6'
BUNDLE_ID = 'com.squidsquad.Squidchat'


class NotificationSystem:
    

    def __init__(self):
        self.conn = HTTP20Connection(APNS_PRODUCTION_SERVER, force_proto='h2')

    def send_payload(self, payload, target_token):
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

        request_headers = {
            'apns-expiration': '0',
            'apns-priority': '10',
            'apns-topic': BUNDLE_ID,
            'authorization': 'bearer {0}'.format(token)
        }
        
        path = '/3/device/{0}'.format(target_token)

        self.conn.request(
            'POST',
            path,
            payload,
            headers=request_headers
        )

        resp = self.conn.get_response()

        print(resp.read())

        if resp.status == 410 or resp.status == 400:
            return False

        return True

    def payload_message(self, author, body, room_title='Channel', type=0):
        if type == 0:  # room
            payload_data = {
                'aps': {
                    'alert': {
                        'title': f'{room_title}',
                        'body': f'{author}: {body}',
                        'sound': 'bingbong.aiff'
                    },
                    'badge': 68
                }
            }
        elif type == 1:  # DM
            payload_data = {
                'aps': {
                    'alert': {
                        'title': f'{author}',
                        'body': f'{body}',
                        'sound': 'bingbong.aiff'
                    },
                    'badge': 70
                }
            }

        payload = json.dumps(payload_data).encode('utf-8')

        return payload

