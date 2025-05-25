from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import random
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from allowed_artists import ALLOWED_ARTISTS
from voice_message_handler import get_audio_preview

load_dotenv("keys.env")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

spotify = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

app = FastAPI()

# Дозволяємо CORS для Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

artist_weights = {artist_id: 1 for artist_id in ALLOWED_ARTISTS.keys()}
user_shown_tracks = {}
user_subscriptions = {}

SUBSCRIPTIONS_FILE = "subscriptions.json"
FEEDBACK_FILE = "feedback.txt"

if os.path.exists(SUBSCRIPTIONS_FILE):
    with open(SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
        user_subscriptions = json.load(f)


@app.get("/recommendation")
def get_recommendation(user_id: str, only_subscribed: bool = False):
    if only_subscribed:
        artist_ids = user_subscriptions.get(user_id, [])
    else:
        artist_ids = list(ALLOWED_ARTISTS.keys())

    if user_id not in user_shown_tracks:
        user_shown_tracks[user_id] = set()

    weighted = random.choices(
        artist_ids,
        weights=[artist_weights.get(aid, 1) for aid in artist_ids],
        k=len(artist_ids)
    )

    for artist_id in weighted:
        albums = spotify.artist_albums(artist_id, album_type='album,single', country='UA', limit=50)
        seen = set()
        tracks = []

        for album in albums['items']:
            for track in spotify.album_tracks(album['id'])['items']:
                if track['id'] not in seen and track['id'] not in user_shown_tracks[user_id]:
                    seen.add(track['id'])
                    tracks.append(track)

        if tracks:
            track = random.choice(tracks)
            user_shown_tracks[user_id].add(track['id'])

            return {
                "id": track['id'],
                "name": track['name'],
                "artist": ALLOWED_ARTISTS[artist_id],
                "artist_id": artist_id,
                "url": track['external_urls']['spotify'],
                "preview_url": track.get('preview_url'),
                "album_cover": spotify.album(track['album']['id'])['images'][0]['url']
                    if track.get('album') and track['album'].get('id') else None
            }

    return {"message": "No more tracks found."}


class ReactionData(BaseModel):
    user_id: str
    artist_id: str
    reaction: str  # like or dislike

@app.post("/react")
def react(data: ReactionData):
    if data.reaction == "like":
        artist_weights[data.artist_id] = artist_weights.get(data.artist_id, 1) + 2
        return {"message": "Liked"}
    elif data.reaction == "dislike":
        artist_weights[data.artist_id] = max(1, artist_weights.get(data.artist_id, 1) - 3)
        return {"message": "Disliked"}
    else:
        return {"error": "Unknown reaction type."}


class SubscribeData(BaseModel):
    user_id: str
    artist_id: str

@app.post("/subscribe")
def subscribe(data: SubscribeData):
    if data.user_id not in user_subscriptions:
        user_subscriptions[data.user_id] = []

    if data.artist_id not in user_subscriptions[data.user_id]:
        user_subscriptions[data.user_id].append(data.artist_id)

        with open(SUBSCRIPTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_subscriptions, f, ensure_ascii=False, indent=2)

    return {"message": "Subscribed"}


@app.get("/subscriptions")
def get_subscriptions(user_id: str):
    return {
        "subscriptions": user_subscriptions.get(user_id, [])
    }


class FeedbackData(BaseModel):
    user_id: str
    username: str
    message: str

@app.post("/feedback")
def submit_feedback(data: FeedbackData):
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(f"{data.user_id} ({data.username}): {data.message}\n")
    return {"message": "Feedback saved"}
