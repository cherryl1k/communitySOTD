import os
import sys
import yaml # type: ignore (idk why im getting errors for this but it works so idc)
import random
from pathlib import Path

import tweepy
import subprocess
from dotenv import load_dotenv

def main():
    workspace_root = Path(__file__).resolve().parent.parent
    dotenv_path = workspace_root / ".env"

    if not dotenv_path.exists():
        print(f"Error: .env file not found at {dotenv_path}")
        sys.exit(1)

    load_dotenv(dotenv_path)

    keys = [
        "API_KEY",
        "API_SECRET",
        "ACCESS_TOKEN",
        "ACCESS_TOKEN_SECRET",
        "BEARER_TOKEN",
    ]

    env_vars = {key: os.getenv(key) for key in keys}

    missing_keys = [key for key, value in env_vars.items() if value is None]
    if missing_keys:
        print(f"Error: You are missing {', '.join(missing_keys)} in your .env file")
        sys.exit(1)

    # v2
    client = tweepy.Client(
        bearer_token=env_vars["BEARER_TOKEN"],
        consumer_key=env_vars["API_KEY"],
        consumer_secret=env_vars["API_SECRET"],
        access_token=env_vars["ACCESS_TOKEN"],
        access_token_secret=env_vars["ACCESS_TOKEN_SECRET"],
    )

    # v1.1
    auth = tweepy.OAuth1UserHandler(
        env_vars["API_KEY"],
        env_vars["API_SECRET"],
        env_vars["ACCESS_TOKEN"],
        env_vars["ACCESS_TOKEN_SECRET"],
    )
    api = tweepy.API(auth)
    
    result = get_and_make_files()
    
    print("Output file:", result["output_file"])
    print("Artists:", result["artists_text"])
    print("Song name:", result["song_name"])
    
    media = api.media_upload(filename=str(result["output_file"]), chunked=True)
    client.create_tweet(
        text=f"{result['song_name']}\n{result['artists_text']}",
        media_ids=[media.media_id]
    )
    
    return

def get_and_make_files():
    workspace_root = Path(__file__).resolve().parent.parent
    settings_path = workspace_root / "settings.yml"
    
    if not settings_path.exists():
        print(f"Error: settings.yml not found at {settings_path}")
        sys.exit(1)
        
    with open(settings_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Get our Audiofile from a subfolder in our "media_directory" 
    media_dir = Path(os.path.expanduser(config.get("media_directory", "")))
    subdirs = [d for d in media_dir.iterdir() if d.is_dir()]
    
    if not subdirs:
        raise ValueError(f"No subdirectories found in {media_dir}")
    
    random_subdir = random.choice(subdirs)
    
    file_formats = {".mp3", ".wav", ".flac", ".ogg", ".m4a"} # I reccomend using .mp3 or .ogg because of twitter compression and saving filespace 
    
    file_formats = [f for f in random_subdir.iterdir() if f.suffix.lower() in file_formats]
    
    if not file_formats:
        raise ValueError(f"No audio files found in {random_subdir}")
        
    random_audio = random.choice(file_formats)
    print(f"randomly chose, {random_audio} from {random_subdir} starting ffmpeg!")
    

    artist_file = random_subdir / "artist.txt"

    if artist_file.exists():
        with open(artist_file, "r", encoding="utf-8") as f:
            artists_text = f.read().strip()
    else:
        print("No artist.txt found in", random_subdir)
        return

    cover_image = random_subdir / "cover.jpg"
    if not cover_image.exists():
        cover_image = None
    
    ffmpeg_cfg = config["ffmpeg"]
    temp_dir = workspace_root / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    output_file = temp_dir / ffmpeg_cfg.get("output")
    options = ffmpeg_cfg.get("options", {})
    cmd = ["ffmpeg", "-y"]
    
    
    if cover_image:
        cmd.extend(["-loop", "1", "-i", str(cover_image)])
        cmd.extend(["-i", str(random_audio)])
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-b:a", "192k", "-shortest"])
    else:
        cmd.extend(["-i", str(random_audio)])
        options["filter_complex"] = options.get(
            "filter_complex",
            "color=black:size=1080x1080 [bg]; [bg][0:a] concat=n=1:v=1:a=1"
        )

    for key, value in options.items():
        ffmpeg_key = f"-{key}" if not key.endswith(":v") and not key.endswith(":a") else f"-{key}"
        if isinstance(value, bool):
            if value:
                cmd.append(ffmpeg_key)
        else:
            if key == "filter_complex":
                cmd.extend([ffmpeg_key, str(value)])
            else:
                cmd.extend([ffmpeg_key, str(value)])    
            
    cmd.append(str(output_file))
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print("FFmpeg failed:", e)
        sys.exit(1)
        
    return {
        "output_file": output_file,
        "artists_text": artists_text,
        "song_name": random_audio.stem
    }
    
if __name__ == "__main__":
    main()
