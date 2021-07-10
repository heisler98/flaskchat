# github.com/colingoodman

from datetime import datetime
# from bson import ObjectId
import bson
from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash

from model.user import User

client = MongoClient(
    'mongodb+srv://user:SecurePassword@cluster0.ojjqo.mongodb.net/<dbname>?retryWrites=true&w=majority')

chat_db = client.get_database('ChatDB')
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
    existing_username = users_collection.find_one({'username': username}, {'username': 1})
    if existing_username:
        raise DuplicateKeyError('Username already exists.')

    now = datetime.now()
    password_hash = generate_password_hash(password)
    identifier = users_collection.insert_one({'username': username, 'email': email, 'password': password_hash,
                                              'real_name': fullname, 'date_joined': now, 'avatar': None}).inserted_id

    return identifier


def store_apn(user_id, token):
    apn_tokens = users_collection.find_one({'_id': ObjectId(user_id)}, {'apn': 1})
    if type(apn_tokens) == dict:
        return None
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


def get_apn(user_id):
    apn_tokens = users_collection.find_one({'_id': ObjectId(user_id)}, {'apn': 1})
    if not apn_tokens:
        return None
    return apn_tokens


def update_checkout(user_id):
    now = datetime.now()
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'last_online': now}})


# used for admin / super user purposes
def crown_user(username, status=True):
    users_collection.update_one({'username': username}, {'$set': {'god': status}})


def change_user_password(username, new_password):
    password_hash = generate_password_hash(new_password)
    now = datetime.now()
    users_collection.update_one({'username': username}, {'$set': {'password': password_hash}})


def change_user_attribute(username, attribute_type, value):
    users_collection.update_one({'username': username}, {'$set': {attribute_type: value}})


def change_user_avatar(user_id, file_id):
    current_avatar = users_collection.find_one({'_id': ObjectId(user_id)}, {'avatar': 1})
    previous_avatars = users_collection.find_one({'_id': ObjectId(user_id)}, {'previous_avatars': 1})

    #users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'previous_avatars': previous_avatars}})
    users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'avatar': file_id}})

    return None

    if previous_avatars:  # if this attr exists
        previous_avatars.append(current_avatar) # does not have append
        # users_collection.update_one({'username': username}, {'$set': {'previous_avatars': previous_avatars}})
    elif current_avatar:  # there are no previous avatars but there is a current one
        previous_avatars = [current_avatar]
        # users_collection.update_one({'username': username}, {'$set': {'previous_avatars': previous_avatars}})
    else:  # there are no previous or current avatars
        previous_avatars = []


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


def get_user(user_id):
    if not user_id:
        raise TypeError

    user_id = str(user_id)  # generally redundant
    print('DB: Attempting to fetch', user_id)

    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        print('DB: Fetched', user_id, '({})'.format(user_data['username']))
    try:
        some_avatar = user_data['avatar']
    except KeyError:  # user has no avatar
        some_avatar = None
    except TypeError as e:
        print('ERROR: Failed to fetch avatar for {}'.format(user_id), e)
        some_avatar = None

    return User(user_data['username'], user_data['email'], user_data['password'],
                some_avatar, user_data['real_name'], user_data['_id']) if user_data else None


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


def is_room_member(room_id, user_id):
    if not room_id:
        return False
    output = room_members_collection.count_documents({'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)}})
    return output


def get_room(room_id):
    return rooms_collection.find_one({'_id': ObjectId(room_id)})


def find_dm(user_one, user_two):
    room_title = ''
    if user_one and user_two:
        if user_one.username > user_two.username:
            room_title = user_two.username + user_one.username
        else:
            room_title = user_one.username + user_two.username

    room = rooms_collection.find_one({'name': room_title})

    if room:
        return str(room['_id'])
    else:
        return None


def create_dm(user_one, user_two):
    room_title = ''
    if user_one and user_two:
        if user_one.username > user_two.username:
            room_title = user_two.username + user_one.username
        else:
            room_title = user_one.username + user_two.username

    room_id = rooms_collection.insert_one(
        {'name': room_title, 'is_dm': True, 'created_by': None, 'created_at': datetime.now()}).inserted_id

    # room_id, room_name, user_id, added_by, is_admin=False, is_owner=False, is_dm=False
    add_room_member(room_id, room_title, str(user_one.ID), None, is_dm=True)
    add_room_member(room_id, room_title, str(user_two.ID), None, is_dm=True)

    return room_id


def save_room(room_name, created_by):
    room_id = rooms_collection.insert_one(
        {'name': room_name, 'is_dm': False, 'created_by': ObjectId(created_by),
         'created_at': datetime.now()}).inserted_id
    return room_id


def update_room(room_id, attribute_type, value):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {attribute_type: value}})
    # room_members_collection.update_many({'_id.room_id': ObjectId(room_id)}, {'$set': {'name': room_name}})


def add_room_member(room_id, room_name, user_id, added_by, is_admin=False, is_owner=False, is_dm=False):
    room_members_collection.insert_one({'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)},
                                        'name': room_name,
                                        'added_by': ObjectId(added_by),
                                        'is_dm': is_dm,
                                        'added_at': datetime.now(),
                                        'is_admin': is_admin,
                                        'is_owner': is_owner})


def add_room_members(room_id, room_name, user_ids, added_by):
    room_members_collection.insert_many([{'_id': {'room_id': ObjectId(room_id), 'user_id': ObjectId(user_id)},
                                          'name': room_name,
                                          'added_by': added_by,
                                          'added_at': datetime.now(),
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
    logging_collection.insert_one({'context': context, 'response': response_code, 'time': datetime.now(),
                                   'event': event_type, 'user': username, 'ip_address': ip_address})


# MISC


def add_reaction(message, reaction, username):
    emoji_id = ''  # = get ID from emoji collection
    reactions_collection.insert_one({'author': username, 'parent_message': message, 'reaction': emoji_id})


# MESSAGES


def save_message(room_id, text, sender, include_image, image_id):
    current_time = datetime.now()
    if include_image and image_id:
        messages_collection.insert_one({'room_id': ObjectId(room_id), 'text': text, 'sender': ObjectId(sender),
                                        'time_sent': current_time, 'include_image': True,
                                        'image_id': ObjectId(image_id)})
    else:
        messages_collection.insert_one({'room_id': ObjectId(room_id), 'text': text, 'sender': ObjectId(sender),
                                        'time_sent': current_time, 'include_image': False,
                                        'image_id': None})


def get_messages(room_id, page=0):
    MESSAGE_FETCH_LIMIT = 50
    offset = page * MESSAGE_FETCH_LIMIT
    messages = list(
        messages_collection.find({'room_id': ObjectId(room_id)}).sort('_id', DESCENDING).limit(MESSAGE_FETCH_LIMIT).skip(offset))
    for message in messages:
        message['time_sent'] = message['time_sent']
    return messages[::-1]


def add_reaction(message_id, user_id, reaction_id):
    now = datetime.now()
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


def save_image(sender, room_id, path, is_avatar):
    current_time = datetime.now()
    image_id = images_collection.insert_one({'room_id': room_id, 'avatar': is_avatar, 'location': path,
                                             'author': ObjectId(sender), 'time_sent': current_time}).inserted_id
    return image_id


def locate_image(image_id):
    return images_collection.find_one({'_id': ObjectId(image_id)})
