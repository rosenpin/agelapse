import yt_dlp
from src.video_compile import compile_video
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_random_audio_from_playlist(playlist_url):
    logging.info(f"Fetching audio from playlist: {playlist_url}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'audio.%(ext)s',  # Use a simple, consistent filename
        'playlistrandom': True,
        'playlistend': 1,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        logging.info("Downloading random audio from playlist...")
        ydl.extract_info(playlist_url, download=True)
        
        # Get the full path of the downloaded audio file
        audio_filepath = os.path.abspath('audio.mp3')
        logging.info(f"Full audio file path: {audio_filepath}")
        
        return audio_filepath

audio_file = get_random_audio_from_playlist("https://www.youtube.com/playlist?list=PL7pkSK1xbGD5DV_k-CgHPECEFYacmq0dc")

output_path = f"/Users/tomer.rosenfeld/AgeLapse/Video/output_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.mp4"

compile_video(
    "/Users/tomer.rosenfeld/AgeLapse/Stabilized_Images",
    output_path,
    25,
    audio_file
)
