import glob
import os
import platform
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
        print(f"EXIF DateTimeOriginal: {d}")
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


def run_ffmpeg(image_dir: str, output_video: str, framerate: int, audio_file: str) -> None:
  """
  Run ffmpeg to compile the images into a video with background music.

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

  # Generate the year overlay filter
  year_overlay_filter = generate_year_overlay_filter(image_dir)

  command = [
    ffmpeg_path,
    '-f', 'concat',
    '-safe', '0',
    '-i', list_filename,
    '-filter_complex', year_overlay_filter,
    '-pix_fmt', 'yuv420p',
    '-y',
    temp_output
  ]

  print(f"[FFMPEG] Command for video: {command}")

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
    '-i', audio_file,
    '-c:v', 'copy',
    '-c:a', 'aac',
    '-shortest',
    '-y',
    output_video
  ]

  print(f"[FFMPEG] Command for adding audio: {command}")

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
    for img, date in image_files:
        print(f"{img}: {date}")

    # Create a temporary file if no filename is provided
    if list_filename is None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        list_filename = temp_file.name
        temp_file.close()

    with open(list_filename, 'w') as file_list:
        for image_file, _ in image_files:
            # Write each file name and duration
            file_list.write(f"file '{os.path.join(image_dir, image_file)}'\n")
            file_list.write(f"duration {time_per_frame}\n")

        # Add an extra duration line for the last image
        if image_files:
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
    
    for i, year in enumerate(years):
        if year != current_year:
            if current_year is not None:
                filter_parts.append(f"drawtext=fontfile=Roboto-Regular.ttf:fontsize=44:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y=h-th-10:text='{current_year}':enable='between(n,{start_frame},{i})'")
            current_year = year
            start_frame = i
    
    # Add the last year segment
    if current_year is not None:
        filter_parts.append(f"drawtext=fontfile=Roboto-Regular.ttf:fontsize=44:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y=h-th-10:text='{current_year}':enable='gte(n,{start_frame})'")
    
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
