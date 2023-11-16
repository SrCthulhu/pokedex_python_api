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

app = Flask(__name__, static_url_path="", static_folder="public")
app.secret_key = env["FLASK_SECRET_KEY"]
client = MongoClient(env["MONGO_DB_URI"])
db = client.pokedex
token_secret = env["TOKEN_SECRET_KEY"]


def get_user_from_token(token):
    print("Decoding Token:", token)
    try:
        decoded_token = jwt.decode(token, token_secret, algorithms=["HS256"])
        user_name = decoded_token.get("user_name")
        user = db.users.find_one({"user": user_name})
        return user
    except Exception as e:
        print("Error decoding token:", str(e))
        return None


@app.route("/login", methods=["POST"])
def login():
    body = request.json
    userDocument = db.users.find_one(
        {"$or": [{"user": body["user"]}, {"email": body["user"].lower()}]}
    )
    if userDocument == None:
        return {"success": False}
    if body["user"] == "" or body["pass"] == "" or body["pass"] != userDocument["pass"]:
        return {"success": False}
    generateToken = {"user_name": str(userDocument["user"])}
    token = jwt.encode(generateToken, env["TOKEN_SECRET_KEY"], algorithm="HS256")
    print("Logged user:", token)
    db.users.update_one({"_id": userDocument["_id"]}, {"$set": {"token": token}})
    return {
        "success": True,
        "token": str(token),
    }


@app.route("/registry", methods=["POST"])
def registry():
    body_registry = request.json
    if (
        body_registry["user"] == ""
        or body_registry["email"] == ""
        or body_registry["pass"] == ""
        or len(body_registry["user"]) < 3
        or len(body_registry["pass"]) < 5
    ):
        return {"success": False}

    if not body_registry["email"].endswith(".com") or "@" not in body_registry["email"]:
        return {"success": False, "error1": True}
    if body_registry["pass"] != body_registry["validatePass"]:
        return {"success": False, "error2": True}
    time = datetime.now()
    body_registry["user_created"] = time.strftime("%d-%m-%Y, %H:%M:%S")

    generateToken = {"user_name": str(body_registry["user"])}
    token = jwt.encode(generateToken, env["TOKEN_SECRET_KEY"], algorithm="HS256")

    # Agregamos el nuevo campo token a nuestro documento de usuario.
    body_registry["token"] = str(token)
    db.users.insert_one(body_registry)
    print("generated token:", body_registry["token"])
    return {
        "success": True,
        "token": str(token),
    }


@app.route("/avatars", methods=["GET"])
def findAvatars():
    token = request.headers.get("token")
    print("tok:", token)
    user = get_user_from_token(token)
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
        "token": str(token),
    }


@app.route("/avatarSelected", methods=["POST"])
def avatarSelected():
    body = request.json
    token = body.get("token")
    avatar = body.get("selectedAvatar")
    user = get_user_from_token(token)

    # Compruebo que el token coincida
    if str(user["token"]) != token:
        return {
            "success": False,
            "message": "Invalid token",
        }

    # Agrega el avatar selecionado al objeto usuario.
    user["avatar"] = avatar
    # Actualiza el documento del usuario con la nueva lista de avatar
    db.users.update_one({"_id": user["_id"]}, {"$set": {"avatar": user["avatar"]}})
    return {
        "success": True,
        "token": str(token),
    }


@app.route("/initial/pokemons", methods=["GET"])
def get_initial():
    token = request.headers.get("token")
    pokemon = db.pokemons.find({"main": False})
    return {
        "success": True,
        "pokemon": json.loads(json_util.dumps(pokemon)),
        "token": str(token),
    }


@app.route("/collected", methods=["POST"])
def saveCollected():
    token = request.headers.get("token")
    print("Token in server side:", token)
    user = get_user_from_token(token)
    print("User:", user)

    if not user:
        return {
            "success": False,
            "error": "Invalid token",
        }

    body_Collected = request.json
    # Agregamos el campo owner al pokemon
    body_Collected["owner"] = str(user["_id"])
    body_Collected["in_use"] = True
    db.collection.insert_one(body_Collected)
    return {
        "success": True,
    }


@app.route("/pokemons", methods=["GET"])
def get_pokemons():
    # Buscamos los elementos y organizamos en orden ascendiente por la clave "number" al contrario: DESCENDING
    pokemons = db.pokemons.find({"main": True}).sort("number", pymongo.ASCENDING)
    return {
        "success": True,
        "pokemons": json.loads(json_util.dumps(pokemons)),
    }


@app.route("/userPokemon", methods=["GET"])
def get_UserPokemon():
    token = request.headers.get("token")
    user = get_user_from_token(token)
    userPokemon = db.collection.find_one(
        {"main": False, "owner": str(user["_id"]), "in_use": True}
    )
    return {
        "success": True,
        "userPokemon": json.loads(json_util.dumps(userPokemon)),
    }


@app.route("/startCombat", methods=["POST"])
def start_Combat():
    token = request.headers.get("token")
    body = request.json
    userPokemon = body["userPokemon"]["_id"]["$oid"]
    # Extraemos el id.
    lastWon = body["lastWon"] + 1
    # El (+ 1) representa sumarle uno al index[0] ya que la clave de pokemons "number" no tiene valor 0 sino que empieza en 1.
    enemyPokemon = db.pokemons.find_one({"number": lastWon})
    newCombatDocument = {
        "status": "active",
        "user_poke_id": str(userPokemon),
        "enemy_poke_id": str(enemyPokemon["_id"]),
        "token": token,
    }
    db.combats.insert_one(newCombatDocument)
    return {
        "success": True,
    }


@app.route("/findFighters", methods=["GET"])
def get_Fighters():
    token = request.headers.get("token")
    actualCombat = db.combats.find_one({"token": token})
    userPokemon = db.collection.find_one(
        {"_id": ObjectId(str(actualCombat["user_poke_id"]))}
    )
    enemyPokemon = db.pokemons.find_one(
        {"_id": ObjectId(str(actualCombat["enemy_poke_id"]))}
    )
    enemy_abilities = {
        "ability": enemyPokemon.get("ability", ""),
        "hidden_ability": enemyPokemon.get("hidden_ability", ""),
    }
    return {
        "success": True,
        "userPokemon": json.loads(json_util.dumps(userPokemon)),
        "enemyPokemon": json.loads(json_util.dumps(enemyPokemon)),
        "enemyAbilities": enemy_abilities,  # Incluir habilidades en la respuesta
        "token": token,
        "actualCombat": str(actualCombat["_id"]),
    }


@app.route("/messages", methods=["POST"])
def send_messages():
    token = request.headers.get("token")
    body = request.json
    combat_Id = body.get("combat_Id")
    message = body.get("message")
    user = get_user_from_token(token)

    if not user:
        return {
            "success": False,
            "error": "Invalid token",
        }
    if message:
        db.messages.insert_one(
            {"combat_Id": combat_Id, "user": str(user["_id"]), "message": message}
        )
        return {
            "success": True,
            "combat_Id": combat_Id,
            "message": message,
        }
    else:
        return {"success": False, "message": "None"}


@app.route("/findEnemyAbilities", methods=["GET"])
def find_enemy_abilities():
    token = request.headers.get("token")
    combat_Id = request.args.get("combat_Id")
    user = get_user_from_token(token)

    if not user:
        return {
            "success": False,
            "error": "Invalid token",
        }
    enemy_id = db.combats.find_one({"_id": ObjectId(combat_Id)})
    enemyPokemon = db.pokemons.find_one({"_id": ObjectId(enemy_id["enemy_poke_id"])})
    print("Enemigo encontrado: ", enemyPokemon)
    return {"success": True, "enemyAbilities": enemyPokemon}


@app.route("/messages", methods=["GET"])
def get_messages():
    token = request.args.get("token")
    combat_Id = request.args.get("combat_Id")
    user = get_user_from_token(token)
    if not user:
        return {"success": False, "error": "Invalid token"}

    userMessages = list(
        db.messages.find({"combat_Id": str(combat_Id), "user": str(user["_id"])})
    )
    print("nuevo mensaje:", userMessages)

    return {
        "success": True,
        "messages": {"userMessages": json.loads(json_util.dumps(userMessages))},
    }


@app.route("/collected", methods=["GET"])
def findCollected():
    collected = db.collection.find()

    return {"success": True, "collected": json.loads(json_util.dumps(collected))}


@app.route("/collected", methods=["DELETE"])
def deleteCollected():
    body_Collected = request.json
    db.collection.delete_many(body_Collected)
    return {"success": True, "collected": json.loads(json_util.dumps(body_Collected))}


@app.route("/collected", methods=["POST"])
def savecollected():
    body = request.json
    db.saved.insert_one(body)
    return {
        "success": True,
    }


@app.route("/collected", methods=["GET"])
def findcollected():
    collected = db.saved.find()
    return {"success": True, "collected": json.loads(json_util.dumps(collected))}


@app.route("/collected", methods=["DELETE"])
def deletecollected():
    body = request.json
    db.saved.delete_many(body)
    return {"success": True, "collected": json.loads(json_util.dumps(body))}
