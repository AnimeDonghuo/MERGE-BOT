import asyncio
import os
import time

from __init__ import LOGGER
from bot import LOGCHANNEL, userBot
from config import Config
from pyrogram import Client
from pyrogram.types import CallbackQuery, Message

from helpers.display_progress import Progress


async def _copy_to_log_channel(sent_: Message, cb: CallbackQuery):
    """Best-effort copy of the uploaded file to LOGCHANNEL. Never fails the upload."""
    if not LOGCHANNEL:
        return
    try:
        media = sent_.video or sent_.document
        await sent_.copy(
            chat_id=int(LOGCHANNEL),
            caption=f"`{media.file_name}`\n\nMerged for: <a href='tg://user?id={cb.from_user.id}'>{cb.from_user.first_name}</a>",
        )
    except Exception as err:
        LOGGER.warning(f"Could not copy upload to LOGCHANNEL: {err}")


async def uploadVideo(
    c: Client,
    cb: CallbackQuery,
    merged_video_path,
    width,
    height,
    duration,
    video_thumbnail,
    file_size,
    upload_mode: bool,
) -> bool:
    """Upload the merged file to the chat. Returns True on success.

    On failure the status panel is kept and shows the error, so the caller only
    removes it after a successful upload.
    """
    file_name = merged_video_path.rsplit("/", 1)[-1]
    prog = Progress(cb.from_user.id, c, cb.message)
    try:
        if Config.IS_PREMIUM:
            # Premium: upload through the user session to LOGCHANNEL, then copy to the chat.
            c_time = time.time()
            async with userBot:
                if upload_mode is False:
                    sent_: Message = await userBot.send_video(
                        chat_id=int(LOGCHANNEL),
                        video=merged_video_path,
                        height=height,
                        width=width,
                        duration=duration,
                        thumb=video_thumbnail,
                        caption=f"`{file_name}`\n\nMerged for: {cb.from_user.mention}",
                        progress=prog.progress_for_pyrogram,
                        progress_args=(f"Uploading: `{file_name}`", c_time),
                    )
                else:
                    sent_: Message = await userBot.send_document(
                        chat_id=int(LOGCHANNEL),
                        document=merged_video_path,
                        thumb=video_thumbnail,
                        caption=f"`{file_name}`\n\nMerged for: <a href='tg://user?id={cb.from_user.id}'>{cb.from_user.first_name}</a>",
                        progress=prog.progress_for_pyrogram,
                        progress_args=(f"Uploading: `{file_name}`", c_time),
                    )
            await c.copy_message(
                chat_id=cb.message.chat.id,
                from_chat_id=sent_.chat.id,
                message_id=sent_.id,
                caption=f"`{file_name}`",
            )
            return True

        c_time = time.time()
        if upload_mode is False:
            sent_: Message = await c.send_video(
                chat_id=cb.message.chat.id,
                video=merged_video_path,
                height=height,
                width=width,
                duration=duration,
                thumb=video_thumbnail,
                caption=f"`{file_name}`",
                progress=prog.progress_for_pyrogram,
                progress_args=(f"Uploading: `{file_name}`", c_time),
            )
        else:
            sent_: Message = await c.send_document(
                chat_id=cb.message.chat.id,
                document=merged_video_path,
                thumb=video_thumbnail,
                caption=f"`{file_name}`",
                progress=prog.progress_for_pyrogram,
                progress_args=(f"Uploading: `{file_name}`", c_time),
            )
    except Exception as err:
        LOGGER.info(err)
        try:
            await cb.message.edit("Failed to upload")
        except Exception:
            pass
        return False

    if sent_ is not None:
        await _copy_to_log_channel(sent_, cb)
    return sent_ is not None


async def uploadFiles(
    c: Client,
    cb: CallbackQuery,
    up_path,
    n,
    all
):
    try:
        sent_ = None
        prog = Progress(cb.from_user.id, c, cb.message)
        c_time = time.time()
        sent_: Message = await c.send_document(
            chat_id=cb.message.chat.id,
            document=up_path,
            caption=f"`{up_path.rsplit('/',1)[-1]}`",
            progress=prog.progress_for_pyrogram,
            progress_args=(
                f"Uploading: `{up_path.rsplit('/',1)[-1]}`",
                c_time,
                f"\n**Uploading: {n}/{all}**"
            ),
        )
        if sent_ is not None:
            if Config.LOGCHANNEL is not None:
                media = sent_.video or sent_.document
                await sent_.copy(
                    chat_id=int(LOGCHANNEL),
                    caption=f"`{media.file_name}`\n\nExtracted by: <a href='tg://user?id={cb.from_user.id}'>{cb.from_user.first_name}</a>",
                )
    except:
        1    
    1
