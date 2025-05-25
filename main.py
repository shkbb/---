from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import random
import os
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
load_dotenv()  # завантажити .env файл

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

spotify = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

app = FastAPI()

# CORS для Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "music_app.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER,
            artist_id TEXT,
            PRIMARY KEY (user_id, artist_id)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS artist_descriptions (
            artist_name TEXT PRIMARY KEY,
            description TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS shown_tracks (
            user_id INTEGER,
            track_id TEXT,
            PRIMARY KEY (user_id, track_id)
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS allowed_artists (
            id TEXT PRIMARY KEY,
            name TEXT
        )''')
        conn.commit()

init_db()

# Тестові дані
TEST_ARTISTS = {
    "1": "alyona alyona",
    "2": "Kalush",
    "3": "Skofka"
}

with sqlite3.connect(DB_FILE) as conn:
    for artist_id, name in TEST_ARTISTS.items():
        conn.execute("INSERT OR IGNORE INTO allowed_artists (id, name) VALUES (?, ?)", (artist_id, name))
    conn.commit()

# Моделі
class UserRegister(BaseModel):
    user_id: int
    username: str

class Feedback(BaseModel):
    user_id: int
    message: str

class Reaction(BaseModel):
    user_id: int
    artist_id: str

# API endpoints
@app.post("/register")
def register(user: UserRegister):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)", (user.user_id, user.username))
    return {"status": "registered"}

@app.get("/get-track")
def get_random_track(user_id: int, only_subscribed: bool = False):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        if only_subscribed:
            cur.execute("SELECT artist_id FROM subscriptions WHERE user_id=?", (user_id,))
        else:
            cur.execute("SELECT id FROM allowed_artists")
        artist_ids = [row[0] for row in cur.fetchall()]
        if not artist_ids:
            return {"error": "no_artists"}

        selected_artist_id = random.choice(artist_ids)
        cur.execute("SELECT name FROM allowed_artists WHERE id=?", (selected_artist_id,))
        artist_name = cur.fetchone()[0]

        fake_track = {
            "track_id": f"track_{random.randint(100,999)}",
            "track_name": f"Demo Track {random.randint(1, 99)}",
            "artist_id": selected_artist_id,
            "artist_name": artist_name,
            "preview_url": None,
            "album_cover": None
        }

        try:
            conn.execute("INSERT INTO shown_tracks (user_id, track_id) VALUES (?, ?)", (user_id, fake_track["track_id"]))
        except:
            pass

        cur.execute("SELECT description FROM artist_descriptions WHERE artist_name=?", (artist_name,))
        row = cur.fetchone()
        fake_track["artist_description"] = row[0] if row else "Опису виконавця немає."

        return fake_track

@app.post("/like")
def like_track(reaction: Reaction):
    return {"status": "liked", "artist_id": reaction.artist_id}

@app.post("/dislike")
def dislike_track(reaction: Reaction):
    return {"status": "disliked", "artist_id": reaction.artist_id}

@app.post("/subscribe")
def subscribe_to_artist(reaction: Reaction):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR IGNORE INTO subscriptions (user_id, artist_id) VALUES (?, ?)", (reaction.user_id, reaction.artist_id))
    return {"status": "subscribed"}

@app.get("/subscriptions")
def get_subscriptions(user_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT artist_id FROM subscriptions WHERE user_id=?", (user_id,))
        ids = [row[0] for row in cur.fetchall()]
        return {"subscriptions": ids}

@app.post("/feedback")
def save_feedback(feedback: Feedback):
    with open("feedback.txt", "a", encoding="utf-8") as f:
        f.write(f"{feedback.user_id}: {feedback.message}\n")
    return {"status": "saved"}
