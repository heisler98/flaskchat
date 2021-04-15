# github.com/colingoodman

from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, DESCENDING, ASCENDING
from werkzeug.security import generate_password_hash

from user import User

client = MongoClient(
    'mongodb+srv://user:SecurePassword@cluster0.ojjqo.mongodb.net/<dbname>?retryWrites=true&w=majority')

chat_db = client.get_database('ChatDB')
users_collection = chat_db.get_collection('users')
rooms_collection = chat_db.get_collection('rooms')
room_members_collection = chat_db.get_collection('room_members')
messages_collection = chat_db.get_collection('messages')
images_collection = chat_db.get_collection('images')


def save_user(username, email, password):
    password_hash = generate_password_hash(password)
    users_collection.insert_one({'_id': username, 'email': email, 'password': password_hash})

    target_room = 'garbage'
    target_room_id = get_room_id(target_room)
    add_room_member(target_room_id, target_room, username, None, is_admin=False, is_dm=False)


def update_user(username, email):
    users_collection.update_one({'_id': username}, {'_id': username, 'email': email})
    return username


def get_user(username):
    user_data = users_collection.find_one({'_id': username})
    try:
        some_path = user_data['avatar']
    except:
        some_path = 'uploads/squid.png'
    return User(user_data['_id'], user_data['email'], user_data['password'], some_path) if user_data else None


def find_dm(user_one, user_two):
    room_title = ''
    if user_one and user_two:
        if user_one.username[0] > user_two.username[0]:
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
        if user_one.username[0] > user_two.username[0]:
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
    add_room_member(room_id, room_name, created_by, created_by, is_dm=False, is_admin=True)
    return room_id


def add_room_member(room_id, room_name, username, added_by, is_dm, is_admin=False):
    room_members_collection.insert_one({'_id': {'room_id': ObjectId(room_id), 'username': username},
                                        'name': room_name,
                                        'added_by': added_by,
                                        'is_dm': is_dm,
                                        'added_at': datetime.now(),
                                        'is_room_admin': is_admin})


def get_all_users():
    return users_collection.find({})


def find_room_with_two():
    return room_members_collection.find({})


def add_room_members(room_id, room_name, usernames, added_by, is_dm):
    room_members_collection.insert_many([{'_id': {'room_id': ObjectId(room_id), 'username': username},
                                          'name': room_name,
                                          'is_dm': is_dm,
                                          'added_by': added_by,
                                          'added_at': datetime.now(),
                                          'is_room_admin': False} for username in usernames])


def get_room_id(room_name):
    target = rooms_collection.find_one({'name': room_name})

    if target:
        return target['_id']
    else:
        return None


def get_room(room_id):
    try:
        return rooms_collection.find_one({'_id': ObjectId(room_id)})
    except Exception as e:
        raise Exception(room_id, e)


def update_room(room_id, room_name):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'name': room_name}})
    room_members_collection.update_many({'_id.room_id': ObjectId(room_id)}, {'$set': {'name': room_name}})


def get_room_members(room_id):
    return list(room_members_collection.find({'_id.room_id': ObjectId(room_id)}))


def remove_room_members(room_id, usernames):
    room_members_collection.delete_many(
        {'_id': {'$in': [{'room_id': room_id, 'username': username} for username in usernames]}})


def get_rooms_for_user(username):
    return list(room_members_collection.find({'_id.username': username}))


def is_room_member(room_id, username):
    output = room_members_collection.count_documents({'_id': {'room_id': ObjectId(room_id), 'username': username}})
    print('is_room_member', output)
    return output


def is_room_admin(room_id, username):
    return room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'is_room_admin': True})


def save_message(room_id, text, sender, is_image):
    current_time = datetime.now()
    messages_collection.insert_one({'room_id': room_id, 'text': text, 'sender': sender, 'time_sent': current_time,
                                    'is_image': is_image})


def save_avatar(user_id, path):
    current_time = datetime.now()
    current_avatar = images_collection.find_one({'avatar': True, 'author': user_id})
    if current_avatar:  # if user already has an avatar, update existing record
        images_collection.replace_one({'avatar': True, 'author': user_id}, {'room_id': None, 'avatar': True,
                                                                            'location': path, 'author': user_id,
                                                                            'time_sent': current_time})
    else:
        images_collection.insert_one({'room_id': None, 'avatar': True, 'location': path, 'author': user_id,
                                      'time_sent': current_time})
    users_collection.update_one({'_id': user_id}, {"$set": {"avatar": path}}, True)


def save_image(sender, room_id, path):
    current_time = datetime.now()
    image_id = images_collection.insert_one({'room_id': room_id, 'avatar': False, 'location': path,
                                             'author': sender, 'time_sent': current_time}).inserted_id
    return image_id


def locate_image(image_id):
    return images_collection.find_one({'_id': ObjectId(image_id)})


def get_avatar(user_id):
    return images_collection.find_one({'avatar': True, 'author': user_id})


def get_images_from_user(username):
    return images_collection.find({'author': username})


MESSAGE_FETCH_LIMIT = 30


def get_messages(room_id, page=0):
    offset = page * MESSAGE_FETCH_LIMIT
    messages = list(
        messages_collection.find({'room_id': room_id}).sort('_id', DESCENDING).limit(MESSAGE_FETCH_LIMIT).skip(offset))
    for message in messages:
        message['time_sent'] = message['time_sent'].strftime("%b %d, %H:%M")
    return messages[::-1]
