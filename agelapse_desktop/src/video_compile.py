import glob
import math
from mutagen.mp3 import MP3
import os
import platform
import re
import subprocess
import threading
import time
from typing import List
import tempfile
import shutil
from datetime import datetime

import exifread

def get_image_creation_date(image_path):
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f)

    # EXIF DateTimeOriginal tag is usually what stores the creation date
    date_tag = tags.get('EXIF DateTimeOriginal')

    if date_tag:
        d = datetime.strptime(str(date_tag), '%Y:%m:%d %H:%M:%S')
        return d
    else:
        modification_time = os.path.getmtime(image_path)
        d = datetime.fromtimestamp(modification_time)
        print(f"Last modified time: {d}")
        return d

def get_ffmpeg_path() -> str:
  """
  Determine the path to the ffmpeg executable based on the operating system.

  Returns:
      str: The path to the ffmpeg executable.
  """
  base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
  if platform.system() == 'Windows':
    ffmpeg_path = os.path.join(base_dir, 'assets', 'ffmpeg_win', 'ffmpeg.exe')
    return ffmpeg_path
  elif platform.system() == 'Darwin':
    # Use the static FFmpeg binary for macOS
    ffmpeg_path = os.path.join(base_dir, 'assets', 'ffmpeg_mac', 'ffmpeg')
    return ffmpeg_path
  return 'ffmpeg'  # Assume ffmpeg is available in PATH on Linux


def get_image_files(image_dir: str) -> List[str]:
  """
  Retrieve and sort the list of image files from the specified directory.

  Args:
      image_dir (str): The directory containing the images.

  Returns:
      List[str]: A sorted list of image file paths.
  """
  image_files = sorted(glob.glob(os.path.join(image_dir, '*.png')))
  if not image_files:
    raise FileNotFoundError("No .png files found in the specified directory.")

  return image_files

def get_video_length_with_opencv(filename: str) -> float:
    import cv2
    video = cv2.VideoCapture(filename)

    duration = video.get(cv2.CAP_PROP_POS_MSEC)
    frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)

    return duration, frame_count

def get_video_length(image_dir: str, framerate:int) -> float:
  image_files = get_image_files(image_dir)
  return len(image_files) / framerate


def run_ffmpeg(image_dir: str, output_video: str, framerate: int, audio_file: str) -> None:
    """
    Run ffmpeg to compile the images into a video with background music.
    The last frame will be held for 5 seconds.

    Args:
        image_dir (str): The directory containing the images.
        output_video (str): The output video file path.
        framerate (int): The output video framerate.
        audio_file (str): The path to the audio file to use as background music.
    """
    print("[LOG] Running ffmpeg...")

    ffmpeg_path: str = get_ffmpeg_path()

    print(f"[LOG] ffmpeg path is: {ffmpeg_path}")

    # Create the file list using a temporary file
    list_filename = create_file_list(image_dir, framerate)
    print(f"[LOG] File list has been created")

    # Create a temporary output file for the video without audio
    temp_output = os.path.join(os.path.dirname(output_video), "temp_output.mp4")

    # Create a temporary trimmed audio file
    temp_audio = os.path.join(os.path.dirname(output_video), "temp_audio.mp3")
    
    # Get the audio duration
    audio_duration = float(MP3(audio_file).info.length)
    
    # Get the video length
    video_length = get_video_length(image_dir, framerate)
    print(f"[LOG] Original video length: {video_length} seconds")
    
    # Add 5 seconds to the video length for the last frame hold
    video_length += 5
    print(f"[LOG] Adjusted video length with last frame hold: {video_length} seconds")
    
    # Calculate the start time for trimming
    start_time = math.floor(max(0, audio_duration - video_length)) -3.3
    
    # Trim the audio
    trim_command = [
        ffmpeg_path,
        "-ss", str(start_time),
        "-i", audio_file,
        "-t", str(video_length),
        "-c", "copy",
        "-y",
        temp_audio
    ]
    
    print("[LOG] Trimming audio...")
    
    subprocess.run(trim_command, check=True)
    
    print(f"[LOG] Audio trimmed to match video length: {video_length} seconds")

    # Generate the year overlay filter
    year_overlay_filter = generate_year_overlay_filter(image_dir)

    # Calculate the crop dimensions (65% of the original size)
    # Ensure the dimensions are even numbers
    crop_filter = "crop=iw*0.65:ih*0.65:x=(iw-ow)/2:y=(ih-oh)/2,scale='iw-mod(iw,2)':'ih-mod(ih,2)'"

    # Add tpad filter to hold the last frame for 5 seconds
    tpad_filter = f"tpad=stop_mode=clone:stop_duration=5"

    # Combine all filters
    combined_filter = f"{crop_filter},{tpad_filter},{year_overlay_filter}"

    command = [
        ffmpeg_path,
        '-f', 'concat',
        '-safe', '0',
        '-i', list_filename,
        '-filter_complex', combined_filter,
        '-pix_fmt', 'yuv420p',
        '-y',
        temp_output
    ]

    print("[LOG] Running video generation...")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    while True:
        line = process.stderr.readline()
        if line == '' and process.poll() is not None:
            break

        if line:
            print(line.strip())

    process.wait()

    # Now add the audio to the video
    command = [
        ffmpeg_path,
        '-i', temp_output,
        '-i', temp_audio,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        '-y',
        output_video
    ]

    print("[LOG] Adding audio to video...")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    while True:
        line = process.stderr.readline()
        if line == '' and process.poll() is not None:
            break

        if line:
            print(line.strip())

    process.wait()

    # Remove temporary files
    if os.path.exists(list_filename):
        os.remove(list_filename)
    if os.path.exists(temp_output):
        os.remove(temp_output)

    print("\n[LOG] Video with audio created successfully!")


def create_file_list(image_dir, framerate, list_filename=None):
  """
  Create a text file containing the list of images for FFmpeg to process.
  The last image will be held for 5 seconds.

  Args:
      image_dir (str): The directory containing the images.
      framerate (int or float): The framerate for the video.
      list_filename (str): The name of the text file to create. If None, a temporary file will be used.
  """
  try:
    print("[LOG] Creating ffmpeg file list...")

    time_per_frame = 1 / framerate  # Calculate duration for each frame

    # Get all image files and their creation dates
    image_files = [(img, get_image_creation_date(os.path.join(image_dir, img))) 
                   for img in os.listdir(image_dir) if img.endswith('.png')]

    # Sort images by creation date
    image_files.sort(key=lambda x: x[1])

    print(f"[LOG] Sorted image_files:")

    # Create a temporary file if no filename is provided
    if list_filename is None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        list_filename = temp_file.name
        temp_file.close()

    with open(list_filename, 'w') as file_list:
        for i, (image_file, _) in enumerate(image_files):
            # Write each file name and duration
            file_list.write(f"file '{os.path.join(image_dir, image_file)}'\n")
            
            # If it's the last image, set duration to 5 seconds
            if i == len(image_files) - 1:
                file_list.write(f"duration 5\n")
            else:
                file_list.write(f"duration {time_per_frame}\n")

    print(f"[LOG] File list created at {list_filename}")

  except Exception as e:
    print(f"[ERROR] Error while compiling video file list: {e}")

  return list_filename  # Return the path to the file list


def generate_year_overlay_filter(image_dir: str) -> str:
    image_files = get_image_files(image_dir)
    years = [get_image_creation_date(img).year for img in image_files]

    years.sort()
    
    filter_parts = []
    current_year = None
    start_frame = 0
    
    def create_drawtext_filter(year, start, end=None):
        enable_condition = f"between(n,{start},{end})" if end else f"gte(n,{start})"
        return (f"drawtext=fontfile=AlfaSlabOne-Regular.ttf:fontsize=116:fontcolor=white:box=1:"
                f"boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y=h-th-20:"
                f"text='{year}':enable='{enable_condition}'")
    
    for i, year in enumerate(years):
        if year != current_year:
            if current_year is not None:
                filter_parts.append(create_drawtext_filter(current_year, start_frame, i))
            current_year = year
            start_frame = i
    
    # Add the last year segment
    if current_year is not None:
        filter_parts.append(create_drawtext_filter(current_year, start_frame))
    
    return ','.join(filter_parts)


def compile_video(stabilized_img_dir: str, output_video_path: str, framerate: int, audio_file: str) -> str:
  """
  Compile images from a specified directory into a video file with background music.
  """
  try:
    print(f"[LOG] Compiling video (framerate: {framerate}) with audio..... ", end=' ', flush=True)

    if not os.path.exists(stabilized_img_dir):
      raise FileNotFoundError(f"The specified image directory '{stabilized_img_dir}' does not exist.")

    if not os.path.exists(audio_file):
      raise FileNotFoundError(f"The specified audio file '{audio_file}' does not exist.")

    output_dir = os.path.dirname(output_video_path)
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    print(f'Saving video to {output_dir}')

    def target():
      run_ffmpeg(stabilized_img_dir, output_video_path, framerate, audio_file)

    thread = threading.Thread(target=target)
    thread.start()

    print("[LOG] Video compilation with audio completed successfully.")
    return output_video_path

  except FileNotFoundError as e:
    print(f"[ERROR] {e}")
  except PermissionError as e:
    print(f"[ERROR] Permission denied: {e}")
  except Exception as e:
    print(f"[ERROR] An unexpected error occurred: {e}")

  return ""
