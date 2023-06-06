from flask import Flask, request
import pymongo
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
    token = userDocument['token']
    print("Logged user:", token)
    return {
        "success": True,
        "token": str(token),
    }


@app.route("/registry", methods=["POST"])
def registry():
    body_registry = request.json
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
    print('generated token:', body_registry['token'])
    return {
        "success": True,
        "token": str(token),
    }


@app.route("/avatars", methods=["GET"])
def findAvatars():
    token = request.headers.get('Token')
    user = db.users.find_one({'token': token})
    if user == None:
        return {
            "success": False,
            "error": "invalid token",
        }
    avatars = db.avatars.find()

    return {
        "success": True,
        "avatars": json.loads(json_util.dumps(avatars)),
        "userDocument": json.loads(json_util.dumps(user)),
        "Token": str(token)
    }


@app.route("/avatarSelected", methods=["POST"])
def avatarSelected():
    body = request.json
    token = body.get("token")
    avatar = body.get("selectedAvatar")
    user = db.users.find_one({"token": token})

    # Compruebo que el token coincida
    if str(user["token"]) != token:
        return {
            "success": False,
            "message": "Invalid token",
        }

    # Agrega el avatar selecionado al objeto usuario.
    user["avatar"] = avatar
    # Actualiza el documento del usuario con la nueva lista de avatar
    db.users.update_one({"_id": user["_id"]}, {
                        "$set": {"avatar": user["avatar"]}})
    return {
        "success": True,
        "token": str(token),
    }


@app.route("/pokemons", methods=["GET"])
def get_pokemons():
    # Buscamos los elementos y organizamos en orden ascendiente por la clave "number" al contrario: DESCENDING
    pokemons = db.pokemons.find({"main": True}).sort(
        "number", pymongo.ASCENDING)
    return {
        "success": True,
        "pokemons": json.loads(json_util.dumps(pokemons)),
    }


@app.route("/userPokemon", methods=["GET"])
def get_UserPokemon():
    userPokemon = db.pokemons.find_one({"main": False, "owner": "user_id"})
    print(userPokemon)
    return {
        "success": True,
        "userPokemon": json.loads(json_util.dumps(userPokemon)),
    }


@app.route("/collected", methods=["POST"])
def saveCollected():
    body_Collected = request.json
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
