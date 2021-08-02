# github.com/colingoodman

from datetime import datetime
import time
# from bson import ObjectId
import bson
from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash

from model.user import User
from model.room import Room
from model.room import Message


class Connect(object):
    @staticmethod
    def get_connection():
        return MongoClient(host='localhost', port=27017, username='flaskuser', password='193812465340',
                           authSource='admin')


client = MongoClient(host='localhost', port=27017, username='flaskuser', password='193812465340', authSource='admin')

chat_db = client['chatdb']
users_collection = chat_db.get_collection('users')
rooms_collection = chat_db.get_collection('rooms')
room_members_collection = chat_db.get_collection('room_members')
messages_collection = chat_db.get_collection('messages')
reactions_collection = chat_db.get_collection('reactions')
emoji_collection = chat_db.get_collection('emoji')
logging_collection = chat_db.get_collection('logs')
images_collection = chat_db.get_collection('images')


# USERS


# create a new user record, used for signups
def save_user(username, email, password, fullname):
    if users_collection.find_one({'username': username}, {'username': 1}):
        raise DuplicateKeyError('Username already exists.')
    if users_collection.find_one({'email': email}, {'email': 1}):
        raise DuplicateKeyError('Email already exists.')

    now = time.time()
    password_hash = generate_password_hash(password)
    identifier = users_collection.insert_one({'username': username, 'email': email, 'password': password_hash,
                                              'real_name': fullname, 'date_joined': now, 'avatar': None}).inserted_id

    return identifier


def store_apn(user_id, token):
    try:
        apn_tokens = users_collection.find_one({'_id': ObjectId(user_id)}, {'apn': 1})['apn']
    except KeyError as e:
        apn_tokens = None
    if apn_tokens:
        if token in apn_tokens:
            return None
        else:
            apn_tokens.append(token)
            users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'apn': apn_tokens}})
            return 'Yes'
    else:
        apn_tokens = [token]
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'apn': apn_tokens}})
        return 'Yes'


def purge_apn(token):
    users_collection.update({}, {'$pull': {'apn': token}})


def get_apn(user_id):
    try:
        apn_tokens = users_collection.find_one({'_id': ObjectId(user_id)}, {'apn': 1})['apn']
    except KeyError as e:
        apn_tokens = None
    if not apn_tokens:
        return None
    return list(apn_tokens)


def update_checkout(user_id):
    now = time.time()
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'last_online': now}})


# used for admin / super user purposes
def crown_user(username, status=True):
    users_collection.update_one({'username': username}, {'$set': {'god': status}})


def change_user_password(user_id, new_password):
    password_hash = generate_password_hash(new_password)
    # now = datetime.now()
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'password': password_hash}})


def update_user(user_id, itemized_user):
    for kvp in itemized_user:
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {kvp[0]: kvp[1]}})


def change_user_avatar(user_id, file_id):
    try:
        current_avatar = users_collection.find_one({'_id': ObjectId(user_id)}, {'avatar': 1})['avatar']
    except KeyError as e:
        current_avatar = None

    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'avatar': ObjectId(file_id)}})
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$push': {'previous_avatars': current_avatar}}, upsert=True)


def get_all_users():
    users = users_collection.find({})
    list_of_users = []
    for user in users:  # create a list of user objects
        if 'avatar' in user:
            this_avatar = user['avatar']
        else:
            this_avatar = None

        new_user = User(user['username'], user['email'], user['password'], this_avatar, user['real_name'], user['_id'])
        list_of_users.append(new_user)
    return list_of_users


# REQUIRES user_id, NOT username
def get_user(user_id):
    if type(user_id) == User:
        raise TypeError('Using User object instead of user_id.')

    user_id = str(user_id)  # generally redundant
    # print('DB: Attempting to fetch', user_id)

    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        pass
    try:
        some_avatar = user_data['avatar']
    except KeyError:  # user has no avatar
        some_avatar = None
    except TypeError as e:
        print('ERROR: Failed to fetch avatar for {}'.format(user_id), e)
        some_avatar = None

    # username, email, password, avatar, real_name, identifier, prev_avatars=None, date_joined=None
    return User(user_data['username'], user_data['email'], user_data['password'],
                some_avatar, user_data['real_name'], user_data['_id'],
                date_joined=user_data['date_joined']) if user_data else None


def get_messages_by_user(username):
    messages = messages_collection.find({'author': username})
    return messages


# Returns a list of room IDs for a given user
def get_rooms_for_user(user_id):
    return list(room_members_collection.find({'_id.user_id': ObjectId(user_id)}, {'_id': 1}))


# this is often used because JWT tokens are associated with usernames instead of IDs.
# Changing that would probably yield a decent speedup.
def get_user_id(username):
    some_user_id = users_collection.find_one({'username': username}, {'_id': 1})
    if some_user_id:
        return str(some_user_id['_id'])
    else:
        return None


# ROOMS


def is_room(some_id):
    query = rooms_collection.find({'_id': ObjectId(some_id)})
    if query:
        return True
    else:
        return False


def is_room_member(room_id, user_id):
    if not room_id:
        return False
    output = room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)}})
    
    if output > 0:
        return True
    else:
        return False


def room_is_mute(room_id, user_id):
    if not room_id:
        return False
    if not is_room_member(room_id, user_id):
        raise FileNotFoundError('Unauthorized')
    output = room_members_collection.find_one({'_id.user_id': ObjectId(user_id), '_id.room_id': ObjectId(room_id)},
                                              {'mute', 1})
    if not output:
        room_members_collection.update_one({'_id.user_id': ObjectId(user_id), '_id.room_id': ObjectId(room_id)},
                                           {'$set': {'mute': False}})
        return False
    else:
        return output


def toggle_mute(room_id, user_id):
    output = room_members_collection.find_one({'_id.user_id': ObjectId(user_id), '_id.room_id': ObjectId(room_id)},
                                              {'mute', 1})
    if not is_room_member(room_id, user_id):
        raise FileNotFoundError('Unauthorized')

    if not output:
        room_members_collection.update_one({'_id.user_id': ObjectId(user_id), '_id.room_id': ObjectId(room_id)},
                                           {'$set': {'mute': True}})
        return True
    else:
        toggle = not output
        room_members_collection.update_one({'_id.user_id': ObjectId(user_id), '_id.room_id': ObjectId(room_id)},
                                           {'$set': {'mute': toggle}})
        return toggle


def get_room(room_id):
    if type(room_id) == Room:
        raise TypeError('Using Room object instead of room_id.')

    room = rooms_collection.find_one({'_id': ObjectId(room_id)})
    bucket_number = get_latest_bucket_number(room_id)
    
    try:
        emoji = room['emoji']
    except KeyError as e:
        emoji = ''
    except TypeError as e:
        emoji = ''

    room_object = Room(room['name'], str(room_id), room['is_dm'], bucket_number, str(room['created_by']), emoji=emoji)
    room_object.set_messages(get_messages(str(room_id), bucket_number))  # this line may be causing issues
    return room_object


def get_room_admins(room_id):
    return room_members_collection.find({'_id.room_id': ObjectId(room_id), 'is_admin': True})


def find_dm(user_one, user_two):
    room_title = ''
    if user_one and user_two:
        if user_one.ID > user_two.ID:
            room_title = user_two.ID + user_one.ID
        else:
            room_title = user_one.ID + user_two.ID

    room = rooms_collection.find_one({'name': room_title})

    if room:
        return str(room['_id'])
    else:
        return None


def create_dm(user_one, user_two):
    room_title = ''
    if user_one == user_two:
        return None
    if user_one and user_two:
        if user_one.ID > user_two.ID:
            room_title = user_two.ID + user_one.ID
        else:
            room_title = user_one.ID + user_two.ID

    room_id = rooms_collection.insert_one(
        {'name': room_title, 'bucket_number': 0, 'is_dm': True, 'created_by': None,
         'created_at': time.time()}).inserted_id

    # room_id, room_name, user_id, added_by, is_admin=False, is_owner=False, is_dm=False
    add_room_member(room_id, room_title, str(user_one.ID), None, is_dm=True)
    add_room_member(room_id, room_title, str(user_two.ID), None, is_dm=True)

    return room_id


def save_room(room_name, created_by, emoji):
    room_id = rooms_collection.insert_one(
        {'name': room_name, 'emoji': emoji, 'is_dm': False, 'created_by': ObjectId(created_by), 'bucket_number': 0,
         'created_at': time.time()}).inserted_id
    return room_id


def update_room(room_id, itemized_room):
    for kvp in itemized_room:
        users_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {kvp[0]: kvp[1]}})


# refactor to not require room_name ?
def add_room_member(room_id, room_name, user_id, added_by, is_admin=False, is_owner=False, is_dm=False):
    room_members_collection.insert_one({'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)},
                                        'name': room_name,
                                        'added_by': ObjectId(added_by),
                                        'is_dm': is_dm,
                                        'added_at': time.time(),
                                        'is_admin': is_admin,
                                        'is_owner': is_owner})


def add_room_members(room_id, room_name, user_ids, added_by):
    room_members_collection.insert_many([{'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)},
                                          'name': room_name,
                                          'added_by': added_by,
                                          'added_at': time.time(),
                                          'is_dm': False,
                                          'is_admin': False,
                                          'is_owner': False} for user_id in user_ids])


def get_room_members(room_id):
    return list(room_members_collection.find({'_id.room_id': ObjectId(room_id)}))


def is_room_admin(room_id, user_id):
    return room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)}, 'is_admin': True})


def remove_room_members(room_id, user_ids):
    room_members_collection.delete_many(
        {'_id': {'$in': [{'room_id': room_id, 'user_id': user_id} for user_id in user_ids]}})


def toggle_admin(room_id, user_id):
    is_admin = room_members_collection.find_one({'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)}},
                                                {'is_admin': 1})['is_admin']
    # (is_admin)
    room_members_collection.update_one({'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)}},
                                       {'$set': {'is_admin': not is_admin}})
    return not is_admin


def delete_room(room_id):
    rooms_collection.delete_one({'_id': ObjectId(room_id)})
    room_members_collection.delete_many({'_id.room_id': ObjectId(room_id)})


# LOG


def add_log_event(response_code, username, event_type, context=None, ip_address=None):
    logging_collection.insert_one({'context': context, 'response': response_code, 'time': time.time(),
                                   'event': event_type, 'user': username, 'ip_address': ip_address})


# MISC


def add_reaction(message, reaction, username):
    emoji_id = ''  # = get ID from emoji collection
    reactions_collection.insert_one({'author': username, 'parent_message': message, 'reaction': emoji_id})


# MESSAGES


# turns a list (from DB) of jsons into a list of message objects
def load_messages(room_id, bucket_number):
    if type(room_id) == Room:
        raise TypeError('Using Room object instead of room_id.')

    message_bson = get_messages(room_id, bucket_number)

    messages = []
    users = {}  # for tracking users already obtained

    if message_bson and bucket_number > 0:
        for item in message_bson:
            try:
                user_id = str(item['sender'])
                if user_id not in users:
                    users[user_id] = get_user(user_id)
                # self, time_sent, text, username, user_id, avatar, image_id
                messages.append(Message(item['time_sent'], item['text'], users[user_id].username, users[user_id].ID,
                                        users[user_id].avatar, str(item['image_id'])).create_json())
            except Exception as e:
                print(e)

    return messages


def get_latest_bucket_number(room_id):
    if type(room_id) == Room:
        raise TypeError('Using Room object instead of room_id.')

    try:
        # finds the latest bucket in the messages collection
        latest_bucket = list(messages_collection.find({'room_id': ObjectId(room_id)}).sort('_id', -1).limit(1))[0]
    except Exception as e:
        latest_bucket = None

    if not latest_bucket:  # no buckets
        latest_bucket_number = 0
    else:
        latest_bucket_number = int(latest_bucket['bucket_number'])

    print('Get latest bucket number', room_id, latest_bucket_number)

    return latest_bucket_number


def save_message(room_id, text, user_id, image_id=None):
    if type(room_id) == Room:
        raise TypeError('Using Room object instead of room_id.')
    if type(user_id) == User:
        raise TypeError('Using User object instead of user_id.')

    current_time = time.time()
    print('DB: SAVE_MESSAGE', room_id, text, user_id, current_time)

    if image_id:
        image_field = ObjectId(image_id)
    else:
        image_field = None

    user_object = get_user(user_id)
    new_message = Message(current_time, text, username=user_object.username, user_id=user_id, avatar=user_object.avatar, image_id=image_field)

    bucket_number = get_latest_bucket_number(room_id)  # return 0 if no buckets
    messages = get_messages(room_id, bucket_number)  # return null if bucket_number == 0

    if not messages:
        new_message_list = [new_message.create_json()]

        bucket_number += 1
        new_bucket = {
            'room_id': ObjectId(room_id),
            'bucket_number': bucket_number,
            'messages': new_message_list
        }
        messages_collection.insert_one(new_bucket)

        return bucket_number

    if len(messages) < 50:
        messages_collection.update_one({'room_id': ObjectId(room_id), 'bucket_number': bucket_number},
                                       {'$push': {'messages': new_message.create_json()}})
    else:  # need a new bucket
        new_message_list = [new_message.create_json()]

        bucket_number += 1
        new_bucket = {
            'room_id': ObjectId(room_id),
            'bucket_number': bucket_number,
            'messages': new_message_list
        }
        messages_collection.insert_one(new_bucket)

    return bucket_number


def get_messages(room_id, bucket_number=0):
    if type(room_id) == Room:
        raise TypeError('Using Room object instead of room_id.')

    if bucket_number == 0:
        return None

    try: 
        messages = messages_collection.find_one({'room_id': ObjectId(room_id), 'bucket_number': bucket_number})['messages']
        print('get_messages', room_id, bucket_number, messages)
    except KeyError as e:
        messages = None
    except TypeError as e:
        print(messages_collection.find_one({'room_id': ObjectId(room_id), 'bucket_number': bucket_number}))
        print('TYPE ERROR')
        return [room_id, bucket_number, 'AHHH']

    print('get_messages', room_id, bucket_number)

    if messages:
        return messages
    else:
        return []


def add_reaction(message_id, user_id, reaction_id):
    now = time.time()
    reaction_array = messages_collection.find_one({'_id': ObjectId(message_id)}, {'reactions': 1})
    reaction_object_id = reactions_collection.insert_one({
        'user_id': ObjectId(user_id),
        'reaction_id': reaction_id,
        'time_inserted': now,
        'message_id': message_id}).inserted_id
    username = get_user(user_id)['username']
    reaction_array.append({
        'reaction_object_id': reaction_object_id,
        'user_id': ObjectId(user_id),
        'username': username
    })
    messages_collection.update_one({'_id': ObjectId(message_id)}, {'$set': {'reactions': reaction_array}})


# IMAGES and UPLOADS


def save_image(sender, room_id, is_avatar):
    current_time = time.time()
    image_id = images_collection.insert_one({'room_id': room_id, 'avatar': is_avatar, 'location': None,
                                             'author': ObjectId(sender), 'time_sent': current_time}).inserted_id
    images_collection.update_one({'_id': ObjectId(str(image_id))}, {'$set': {'location': str(image_id)}})
    return str(image_id)


def locate_image(image_id):
    return images_collection.find_one({'_id': ObjectId(image_id)})
