"""
Helpers for the per-user branding that ends up in merged files:

* the author name written into the container metadata (author / encoded_by),
* the default output file name,
* audio / subtitle track titles, which are the language name (e.g. "English").

Nothing here talks to the database; the caller passes the user's author name in.
"""
import os
import re
from typing import List, Optional

# Anything that carries the old hard-coded branding is cleared from the output
# instead of being carried over from the source file.
BRAND_RE = re.compile(r"yashoswal", re.IGNORECASE)

MAX_AUTHOR_LENGTH = 32

# ISO 639-1 / 639-2 (T and B) codes -> English language name.
_LANGUAGE_CODES = {
    "en": "English", "eng": "English",
    "hi": "Hindi", "hin": "Hindi",
    "ja": "Japanese", "jp": "Japanese", "jpn": "Japanese",
    "ko": "Korean", "kor": "Korean",
    "zh": "Chinese", "zho": "Chinese", "chi": "Chinese",
    "es": "Spanish", "spa": "Spanish",
    "pt": "Portuguese", "por": "Portuguese",
    "fr": "French", "fra": "French", "fre": "French",
    "de": "German", "deu": "German", "ger": "German",
    "it": "Italian", "ita": "Italian",
    "ru": "Russian", "rus": "Russian",
    "ar": "Arabic", "ara": "Arabic",
    "bn": "Bengali", "ben": "Bengali",
    "ta": "Tamil", "tam": "Tamil",
    "te": "Telugu", "tel": "Telugu",
    "ml": "Malayalam", "mal": "Malayalam",
    "kn": "Kannada", "kan": "Kannada",
    "mr": "Marathi", "mar": "Marathi",
    "gu": "Gujarati", "guj": "Gujarati",
    "pa": "Punjabi", "pan": "Punjabi",
    "ur": "Urdu", "urd": "Urdu",
    "ne": "Nepali", "nep": "Nepali",
    "si": "Sinhala", "sin": "Sinhala",
    "sa": "Sanskrit", "san": "Sanskrit",
    "th": "Thai", "tha": "Thai",
    "vi": "Vietnamese", "vie": "Vietnamese",
    "id": "Indonesian", "ind": "Indonesian",
    "ms": "Malay", "msa": "Malay", "may": "Malay",
    "tl": "Tagalog", "tgl": "Tagalog", "fil": "Filipino",
    "tr": "Turkish", "tur": "Turkish",
    "fa": "Persian", "fas": "Persian", "per": "Persian",
    "he": "Hebrew", "heb": "Hebrew",
    "el": "Greek", "ell": "Greek", "gre": "Greek",
    "nl": "Dutch", "nld": "Dutch", "dut": "Dutch",
    "pl": "Polish", "pol": "Polish",
    "uk": "Ukrainian", "ukr": "Ukrainian",
    "cs": "Czech", "ces": "Czech", "cze": "Czech",
    "sk": "Slovak", "slk": "Slovak", "slo": "Slovak",
    "hu": "Hungarian", "hun": "Hungarian",
    "ro": "Romanian", "ron": "Romanian", "rum": "Romanian",
    "bg": "Bulgarian", "bul": "Bulgarian",
    "sr": "Serbian", "srp": "Serbian",
    "hr": "Croatian", "hrv": "Croatian",
    "bs": "Bosnian", "bos": "Bosnian",
    "sl": "Slovenian", "slv": "Slovenian",
    "sv": "Swedish", "swe": "Swedish",
    "no": "Norwegian", "nor": "Norwegian", "nb": "Norwegian", "nob": "Norwegian",
    "da": "Danish", "dan": "Danish",
    "fi": "Finnish", "fin": "Finnish",
    "is": "Icelandic", "isl": "Icelandic", "ice": "Icelandic",
    "ca": "Catalan", "cat": "Catalan",
    "lv": "Latvian", "lav": "Latvian",
    "lt": "Lithuanian", "lit": "Lithuanian",
    "et": "Estonian", "est": "Estonian",
    "sw": "Swahili", "swa": "Swahili",
    "am": "Amharic", "amh": "Amharic",
    "my": "Burmese", "mya": "Burmese", "bur": "Burmese",
    "km": "Khmer", "khm": "Khmer",
    "lo": "Lao", "lao": "Lao",
    "mn": "Mongolian", "mon": "Mongolian",
    "kk": "Kazakh", "kaz": "Kazakh",
    "uz": "Uzbek", "uzb": "Uzbek",
    "az": "Azerbaijani", "aze": "Azerbaijani",
    "ka": "Georgian", "kat": "Georgian", "geo": "Georgian",
    "hy": "Armenian", "hye": "Armenian", "arm": "Armenian",
}

# Lower-cased English names, so "English" or "hindi" in a file name is recognised.
_LANGUAGE_NAMES = {name.lower(): name for name in set(_LANGUAGE_CODES.values())}

_SEPARATORS = re.compile(r"[\s._\-\[\]\(\)]+")


def language_name(code: Optional[str]) -> Optional[str]:
    """Return the English name for a language tag such as 'eng' or 'en'.

    Unknown or undetermined tags ('und', 'mul', missing) return None.
    """
    if not code:
        return None
    return _LANGUAGE_CODES.get(code.strip().lower())


def guess_language_from_filename(filename: Optional[str]) -> Optional[str]:
    """Best-effort language from a file name, e.g. 'Movie.English.srt' -> 'English'.

    A full language name is accepted anywhere in the name. A short code such as
    'en' or 'hin' is only accepted as the last part before the extension, so
    words like 'in' or 'it' inside titles are not mistaken for a language.
    """
    if not filename:
        return None
    stem = os.path.splitext(os.path.basename(filename))[0]
    parts = [p for p in _SEPARATORS.split(stem) if p]
    for position, part in enumerate(reversed(parts)):
        lowered = part.lower()
        if lowered in _LANGUAGE_NAMES:
            return _LANGUAGE_NAMES[lowered]
        if position == 0 and lowered in _LANGUAGE_CODES:
            return _LANGUAGE_CODES[lowered]
    return None


def clean_author(raw: Optional[str]) -> Optional[str]:
    """Normalise a user supplied author name. Returns None when nothing usable is left."""
    if not raw:
        return None
    text = re.sub(r"[\r\n\t]+", " ", raw)
    text = re.sub(r'[\\/:*?"<>|]', "", text)  # characters that are unsafe in file names
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return text[:MAX_AUTHOR_LENGTH].rstrip()


def default_file_name(author: Optional[str]) -> str:
    """File name used when the user does not choose a custom one."""
    if author:
        return f"[{author}]_merged.mkv"
    return "merged.mkv"


def _lower_keys(tags) -> dict:
    """Tag names are case-insensitive. Matroska stores container tags in upper case (AUTHOR)."""
    return {str(k).lower(): v for k, v in (tags or {}).items()}


def _tags(stream: dict) -> dict:
    return _lower_keys(stream.get("tags"))


def _original_track_args(streams: list, codec_type: str) -> List[str]:
    """Title arguments for streams copied from the source file, in output order."""
    spec = "a" if codec_type == "audio" else "s"
    args: List[str] = []
    index = 0
    for stream in streams:
        if stream.get("codec_type") != codec_type:
            continue
        tags = _tags(stream)
        name = language_name(tags.get("language"))
        if name is None:
            old_title = tags.get("title", "")
            # Keep a meaningful original title, but drop titles with the old branding.
            name = "" if BRAND_RE.search(old_title) else old_title
        args += [f"-metadata:s:{spec}:{index}", f"title={name}"]
        index += 1
    return args


def track_names_for_file(path: str, codec_type: str, display_name: Optional[str] = None) -> List[str]:
    """One display name per stream of `codec_type` in an added input file.

    Uses the language tag inside the file first, then the file name, then
    'Track N'. `path` is probed with ffprobe.
    """
    import ffmpeg  # local import keeps this module light for tests

    fallback_name = display_name or os.path.basename(path)
    try:
        streams = [
            s for s in ffmpeg.probe(filename=path).get("streams", [])
            if s.get("codec_type") == codec_type
        ]
    except Exception:
        streams = []
    if not streams:
        streams = [{"codec_type": codec_type, "tags": {}}]
    names = []
    for ordinal, stream in enumerate(streams, start=1):
        name = (
            language_name(_tags(stream).get("language"))
            or guess_language_from_filename(fallback_name)
            or f"Track {ordinal}"
        )
        names.append(name)
    return names


def global_metadata_args(author: Optional[str], format_tags: dict) -> List[str]:
    """Container-level metadata: the user's author name, and removal of old branding."""
    format_tags = _lower_keys(format_tags)
    args: List[str] = []
    for key in ("author", "encoded_by"):
        if author:
            args += ["-metadata", f"{key}={author}"]
        elif BRAND_RE.search(format_tags.get(key, "") or ""):
            args += ["-metadata", f"{key}="]
    for key in ("title", "comment"):
        if BRAND_RE.search(format_tags.get(key, "") or ""):
            args += ["-metadata", f"{key}="]
    return args


def brand_args(
    source_streams: list,
    source_format_tags: dict,
    author: Optional[str],
    added_audio: Optional[List[str]] = None,
    added_subs: Optional[List[str]] = None,
) -> List[str]:
    """All ffmpeg output options that set track titles and author metadata.

    `source_streams` are the streams of the main input, in the order they are
    mapped to the output. `added_audio` / `added_subs` are display names for
    tracks that are appended after the source tracks.
    Must be placed before the output file name.
    """
    args: List[str] = []
    args += _original_track_args(source_streams, "audio")
    args += _original_track_args(source_streams, "subtitle")
    source_audio = sum(1 for s in source_streams if s.get("codec_type") == "audio")
    source_subs = sum(1 for s in source_streams if s.get("codec_type") == "subtitle")
    for offset, name in enumerate(added_audio or []):
        args += [f"-metadata:s:a:{source_audio + offset}", f"title={name}"]
    for offset, name in enumerate(added_subs or []):
        args += [f"-metadata:s:s:{source_subs + offset}", f"title={name}"]
    args += global_metadata_args(author, source_format_tags)
    return args
