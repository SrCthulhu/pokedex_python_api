from flask import Flask, request
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import json_util
import json
from datetime import datetime, timedelta
from jose import jwt
from dotenv import dotenv_values
env = dotenv_values(".env")

app = Flask(__name__, static_url_path='', static_folder='public')
app.secret_key = env['FLASK_SECRET_KEY']
client = MongoClient(env['MONGO_DB_URI'])
db = client.pokedex
token_secret = env['TOKEN_SECRET_KEY']


@app.route("/login", methods=["POST"])
def login():
    body = request.json
    userDocument = db.users.find_one(
        {'$or': [{'user': body['user']}, {'email': body['user'].lower()}]})
    if userDocument == None:
        return {
            "success": False
        }
    if body['user'] == "" or body['pass'] == "" or body['pass'] != userDocument['pass']:
        return {
            "success": False
        }
    token_payload = {
        'user_id': str(userDocument['_id']),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(
        token_payload, env['TOKEN_SECRET_KEY'], algorithm='HS256')
    return {
        "success": True,
        "token": str(token),
    }


@app.route("/registry", methods=["POST"])
def registry():
    body_registry = request.json
    print(body_registry)

    if body_registry['user'] == "" or body_registry['email'] == "" or body_registry['pass'] == "" or len(body_registry['user']) < 3 or len(body_registry['pass']) < 5:
        return {
            "success": False
        }

    if not body_registry['email'].endswith('.com') or "@" not in body_registry['email']:
        return {
            "success": False,
            "error1": True
        }
    if body_registry['pass'] != body_registry['validatePass']:
        return {
            "success": False,
            "error2": True
        }
    time = datetime.now()
    body_registry['user_created'] = time.strftime('%d-%m-%Y, %H:%M:%S')

    generateToken = {
        'user_name': str(body_registry['user']),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(
        generateToken, env['TOKEN_SECRET_KEY'], algorithm='HS256')

    # Agregamos el nuevo campo token a nuestro documento de usuario.
    body_registry['token'] = str(token)

    db.users.insert_one(body_registry)

    return {
        "success": True,
        "token": str(token),
    }


@app.route("/avatars", methods=["GET"])
def findAvatars():
    avatars = db.avatars.find()
    return {
        "success": True,
        "avatars": json.loads(json_util.dumps(avatars))
    }


@app.route("/avatarSelected", methods=["POST"])
def avatarSelected():
    body = request.json
    token = body.get("accessToken")
    avatar = body.get("avatar")

    # Busco el usuario usando el token
    user = db.users.find_one({"token": token})

    if user is None:
        return {
            "success": False,
            "message": "User not found",
        }

    # Agrega el avatar selecionado a la lista de avatars del usuario.
    avatars = user.get("avatar", [])
    avatars.append(avatar)

    # Actualiza el documento del usuario con la nueva lista de avatar
    db.users.update_one({"_id": user["_id"]}, {"$set": {"avatar": avatars}})

    return {
        "success": True,
        "token": str(token),
    }


@app.route("/collected", methods=["POST"])
def saveCollected():
    body_Collected = request.json
    print({"body_Collected": body_Collected})
    db.collection.insert_one(body_Collected)
    return {
        "success": True,
    }


@app.route("/collected", methods=["GET"])
def findCollected():
    collected = db.collection.find()
    return {
        "success": True,
        "collected": json.loads(json_util.dumps(collected))
    }


@app.route("/collected", methods=["DELETE"])
def deleteCollected():
    body_Collected = request.json
    db.collection.delete_many(body_Collected)
    return {
        "success": True,
        "collected": json.loads(json_util.dumps(body_Collected))
    }
