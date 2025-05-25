import requests
from io import BytesIO
from aiogram.types import InputFile
from pydub import AudioSegment
from ytmusicapi import YTMusic
import yt_dlp

ytmusic = YTMusic()

async def get_audio_preview(preview_url, track_name, artist_name):
    print(f"🔍 Отримуємо аудіо-прев'ю за URL: {preview_url}")
    try:
        if preview_url:
            response = requests.get(preview_url)
            print(f"🎵 Статус завантаження аудіо: {response.status_code}")
            if response.status_code == 200:
                audio = AudioSegment.from_file(BytesIO(response.content), format="mp3")
                buffer = BytesIO()
                audio.export(buffer, format="ogg", codec="libopus")
                buffer.seek(0)
                print("✅ Успішно створено голосове повідомлення")
                return InputFile(buffer, filename="preview.ogg")
            else:
                print("❌ Помилка отримання аудіо")
        else:
            print(f"🔎 Шукаємо прев’ю на YouTube Music для: {track_name} – {artist_name}")
            video_id = search_youtube_music(track_name, artist_name)
            if video_id:
                audio_data = download_youtube_audio(video_id)
                if audio_data:
                    return convert_to_voice(audio_data)
                else:
                    print("❌ Не вдалося завантажити аудіо з YouTube Music")
            else:
                print("❌ Трек не знайдено на YouTube Music")
    except Exception as e:
        print(f"🚨 Помилка обробки аудіо: {e}")
    return None

def download_audio(url):
    """ Завантажує аудіофайл за URL """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return BytesIO(response.content)
    except Exception as e:
        print(f"Помилка завантаження аудіо: {e}")
    return None

def search_youtube_music(track_name, artist_name):
    """ Шукає трек у YouTube Music і повертає ID відео """
    try:
        print(f"🔎 Шукаємо прев’ю на YouTube Music для: {track_name} – {artist_name}")
        search_results = ytmusic.search(f"{track_name} {artist_name}", filter="songs")
        if search_results:
            return search_results[0]['videoId']
    except Exception as e:
        print(f"Помилка пошуку на YouTube Music: {e}")
    return None

def download_youtube_audio(video_id):
    """ Завантажує аудіо з YouTube за допомогою yt-dlp """
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '-',
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            return download_audio(audio_url)
    except Exception as e:
        print(f"Помилка завантаження аудіо з YouTube: {e}")
    return None

def convert_to_voice(audio_data):
    """ Конвертує аудіо у формат голосового повідомлення """
    try:
        audio = AudioSegment.from_file(audio_data, format="mp3")
        buffer = BytesIO()
        audio.export(buffer, format="ogg", codec="libopus")
        buffer.seek(0)
        return InputFile(buffer, filename="preview.ogg")
    except Exception as e:
        print(f"Помилка конвертації в голосове повідомлення: {e}")
    return None
