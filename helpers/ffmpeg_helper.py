import asyncio
import subprocess
import shutil
import os
import time
import ffmpeg
from pyrogram.types import CallbackQuery
from config import Config
from pyrogram.types import Message
from __init__ import LOGGER
from helpers.utils import get_path_size
from helpers.database import getUserAuthor
from helpers.branding import brand_args, track_names_for_file


def _probe_streams(path: str):
    """(streams, format_tags) for a media file; empty values if probing fails."""
    try:
        data = ffmpeg.probe(filename=path)
        return data.get("streams", []), (data.get("format") or {}).get("tags") or {}
    except Exception as e:
        LOGGER.warning(f"Could not probe {path}: {e}")
        return [], {}


def _first_input_of_concat(input_file: str):
    """Path of the first file listed in an ffmpeg concat list (lines like: file '/path')."""
    with open(input_file, "r") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("file "):
                return line[len("file "):].strip().strip("'")
    return None


async def MergeVideo(input_file: str, user_id: int, message: Message, format_: str):
    """
    This is for Merging Videos Together!
    :param `input_file`: input.txt file's location.
    :param `user_id`: Pass user_id as integer.
    :param `message`: Pass Editable Message for Showing FFmpeg Progress.
    :param `format_`: Pass File Extension.
    :return: This will return Merged Video File Path
    """
    output_vid = f"downloads/{str(user_id)}/concat_output.{format_.lower()}"
    brand = []
    first_file = _first_input_of_concat(input_file)
    if first_file:
        streams, format_tags = _probe_streams(first_file)
        brand = brand_args(streams, format_tags, getUserAuthor(user_id))
    file_generator_command = [
        "ffmpeg",
        "-y",  # overwrite a leftover output from an earlier failed run instead of prompting
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        input_file,
        "-map",
        "0",
        "-c",
        "copy",
        *brand,
        output_vid,
    ]
    process = None
    try:
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except NotImplementedError:
        await message.edit(
            text="Unable to Execute FFmpeg Command! Got `NotImplementedError` ...\n\nPlease run bot in a Linux/Unix Environment."
        )
        await asyncio.sleep(10)
        return None
    await message.edit("Merging Video Now ...\n\nPlease Keep Patience ...")
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    LOGGER.info(e_response)
    LOGGER.info(t_response)
    if os.path.lexists(output_vid):
        return output_vid
    else:
        return None


async def MergeSub(filePath: str, subPath: str, user_id):
    """
    This is for Merging Video + Subtitle Together.

    Parameters:
    - `filePath`: Path to Video file.
    - `subPath`: Path to subtitile file.
    - `user_id`: To get parent directory.

    returns: Merged Video File Path
    """
    LOGGER.info("Generating mux command")
    softmuxed = f"./downloads/{str(user_id)}/softmuxed_video.mkv"
    streams, format_tags = _probe_streams(filePath)
    brand = brand_args(
        streams,
        format_tags,
        getUserAuthor(user_id),
        added_subs=track_names_for_file(subPath, "subtitle"),
    )
    muxcmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        filePath,
        "-i",
        subPath,
        "-map",
        "0:v:0",
        "-map",
        "0:a:?",
        "-map",
        "0:s:?",
        "-map",
        "1:s",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "srt",
        *brand,
        softmuxed,
    ]
    LOGGER.info("Muxing subtitles")
    subprocess.call(muxcmd)
    orgFilePath = shutil.move(softmuxed, filePath)
    return orgFilePath


def MergeSubNew(filePath: str, subPath: str, user_id, file_list, file_names=None):
    """
    This method is for Merging Video + Subtitle(s) Together.

    Parameters:
    - `filePath`: Path to Video file.
    - `subPath`: Path to subtitile file.
    - `user_id`: To get parent directory.
    - `file_list`: List of all input files
    - `file_names`: Original file names of the inputs (same order as `file_list`),
      used to detect the subtitle language when the file itself has no tag.

    returns: Merged Video File Path
    """
    LOGGER.info("Generating mux command")
    softmuxed = f"downloads/{str(user_id)}/softmuxed_video.mkv"
    streams, format_tags = _probe_streams(filePath)
    added_subs = []
    for position, path in enumerate(file_list[1:], start=1):
        display = file_names[position] if file_names and position < len(file_names) else None
        added_subs += track_names_for_file(path, "subtitle", display)
    brand = brand_args(streams, format_tags, getUserAuthor(user_id), added_subs=added_subs)
    muxcmd = ["ffmpeg", "-y", "-hide_banner"]
    for i in file_list:
        muxcmd += ["-i", i]
    muxcmd += [
        "-map",
        "0:v:0",
        "-map",
        "0:a:?",
        "-map",
        "0:s:?",
    ]
    for j in range(1, len(file_list)):
        muxcmd += ["-map", f"{j}:s"]
    muxcmd += [
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "srt",
        *brand,
        f"./{softmuxed}",
    ]
    LOGGER.info("Sub muxing")
    subprocess.call(muxcmd)
    return softmuxed


def MergeAudio(videoPath: str, files_list: list, user_id, file_names=None):
    LOGGER.info("Generating Mux Command")
    export = f"downloads/{str(user_id)}/export.mkv"
    streams, format_tags = _probe_streams(videoPath)
    audio_disposition = [
        f"-disposition:a:{i}"
        for i in range(sum(1 for s in streams if s.get("codec_type") == "audio"))
    ]
    added_audio = []
    for position, path in enumerate(files_list[1:], start=1):
        display = file_names[position] if file_names and position < len(file_names) else None
        added_audio += track_names_for_file(path, "audio", display)
    brand = brand_args(streams, format_tags, getUserAuthor(user_id), added_audio=added_audio)
    muxcmd = ["ffmpeg", "-y", "-hide_banner"]
    for i in files_list:
        muxcmd += ["-i", i]
    muxcmd += ["-map", "0:v:0", "-map", "0:a:?"]
    for disposition in audio_disposition:
        muxcmd += [disposition, "0"]
    for j in range(1, len(files_list)):
        muxcmd += ["-map", f"{j}:a"]
    # The first added audio track becomes the default one.
    audio_count = len(audio_disposition)
    if len(files_list) > 1:
        muxcmd += [f"-disposition:a:{audio_count}", "default"]
    muxcmd += [
        "-map",
        "0:s:?",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "copy",
        *brand,
        export,
    ]

    LOGGER.info(muxcmd)
    process = subprocess.call(muxcmd)
    LOGGER.info(process)
    return export


async def cult_small_video(video_file, output_directory, start_time, end_time, format_):
    # https://stackoverflow.com/a/13891070/4723940
    out_put_file_name = (
        output_directory + str(round(time.time())) + "." + format_.lower()
    )
    file_generator_command = [
        "ffmpeg",
        "-ss",
        str(start_time),
        "-to",
        str(end_time),
        "-i",
        video_file,
        "-async",
        "1",
        "-strict",
        "-2",
        out_put_file_name,
    ]
    process = await asyncio.create_subprocess_exec(
        *file_generator_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    LOGGER.info(e_response)
    LOGGER.info(t_response)
    if os.path.lexists(out_put_file_name):
        return out_put_file_name
    else:
        return None


async def take_screen_shot(video_file, output_directory, ttl):
    """
    This functions generates custom_thumbnail / Screenshot.

    Parameters:

    - `video_file`: Path to video file.
    - `output_directory`: Path where to save thumbnail
    - `ttl`: Timestamp to generate ss

    returns: This will return path of screenshot
    """
    # https://stackoverflow.com/a/13891070/4723940
    out_put_file_name = os.path.join(output_directory, str(time.time()) + ".jpg")
    if video_file.upper().endswith(
        (
            "MKV",
            "MP4",
            "WEBM",
            "AVI",
            "MOV",
            "OGG",
            "WMV",
            "M4V",
            "TS",
            "MPG",
            "MTS",
            "M2TS",
            "3GP",
        )
    ):
        file_genertor_command = [
            "ffmpeg",
            "-ss",
            str(ttl),
            "-i",
            video_file,
            "-vframes",
            "1",
            out_put_file_name,
        ]
        # width = "90"
        process = await asyncio.create_subprocess_exec(
            *file_genertor_command,
            # stdout must a pipe to be accessible as process.stdout
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Wait for the subprocess to finish
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
    #
    if os.path.exists(out_put_file_name):
        return out_put_file_name
    else:
        return None


async def extractAudios(path_to_file, user_id):
    """
    docs
    """
    dir_name = os.path.dirname(os.path.dirname(path_to_file))
    if not os.path.exists(path_to_file):
        return None
    if not os.path.exists(dir_name + "/extract"):
        os.makedirs(dir_name + "/extract")
    videoStreamsData = ffmpeg.probe(path_to_file)
    # with open("data.json",'w') as f:
    #     f.write(json.dumps(videoStreamsData))
    extract_dir = dir_name + "/extract"
    audios = []
    for stream in videoStreamsData.get("streams"):
        try:
            if stream["codec_type"] == "audio":
                audios.append(stream)
        except Exception as e:
            LOGGER.warning(e)
    for audio in audios:
        extractcmd = []
        extractcmd.append("ffmpeg")
        extractcmd.append("-hide_banner")
        extractcmd.append("-i")
        extractcmd.append(path_to_file)
        extractcmd.append("-map")
        try:
            index = audio["index"]
            extractcmd.append(f"0:{index}")
            try:
                output_file: str = (
                    "("
                    + audio["tags"]["language"]
                    + ") "
                    + audio["tags"]["title"]
                    + "."
                    + audio["codec_type"]
                    + ".mka"
                )
                output_file = output_file.replace(" ", ".")
            except:
                output_file = str(audio["index"]) + "." + audio["codec_type"] + ".mka"
            extractcmd.append("-c")
            extractcmd.append("copy")
            extractcmd.append(f"{extract_dir}/{output_file}")
            LOGGER.info(extractcmd)
            subprocess.call(extractcmd)
        except Exception as e:
            LOGGER.error(f"Something went wrong: {e}")
    if get_path_size(extract_dir) > 0:
        return extract_dir
    else:
        LOGGER.warning(f"{extract_dir} is empty")
        return None


async def extractSubtitles(path_to_file, user_id):
    """
    docs
    """
    dir_name = os.path.dirname(os.path.dirname(path_to_file))
    if not os.path.exists(path_to_file):
        return None
    if not os.path.exists(dir_name + "/extract"):
        os.makedirs(dir_name + "/extract")
    videoStreamsData = ffmpeg.probe(path_to_file)
    # with open("data.json",'w') as f:
    #     f.write(json.dumps(videoStreamsData))
    extract_dir = dir_name + "/extract"
    subtitles = []
    for stream in videoStreamsData.get("streams"):
        try:
            if stream["codec_type"] == "subtitle":
                subtitles.append(stream)
        except Exception as e:
            LOGGER.warning(e)
    for subtitle in subtitles:
        extractcmd = []
        extractcmd.append("ffmpeg")
        extractcmd.append("-hide_banner")
        extractcmd.append("-i")
        extractcmd.append(path_to_file)
        extractcmd.append("-map")
        try:
            index = subtitle["index"]
            extractcmd.append(f"0:{index}")
            try:
                output_file: str = (
                    "("
                    + subtitle["tags"]["language"]
                    + ") "
                    + subtitle["tags"]["title"]
                    + "."
                    + subtitle["codec_type"]
                    + ".mka"
                )
                output_file = output_file.replace(" ", ".")
            except:
                try:
                    output_file = (
                        str(subtitle["index"])
                        + "."
                        + subtitle["tags"]["language"]
                        + "."
                        + subtitle["codec_type"]
                        + ".mka"
                    )
                except:
                    output_file = (
                        str(subtitle["index"]) + "." + subtitle["codec_type"] + ".mka"
                    )
            extractcmd.append("-c")
            extractcmd.append("copy")
            extractcmd.append(f"{extract_dir}/{output_file}")
            LOGGER.info(extractcmd)
            subprocess.call(extractcmd)
        except Exception as e:
            LOGGER.error(f"Something went wrong: {e}")
    if get_path_size(extract_dir) > 0:
        return extract_dir
    else:
        LOGGER.warning(f"{extract_dir} is empty")
        return None
