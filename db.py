# github.com/colingoodman

from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, DESCENDING
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

def save_user(username, email, password, fullname):
    password_hash = generate_password_hash(password)
    now = datetime.now()
    identifier = hash(username)
    users_collection.insert_one({'_id': identifier, 'username': username, 'email': email, 'password': password_hash,
                                 'realname': fullname, 'date_joined': now})


def add_twitter_handle(username, handle):
    now = datetime.now()
    users_collection.update_one({'username': username}, {'$set': {'twitter': handle}})  # {'$set': {'name': room_name}}


def change_user_password(username, new_password):
    password_hash = generate_password_hash(new_password)
    now = datetime.now()
    users_collection.update_one({'username': username}, {'$set': {'password': password_hash}})


def change_user_realname(username, realname):
    now = datetime.now()
    users_collection.update_one({'username': username}, {'$set': {'realname': realname}})


def change_user_avatar(username, file_id):
    now = datetime.now()
    users_collection.update_one({'username': username}, {'$set': {'avatar': file_id}})


def get_all_users():
    users = users_collection.find({})
    list_of_users = []
    for user in users:
        list_of_users.append(user)
    return list_of_users


def get_user(user_id):
    if not user_id:
        raise TypeError

    user_id = int(user_id)
    print('DB: Attempting to fetch', user_id)

    user_data = users_collection.find_one({'_id': user_id})
    if user_data:
        print('DB: Fetched', user_id, '({})'.format(user_data['username']))
    try:
        some_avatar = user_data['avatar']
    except KeyError as e:
        some_avatar = None

    return User(user_data['username'], user_data['email'], user_data['password'],
                some_avatar, user_data['realname'], user_data['_id']) if user_data else None


def get_messages_by_user(username):
    messages = messages_collection.find({'author': username})
    return messages


# Returns a list of room IDs for a given user
def get_rooms_for_user(username):
    return list(room_members_collection.find({'_id.username': username}, {'_id': 1}))


def get_user_id(username):
    some_user_id = users_collection.find_one({'username': username}, {'_id': 1})
    if some_user_id:
        return some_user_id['_id']
    else:
        return None

# ROOMS


def is_room_member(room_id, username):
    output = room_members_collection.count_documents({'_id': {'room_id': ObjectId(room_id), 'username': username}})
    print('is_room_member', output)
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
        return room['_id']
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

    add_room_member(room_id, room_title, user_one.username, None, is_dm=True, is_admin=False)
    add_room_member(room_id, room_title, user_two.username, None, is_dm=True, is_admin=False)

    return room_id


def save_room(room_name, created_by):
    room_id = rooms_collection.insert_one(
        {'name': room_name, 'is_dm': False, 'created_by': created_by, 'created_at': datetime.now()}).inserted_id
    return room_id


def update_room(room_id, room_name):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'name': room_name}})
    room_members_collection.update_many({'_id.room_id': ObjectId(room_id)}, {'$set': {'name': room_name}})


def add_room_member(room_id, room_name, username, added_by, is_admin=False):
    room_members_collection.insert_one({'_id': {'room_id': ObjectId(room_id), 'username': username},
                                        'name': room_name,
                                        'added_by': added_by,
                                        'added_at': datetime.now(),
                                        'is_room_admin': is_admin})


def add_room_members(room_id, room_name, usernames, added_by):
    room_members_collection.insert_many([{'_id': {'room_id': ObjectId(room_id), 'username': username},
                                          'name': room_name,
                                          'added_by': added_by,
                                          'added_at': datetime.now(),
                                          'is_room_admin': False} for username in usernames])


def get_room_members(room_id):
    return list(room_members_collection.find({'_id.room_id': ObjectId(room_id)}))


def is_room_admin(room_id, username):
    return room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'is_room_admin': True})


def remove_room_members(room_id, usernames):
    room_members_collection.delete_many(
        {'_id': {'$in': [{'room_id': room_id, 'username': username} for username in usernames]}})

# LOG


def add_log_event(event_message, username):
    logging_collection.insert_one({'content': event_message, 'time': datetime.now(), 'user': username})

# MISC


def add_reaction(message, reaction, username):
    emoji_id = '' # = get ID from emoji collection
    reactions_collection.insert_one({'author': username, 'parent_message': message, 'reaction': emoji_id})

# MESSAGES


def save_message(room_id, text, sender, is_image, image_id):
    current_time = datetime.now()
    messages_collection.insert_one({'room_id': room_id, 'text': text, 'sender': sender, 'time_sent': current_time,
                                    'is_image': is_image, 'image': image_id})


def get_messages(room_id, page=0):
    MESSAGE_FETCH_LIMIT = 50
    offset = page * MESSAGE_FETCH_LIMIT
    messages = list(
        messages_collection.find({'room_id': room_id}).sort('_id', DESCENDING).limit(MESSAGE_FETCH_LIMIT).skip(offset))
    for message in messages:
        message['time_sent'] = message['time_sent'].strftime("%H:%M")
    return messages[::-1]

# IMAGES and UPLOADS


def save_image(sender, room_id, path, is_avatar):
    current_time = datetime.now()
    image_id = images_collection.insert_one({'room_id': room_id, 'avatar': is_avatar, 'location': path,
                                             'author': sender, 'time_sent': current_time}).inserted_id
    return image_id


def locate_image(image_id):
    return images_collection.find_one({'_id': ObjectId(image_id)})

