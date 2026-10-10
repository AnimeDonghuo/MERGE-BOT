"""
/setauthor — each user sets the name that is written into their merged files.

It is used for:
  * the default output file name, e.g. [Your Name]_merged.mkv
  * the container metadata (author / encoded_by)

Audio and subtitle track titles are the language name (English, Hindi, ...).
"""
from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.branding import MAX_AUTHOR_LENGTH, clean_author, default_file_name
from helpers.database import getUserAuthor, setUserAuthor

CLEAR_WORDS = {"clear", "remove", "reset", "none", "off"}

USAGE = (
    "**Set your author name**\n\n"
    "`/setauthor <name>` - set the name used in your files\n"
    "`/setauthor clear` - remove it\n\n"
    f"Max {MAX_AUTHOR_LENGTH} characters. Example: `/setauthor My Anime Channel`"
)


@Client.on_message(filters.command(["setauthor"]) & filters.private)
async def set_author_handler(c: Client, m: Message):
    parts = (m.text or "").split(maxsplit=1)
    current = getUserAuthor(m.from_user.id)

    if len(parts) < 2:
        if current:
            await m.reply_text(
                f"Your current author name is **{current}**.\n\n"
                f"Default file name: `{default_file_name(current)}`\n\n{USAGE}",
                quote=True,
            )
        else:
            await m.reply_text(f"You have not set an author name yet.\n\n{USAGE}", quote=True)
        return

    argument = parts[1].strip()
    if argument.lower() in CLEAR_WORDS:
        setUserAuthor(m.from_user.id, None)
        await m.reply_text(
            "Author name removed. Your files will no longer carry an author name.",
            quote=True,
        )
        return

    author = clean_author(argument)
    if author is None:
        await m.reply_text(
            f"That name can't be used (it may only contain symbols).\n\n{USAGE}", quote=True
        )
        return
    if len(argument) > MAX_AUTHOR_LENGTH:
        await m.reply_text(
            f"Name is too long. Keep it under {MAX_AUTHOR_LENGTH} characters.\n\n{USAGE}",
            quote=True,
        )
        return

    setUserAuthor(m.from_user.id, author)
    await m.reply_text(
        "✅ Author name saved: **{}**\n\n"
        "Your next merged files will use:\n"
        "• File name: `{}`\n"
        "• Metadata author: {}\n"
        "• Audio/subtitle track names: language names such as English, Hindi".format(
            author, default_file_name(author), author
        ),
        quote=True,
    )
