import asyncio

from pymongo import MongoClient
from pymongo.errors import ConfigurationError, DuplicateKeyError
from pyrogram.types import CallbackQuery
from config import Config
from __init__ import LOGGER, MERGE_MODE

if not Config.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to your deployment's environment variables "
        "(e.g. Koyeb service settings) or to config.env for local runs."
    )

try:
    # Fail fast (10s) instead of pymongo's 30s default, so bot commands don't hang
    # for minutes when the database is unreachable.
    _client = MongoClient(Config.DATABASE_URL, serverSelectionTimeoutMS=10000)
except ConfigurationError as exc:
    raise RuntimeError(
        f"DATABASE_URL is invalid or its hostname could not be resolved: {exc}. "
        "Copy the connection string again from MongoDB Atlas (Connect > Drivers) "
        "and make sure the value set in the environment is the one you expect."
    ) from exc


class Database(object):
    client = _client
    mergebot = client.MergeBot


async def addUser(uid, fname, lname):
    try:
        userDetails = {
            "_id": uid,
            "name": f"{fname} {lname}",
        }
        Database.mergebot.users.insert_one(userDetails)
        LOGGER.info(f"New user added id={uid}\n{fname} {lname} \n")
    except DuplicateKeyError:
        LOGGER.info(f"Duplicate Entry Found for id={uid}\n{fname} {lname} \n")
    return


async def broadcast():
    a = Database.mergebot.mergeSettings.find({})
    return a


async def allowUser(uid, fname, lname):
    try:
        a = Database.mergebot.allowedUsers.insert_one(
            {
                "_id": uid,
            }
        )
    except DuplicateKeyError:
        LOGGER.info(f"Duplicate Entry Found for id={uid}\n{fname} {lname} \n")
    return


async def allowedUser(uid):
    a = Database.mergebot.allowedUsers.find_one({"_id": uid})
    try:
        if uid == a["_id"]:
            return True
    except TypeError:
        return False


async def saveThumb(uid, fid):
    try:
        Database.mergebot.thumbnail.insert_one({"_id": uid, "thumbid": fid})
    except DuplicateKeyError:
        Database.mergebot.thumbnail.replace_one({"_id": uid}, {"thumbid": fid})


async def delThumb(uid):
    Database.mergebot.thumbnail.delete_many({"_id": uid})
    return True


async def getThumb(uid):
    res = Database.mergebot.thumbnail.find_one({"_id": uid})
    return res["thumbid"]


async def deleteUser(uid):
    Database.mergebot.mergeSettings.delete_many({"_id": uid})


async def addUserRcloneConfig(cb: CallbackQuery, fileId):
    try:
        await cb.message.edit("Adding file to DB")
        uid = cb.from_user.id
        Database.mergebot.rcloneData.insert_one({"_id": uid, "rcloneFileId": fileId})
    except Exception as err:
        LOGGER.info("Updating rclone")
        await cb.message.edit("Updating file in DB")
        uid = cb.from_user.id
        Database.mergebot.rcloneData.replace_one({"_id": uid}, {"rcloneFileId": fileId})
    await cb.message.edit("Done")
    return


async def getUserRcloneConfig(uid):
    try:
        res = Database.mergebot.rcloneData.find_one({"_id": uid})
        return res["rcloneFileId"]
    except Exception as err:
        return None


def getUserMergeSettings(uid: int):
    try:
        res_cur = Database.mergebot.mergeSettings.find_one({"_id": uid})
        return res_cur
    except Exception as e:
        LOGGER.info(e)
        return None


def setUserMergeSettings(uid: int, name: str, mode, edit_metadata, banned, allowed, thumbnail):
    modes = Config.MODES
    if uid:
        try:
            Database.mergebot.mergeSettings.insert_one(
                document={
                    "_id": uid,
                    "name": name,
                    "user_settings": {
                        "merge_mode": mode,
                        "edit_metadata": edit_metadata,
                    },
                    "isAllowed": allowed,
                    "isBanned": banned,
                    "thumbnail": thumbnail,
                }
            )
            LOGGER.info("User {} Mode updated to {}".format(uid, modes[mode - 1]))
        except Exception:
            Database.mergebot.mergeSettings.replace_one(
                filter={"_id": uid},
                replacement={
                    "name": name,
                    "user_settings": {
                        "merge_mode": mode,
                        "edit_metadata": edit_metadata,
                    },
                    "isAllowed": allowed,
                    "isBanned": banned,
                    "thumbnail": thumbnail,
                },
            )
            LOGGER.info("User {} Mode updated to {}".format(uid, modes[mode - 1]))
        MERGE_MODE[uid] = mode
    # elif mode == 2:
    #     try:
    #         Database.mergebot.mergeModes.insert_one(
    #             document={"_id": uid, modes[0]: 0, modes[1]: 1, modes[2]: 0}
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[1]))
    #     except Exception:
    #         rep = Database.mergebot.mergeModes.replace_one(
    #             filter={"_id": uid},
    #             replacement={modes[0]: 0, modes[1]: 1, modes[2]: 0},
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[1]))
    #     MERGE_MODE[uid] = 2
    #     # Database.mergebot.mergeModes.delete_many({'id':uid})
    # elif mode == 3:
    #     try:
    #         Database.mergebot.mergeModes.insert_one(
    #             document={"_id": uid, modes[0]: 0, modes[1]: 0, modes[2]: 1}
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[2]))
    #     except Exception:
    #         rep = Database.mergebot.mergeModes.replace_one(
    #             filter={"_id": uid},
    #             replacement={modes[0]: 0, modes[1]: 0, modes[2]: 1},
    #         )
    #         LOGGER.info("User {} Mode updated to {}".format(uid, modes[2]))
    #     MERGE_MODE[uid]=3
    LOGGER.info(MERGE_MODE)


def enableMetadataToggle(uid: int, value: bool):

    1


def disableMetadataToggle(uid: int, value: bool):
    1


def getUserAuthor(uid: int):
    """Author name the user set with /setauthor, or None.

    Stored in its own collection so the merge settings writer cannot overwrite it.
    """
    try:
        doc = Database.mergebot.userBranding.find_one({"_id": uid})
        return doc.get("author") if doc else None
    except Exception as e:
        LOGGER.info(e)
        return None


def setUserAuthor(uid: int, author):
    """Save the author name, or remove it when `author` is None."""
    if author:
        Database.mergebot.userBranding.replace_one(
            {"_id": uid}, {"_id": uid, "author": author}, upsert=True
        )
    else:
        Database.mergebot.userBranding.delete_one({"_id": uid})


def checkDatabaseConnection() -> bool:
    """Ping MongoDB once at startup and log a clear hint if it can't be reached."""
    try:
        Database.client.admin.command("ping")
        LOGGER.info("MongoDB connection OK")
        return True
    except Exception as e:
        LOGGER.error(
            "Cannot reach MongoDB: %s. Check that DATABASE_URL is correct and that "
            "MongoDB Atlas > Network Access allows the host running the bot "
            "(for Koyeb's free tier, allow 0.0.0.0/0). Commands will not work "
            "until the database is reachable.",
            e,
        )
        return False


async def getUserAuthorAsync(uid: int):
    """getUserAuthor() without blocking the event loop (pymongo is synchronous)."""
    return await asyncio.get_running_loop().run_in_executor(None, getUserAuthor, uid)
