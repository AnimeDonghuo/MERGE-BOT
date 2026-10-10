#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) Shrimadhav U K | gautamajay52

import logging
import math
import time

from pyrogram.errors.exceptions import FloodWait
from __init__ import (
    FINISHED_PROGRESS_STR,
    UN_FINISHED_PROGRESS_STR,
    EDIT_SLEEP_TIME_OUT,
    gDict,
    LOGGER,
)
from pyrogram import Client

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


class Progress:
    """Progress panel for uploads and downloads.

    Pyrogram awaits the progress callback for every transferred chunk, so the
    callback must stay cheap: it only edits the panel at most once every
    EDIT_SLEEP_TIME_OUT seconds, never sleeps, and skips edits while Telegram
    asks us to back off (FloodWait).
    """

    def __init__(self, from_user, client, mess: Message):
        self._from_user = from_user
        self._client = client
        self._mess = mess
        self._cancelled = False
        self._cancel_announced = False
        self._last_edit = 0.0
        self._resume_at = 0.0  # no panel edits before this time (after FloodWait)

    @property
    def is_cancelled(self):
        chat_id = self._mess.chat.id
        mes_id = self._mess.id
        if gDict[chat_id] and mes_id in gDict[chat_id]:
            self._cancelled = True
        return self._cancelled

    async def progress_for_pyrogram(self, current, total, ud_type, start, count=""):
        if self.is_cancelled:
            if not self._cancel_announced:
                self._cancel_announced = True
                LOGGER.info("stopping ")
                try:
                    await self._mess.edit(
                        f"⛔ **Cancelled** ⛔ \n\n `{ud_type}` ({humanbytes(total)})"
                    )
                except Exception as ou:
                    logger.info(ou)
            await self._client.stop_transmission()
            return

        now = time.time()
        finished = current >= total
        if not finished:
            if now - self._last_edit < EDIT_SLEEP_TIME_OUT or now < self._resume_at:
                return
        self._last_edit = now

        diff = max(now - start, 0.001)
        total = total or 1
        percentage = current * 100 / total
        speed = current / diff
        time_to_completion = round((total - current) / speed) * 1000 if speed else 0
        estimated_total_time = TimeFormatter(milliseconds=time_to_completion) or "0 s"

        progress = "\n<code>[{0}{1}] {2}%</code>\n".format(
            "".join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 5))]),
            "".join(
                [
                    UN_FINISHED_PROGRESS_STR
                    for i in range(20 - math.floor(percentage / 5))
                ]
            ),
            round(percentage, 2),
        )
        tmp = (
            progress
            + "\n**⌧ Total 🗃:**` 〚{1}〛`\n**⌧ Done ✅ :**` 〚{0}〛`\n**⌧ Speed 📊 :** ` 〚{2}/s〛`\n**⌧ ETA 🔃 :**` 〚{3}〛`\n {4}".format(
                humanbytes(current),
                humanbytes(total),
                humanbytes(speed),
                estimated_total_time,
                count,
            )
        )
        try:
            if not self._mess.photo:
                await self._mess.edit_text(
                    text="{}\n {}".format(ud_type, tmp),
                    reply_markup=self._cancel_markup(),
                )
            else:
                await self._mess.edit_caption(caption="{}\n {}".format(ud_type, tmp))
        except FloodWait as fd:
            wait = getattr(fd, "value", None) or getattr(fd, "x", 0) or 0
            logger.warning(f"FloodWait on progress edit, skipping edits for {wait}s")
            self._resume_at = time.time() + wait
        except Exception as ou:
            logger.info(ou)

    def _cancel_markup(self):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⛔ Cancel ⛔",
                        callback_data=(
                            f"gUPcancel/{self._mess.chat.id}/{self._mess.id}/{self._from_user}"
                        ).encode("UTF-8"),
                    )
                ]
            ]
        )


def humanbytes(size):
    # https://stackoverflow.com/a/49361727/4723940
    # 2**10 = 1024
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: "", 1: "K", 2: "M", 3: "G", 4: "T"}
    while size > power:
        size /= power
        n += 1
    return f"{str(round(size, 2))} {Dic_powerN[n]}B"


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + "d, ") if days else "")
        + ((str(hours) + "h, ") if hours else "")
        + ((str(minutes) + "m, ") if minutes else "")
        + ((str(seconds) + "s, ") if seconds else "")
        + ((str(milliseconds) + "ms, ") if milliseconds else "")
    )
    return tmp[:-2]
