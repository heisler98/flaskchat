# github.com/colingoodman

import jwt
import time
import json
from hyper import HTTPConnection, HTTP20Connection
import os

APNS_DEVELOPMENT_SERVER = 'api.sandbox.push.apple.com:443'
APNS_PRODUCTION_SERVER = 'api.push.apple.com:443'

TOKEN_TIME_STORAGE = '/tiny/flaskchat/jwt_birthtime'

APNS_AUTH_KEY = open('/tiny/flaskchat/key.p8')
APNS_KEY_ID = open('/tiny/flaskchat/key_id').read().strip()
secret = APNS_AUTH_KEY.read()

TEAM_ID = 'TN69P7NFS6'
BUNDLE_ID = 'com.squidsquad.Squidchat'


class NotificationSystem:
    def __init__(self):
        self.token = None
        self.generate_token()
        self.conn = HTTP20Connection(APNS_PRODUCTION_SERVER, force_proto='h2')

    # Generate a new JWT for APNS every 30 minutes
    def generate_token(self):
        if os.path.isfile(TOKEN_TIME_STORAGE):
            jwt_birthtime_file = open(TOKEN_TIME_STORAGE, 'r')
            jwt_birthtime = float(jwt_birthtime_file.read())
            jwt_birthtime_file.close()
        else:
            jwt_birthtime = 0
        
        now = time.time()
        create_new = False
        if not self.token:
            create_new = True
        else:
            if now - jwt_birthtime > 1800:  # 1800 seconds in 30 min
                create_new = True
        
        if create_new:
            self.token = jwt.encode(
                {
                    'iss': TEAM_ID,
                    'iat': now
                },
                secret,
                algorithm='ES256',
                headers={
                    'alg': 'ES256',
                    'kid': APNS_KEY_ID
                }
            )

            jwt_birthtime_file = open(TOKEN_TIME_STORAGE, 'w')
            jwt_birthtime_file.write(str(now))
            jwt_birthtime_file.close()

    def send_payload(self, payload, target_token):
        print('Generated APNS payload.')

        self.generate_token()

        request_headers = {
            'apns-expiration': '0',
            'apns-priority': '10',
            'apns-topic': BUNDLE_ID,
            'authorization': 'bearer {0}'.format(self.token)
        }
        
        path = '/3/device/{0}'.format(target_token)

        self.conn.request(
            'POST',
            path,
            payload,
            headers=request_headers
        )

        resp = self.conn.get_response()
        print('Sent APNS payload.')

        print(resp.read())

        if resp.status == 410 or resp.status == 400:
            return False

        return True

    def payload_message(self, author, body, room_id, room_title='Channel', type=0):
        # print('Generated APNS payload message.')  # for debug

        if type == 0:  # room
            payload_data = {
                'aps': {
                    'alert': {
                        'title': f'{room_title}',
                        'body': f'{author}: {body}',
                        'sound': 'default'
                    },
                    'badge': 68
                },
                'room_id': room_id
            }
        elif type == 1:  # DM
            payload_data = {
                'aps': {
                    'alert': {
                        'title': f'{author}',
                        'body': f'{body}',
                        'sound': 'default'
                    },
                    'badge': 70
                },
                'room_id': room_id
            }

        payload = json.dumps(payload_data).encode('utf-8')

        return payload

