# github.com/colingoodman

import jwt
import time
import json
from hyper import HTTPConnection, HTTP20Connection
import os
import threading

APNS_DEVELOPMENT_SERVER = 'api.sandbox.push.apple.com:443'
APNS_PRODUCTION_SERVER = 'api.push.apple.com:443'

TEAM_ID = 'UR4RG553ZN'
BUNDLE_ID = 'com.squids.Squidchat'


class NotificationSystem:
    def __init__(self):
        cwd = os.getcwd()
        self.secret = open(os.path.join(cwd, 'key.p8')).read()
        self.id = open(os.path.join(cwd, 'key_id')).read().strip()
        self.token_storage = os.path.join(cwd, 'jwt_birthtime')

        self.token = None
        self.generate_token()
        self.conn = HTTP20Connection(APNS_DEVELOPMENT_SERVER, force_proto='h2')

        refresh_thread = threading.Thread(target=self.consistent_connection, args=())
        refresh_thread.start()

    def consistent_connection(self):
        while True:
            time.sleep(2700)
            self.generate_token()

    # Generate a new JWT for APNS every 30 minutes
    def generate_token(self):
        if os.path.isfile(self.token_storage):
            jwt_birthtime_file = open(self.token_storage, 'r')
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
                self.secret,
                algorithm='ES256',
                headers={
                    'alg': 'ES256',
                    'kid': self.id
                }
            )

            jwt_birthtime_file = open(self.token_storage, 'w')
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
        # print('Token is ' + target_token)
        print('Sent APNS payload.', resp.read())

        # print(resp.read())

        if resp.status == 410 or resp.status == 400:
            return False

        return True

    def payload_message(self, author, body, room_id, room_title='Channel', type=0):
        # print('Generated APNS payload message.')  # for debug

        # check if message is in a DM or might be an image
        if type == 0:
            if len(body) == 0:
                content_body = 'Image'
                title = f'{room_title}'
            else:
                content_body = f'{author}: {body}'
                title = f'{room_title}'
        elif type == 1:
            if len(body) == 0:
                content_body = 'Image'
                title = f'{author}'
            else:
                content_body = f'{body}'
                title = f'{author}'

        payload_data = {
            'aps': {
                'alert': {
                    'title': title,
                    'body': content_body 
                },
                'sound': 'default',
                'badge': 0
            },
            'room_id': room_id
        }

        payload = json.dumps(payload_data).encode('utf-8')

        return payload

