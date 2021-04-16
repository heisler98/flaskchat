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
direct_message_collection = chat_db.get_collection('dm_rooms')


def get_dm(user_one, user_two):
    room_title = ''
    if len(user_one) > 0 and len(user_two) > 0:
        if user_one[0] > user_two[0]:
            room_title = user_two.username + user_one.username
        else:
            room_title = user_one.username + user_two.username
    return direct_message_collection.find({'_id': room_title})


def create_dm_pair(user_one, user_two):
    room_title = ''
    if len(user_one) > 0 and len(user_two) > 0:
        if user_one[0] > user_two[0]:
            room_title = user_two.username + user_one.username
        else:
            room_title = user_one.username + user_two.username
    direct_message_collection.insert_one({'_id': room_title})
    print('creating direct message pair between', user_one, user_two)


def save_user(username, email, password):
    password_hash = generate_password_hash(password)
    current_user = users_collection.values.count({"username": username})
    user_data = users_collection.find_one({'username': username})

    print(type(user_data))
    print(user_data)

    if user_data:
        raise DuplicateKeyError('User already exists.')

    identifier = hash(username)
    users_collection.insert_one({'_id': identifier,
                                 'name_first': '',
                                 'name_last': '',
                                 'username': username,
                                 'email': email,
                                 'password': password_hash})


def get_all_users():
    users = users_collection.find({})
    list_of_users = []
    for user in users:
        list_of_users.append(user)
    return list_of_users


def get_user(username):
    print('Attempting to fetch', username)
    user_data = users_collection.find_one({'_id': username})
    return User(user_data['_id'], user_data['email'], user_data['password']) if user_data else None


def save_room(room_name, created_by):
    room_id = rooms_collection.insert_one(
        {'name': room_name, 'created_by': created_by, 'created_at': datetime.now()}).inserted_id
    return room_id


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


def get_room(room_id):
    return rooms_collection.find_one({'_id': ObjectId(room_id)})


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


def save_message(room_id, text, sender):
    current_time = datetime.now()
    messages_collection.insert_one({'room_id': room_id, 'text': text, 'sender': sender, 'time_sent': current_time})


MESSAGE_FETCH_LIMIT = 50


def get_messages(room_id, page=0):
    offset = page * MESSAGE_FETCH_LIMIT
    messages = list(
        messages_collection.find({'room_id': room_id}).sort('_id', DESCENDING).limit(MESSAGE_FETCH_LIMIT).skip(offset))
    for message in messages:
        message['time_sent'] = message['time_sent'].strftime("%H:%M")
    return messages[::-1]
