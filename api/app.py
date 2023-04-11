from flask import Flask, render_template, request, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson import json_util
import json
from datetime import datetime
from dotenv import dotenv_values
env = dotenv_values(".env")

app = Flask(__name__, static_url_path='', static_folder='public')
app.secret_key = env['FLASK_SECRET_KEY']
client = MongoClient(env['MONGO_DB_URI'])
db = client.pokedex


@app.route("/login", methods=["POST"])
def login():
    body = request.json
    userDocument = db.users.find_one({'user': body['user']})
#    {'$or': [{'email': body['email']}, {'user': body['user']}]})
    # body['user'] era el antiguo request.args.email
    if body['user'] == "" or body['pass'] == "" or body['pass'] != userDocument['pass']:
        return {
            "success": False
        }
    print(userDocument)
    return {
        "success": True,
        "token": body['user'],
    }


@app.route("/registry", methods=["POST"])
def registry():
    body_registry = request.json
    print(body_registry)

    if body_registry['user'] == "" or body_registry['email'] == "" or body_registry['pass'] == "" or len(body_registry['user']) < 4 or len(body_registry['user']) < 5:
        return {
            "success": False
        }
    #emailSplitted = body_registry['email'].split('@')
    # if len(emailSplitted) != 2 or emailSplitted[1] != 'gmail.com' != 'hotmail.com':
        # return {
       #     "success": False,
       #     "error": True,
       # }
    time = datetime.now()
    body_registry['user_created'] = time.strftime('%d-%m-%Y, %H:%M:%S')

    db.users.insert_one(body_registry)
    return {
        "success": True,
        "token": body_registry['user'],
    }


@app.route("/favorites", methods=["POST"])
def saveFavorites():
    body_Favorites = request.json
    print({"body_Favorites": body_Favorites})
    db.favorites.insert_one(body_Favorites)
    return {
        "success": True,
    }


@app.route("/favorites", methods=["GET"])
def findFavorites():
    favorites = db.favorites.find()
    return {
        "success": True,
        "favorites": json.loads(json_util.dumps(favorites))
    }


@app.route("/favorites", methods=["DELETE"])
def deleteFavorites():
    body_Favorites = request.json
    db.favorites.delete_many(body_Favorites)
    return {
        "success": True,
        "favorites": json.loads(json_util.dumps(body_Favorites))
    }
