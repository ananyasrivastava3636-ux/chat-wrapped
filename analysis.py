# =============================================================================
# analysis.py  —  the PYTHON brain of Chat Wrapped
# -----------------------------------------------------------------------------
# What this file is responsible for:
#   Turning the raw WhatsApp .txt text into a neat pandas table (and, from
#   Stage 2, calculating all the fun stats from that table).
#
# How it connects to the other files:
#   • index.html loads this file with  <script type="py" src="analysis.py">.
#     PyScript then runs it INSIDE the browser.
#   • script.js reads the chat file and hands the text to Python by calling
#     window.analyseChat(text)  (we create that "doorway" at the bottom).
#   • Python hands the answer back to JavaScript as a JSON string.
#   • Nothing here ever sends the chat over the internet. 🔒
#
# NEW CONCEPT — PyScript:
#   Browsers normally only understand JavaScript. PyScript loads a full Python
#   (called Pyodide) into the web page, so Python code can run on the
#   visitor's own phone/laptop. Like carrying a tiny Python kitchen in your bag
#   instead of sending your ingredients to a restaurant.
# =============================================================================


# --- Imports: bringing in the tools we need -------------------------------------
# re      → regular expressions (pattern matching on text)
# json    → converting Python data into text JavaScript can understand
# pandas  → tables of data (DataFrames). Loaded thanks to the "packages" setting
#           in index.html.
import re
import json
import pandas as pd


# --- Step 0: clean invisible characters -----------------------------------------
# WhatsApp hides some invisible characters in exports:
#   ‎ is an invisible "left-to-right mark" (iPhone loves these),
#     and   are special "non-breaking" spaces (e.g. in "9:15 pm").
# They look like nothing, but they break pattern matching, so we swap them out
# for normal spaces (or remove them) before doing anything else.
def clean_invisible_characters(text):
    text = text.replace("‎", "").replace("‏", "").replace("﻿", "")
    text = text.replace(" ", " ").replace(" ", " ")
    return text


# --- The pattern that recognises "this line starts a new message" ------------------
# NEW CONCEPT — regex (regular expression):
#   A regex is a search pattern for text. Instead of searching for one exact
#   word, you describe a SHAPE, like "two digits, a slash, two digits".
#   Real-life example: a regex for an Indian mobile number could be "10 digits
#   starting with 6, 7, 8 or 9".
#
# A message line looks like ONE of these:
#   Android:  05/01/26, 1:02 pm - Ananya: hello
#   Android:  05/01/2026, 13:02 - Ananya: hello
#   iPhone:   [05/01/26, 1:02:45 PM] Ananya: hello
#
# Reading the pattern piece by piece:
#   ^\[?                 the line may start with "[" (iPhone)
#   (?P<date>...)        a date like 5/1/26 or 05/01/2026   → saved as "date"
#   ,?\s+                an optional comma, then spaces
#   (?P<time>...)        a time like 13:02, 1:02 pm, 1:02:45 PM, 1:02 p.m. → "time"
#   \]?\s*(?:-\s*)?      an optional "]" (iPhone) or " - " (Android)
#   (?P<rest>.*)$        everything after that (sender + message) → "rest"
MESSAGE_START_PATTERN = re.compile(
    r"^\[?(?P<date>\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}),?\s+"
    r"(?P<time>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s?[aApP]\.?\s?[mM]\.?)?)"
    r"\]?\s*(?:-\s*)?(?P<rest>.*)$"
)

# Words that tell us a line is a SYSTEM message (WhatsApp talking, not a person).
# Some iPhone exports put these after a "sender" name, so we check the text too.
SYSTEM_MESSAGE_HINTS = [
    "messages and calls are end-to-end encrypted",
    "created group",
    "created this group",
    "changed the subject",
    "changed this group's icon",
    "changed the group description",
    "joined using this group's invite link",
    "security code changed",
    "disappearing messages",
]


# --- Step 1: split the raw text into individual messages ---------------------------
# We walk through the file line by line:
#   • If a line matches the "new message" pattern → start a new message.
#   • If it doesn't → it's the next line of a long message, so glue it onto the
#     previous message (that's how we handle multi-line messages).
#   • If the "rest" has no "Name: " part → it's a system message, so we skip it.
#   • iPhone twist: iPhone writes system messages as if the GROUP sent them,
#     e.g. "[..] Chai & Chaos ☕: Ananya added Rohan". So when we spot a system
#     message with a "sender", we remember that name as a fake sender and
#     remove all of its messages at the end.
#
# NEW CONCEPT — dictionary:
#   A dictionary stores pairs of "label → value", like a contact card:
#   {"name": "Ananya", "phone": "98xxxxxx"}. Here each message becomes
#   {"date": ..., "time": ..., "sender": ..., "message": ...}.
def split_into_messages(raw_text):
    messages = []          # a list that will hold one dictionary per message
    current_message = None # the message we are currently building
    fake_senders = set()   # names that are really the group (iPhone), not people.
                           # A "set" is like a list that never repeats an item.

    for line in clean_invisible_characters(raw_text).splitlines():
        match = MESSAGE_START_PATTERN.match(line)

        if match:
            # This line starts a new message. First, save the one we were building.
            if current_message is not None:
                messages.append(current_message)
                current_message = None

            rest = match.group("rest")

            # A person's message always has "Name: text". No ": " means a
            # system line like "Ananya added Rohan" → skip it.
            if ": " not in rest:
                continue

            sender, message_text = rest.split(": ", 1)  # split only at the FIRST ": "

            # Skip system messages that sneak in with a "sender" (iPhone does this),
            # and remember that "sender" so we can remove its other messages later.
            if any(hint in message_text.lower() for hint in SYSTEM_MESSAGE_HINTS):
                fake_senders.add(sender.strip())
                continue

            current_message = {
                "date": match.group("date"),
                "time": match.group("time"),
                "sender": sender.strip(),
                "message": message_text.strip(),
            }

        elif current_message is not None:
            # Not a new message → it continues the previous one on a new line.
            current_message["message"] += "\n" + line

    # Don't forget the very last message in the file!
    if current_message is not None:
        messages.append(current_message)

    # Keep only messages from real people (drop the group's "fake sender" lines).
    real_messages = [message for message in messages if message["sender"] not in fake_senders]
    return real_messages


# --- Step 2: work out how the dates and times are written ---------------------------
# Different phones write dates differently: 05/01/26 or 05/01/2026, 13:02 or
# 1:02 PM. We try a list of possible "formats" and pick the one that correctly
# reads the most rows. Day-first (Indian) formats are listed first, so if two
# formats work equally well, the Indian one wins.
#   %d = day, %m = month, %y = 2-digit year, %Y = 4-digit year,
#   %H = 24-hour hour, %I = 12-hour hour, %M = minutes, %S = seconds, %p = AM/PM
POSSIBLE_DATETIME_FORMATS = [
    "%d/%m/%y %H:%M", "%d/%m/%y %H:%M:%S", "%d/%m/%y %I:%M %p", "%d/%m/%y %I:%M:%S %p",
    "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %I:%M %p", "%d/%m/%Y %I:%M:%S %p",
    "%m/%d/%y %H:%M", "%m/%d/%y %H:%M:%S", "%m/%d/%y %I:%M %p", "%m/%d/%y %I:%M:%S %p",
    "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M %p", "%m/%d/%Y %I:%M:%S %p",
]


# This tidies up one date+time string so every phone's style looks the same:
# "05.01.26" → "05/01/26",  "1.02 p.m." → "1:02 PM",  "1:02pm" → "1:02 PM".
def tidy_datetime_text(date_text, time_text):
    date_text = re.sub(r"[.\-]", "/", date_text)
    time_text = time_text.upper().replace(".", ":")       # 1.02 → 1:02
    time_text = re.sub(r":?\s*([AP]):?M:?$", r" \1M", time_text)  # P:M: / PM → " PM"
    return f"{date_text} {time_text.strip()}"


# NEW CONCEPT — DataFrame:
#   A pandas DataFrame is a table in Python, like a Google Sheet: it has rows
#   (one per message) and columns (datetime, sender, message). You can sort it,
#   filter it and count things in it with one line of code.
#
# This function takes the list of message dictionaries and builds that table.
def build_messages_table(messages):
    messages_table = pd.DataFrame(messages)

    # Join date + time into one tidy string per row.
    datetime_text = [
        tidy_datetime_text(date, time)
        for date, time in zip(messages_table["date"], messages_table["time"])
    ]
    datetime_text = pd.Series(datetime_text)

    # Try every format. errors="coerce" means "if a row can't be read, mark it as
    # NaT (Not a Time) instead of crashing". We keep the format with fewest NaTs.
    best_parsed_dates = None
    for date_format in POSSIBLE_DATETIME_FORMATS:
        parsed_dates = pd.to_datetime(datetime_text, format=date_format, errors="coerce")
        if best_parsed_dates is None or parsed_dates.isna().sum() < best_parsed_dates.isna().sum():
            best_parsed_dates = parsed_dates

    messages_table["datetime"] = best_parsed_dates

    # Keep only the columns we need, drop rows whose date couldn't be read,
    # and make sure everything is in time order.
    messages_table = messages_table[["datetime", "sender", "message"]]
    messages_table = messages_table.dropna(subset=["datetime"])
    messages_table = messages_table.sort_values("datetime").reset_index(drop=True)
    return messages_table


# =============================================================================
# STAGE 2: THE STATS
# -----------------------------------------------------------------------------
# Everything below takes the messages table and calculates one stat at a time.
# Each stat is its own small function, so it's easy to read, test and change.
#
# NEW CONCEPT — groupby:
#   groupby splits the table into piles (one pile per person, per hour, per
#   month...) and then counts or averages each pile. Like sorting a class's
#   exam papers into one pile per student, then counting each pile.
#   messages_table.groupby("sender").size()  →  "how many rows per person?"
# =============================================================================


# --- Helper: words to ignore when finding "most-used words" --------------------------
# These are filler words (English + Hinglish) that would win every time but say
# nothing fun about the chat. Add your own if boring words show up in the results!
COMMON_WORDS_TO_IGNORE = {
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "am", "i", "im", "i'm",
    "you", "your", "u", "we", "they", "he", "she", "it", "its", "it's", "me", "my", "mine",
    "to", "of", "in", "on", "at", "for", "with", "and", "or", "but", "so", "if", "this",
    "that", "what", "why", "how", "who", "when", "where", "do", "did", "does", "not", "no",
    "yes", "ok", "okay", "k", "oh", "just", "all", "up", "out", "by", "from", "as", "will",
    "can", "have", "has", "had", "too", "very", "also", "there", "here", "then", "than",
    "our", "us", "them", "her", "him", "his", "get", "got", "about", "one", "would",
    "should", "could", "let", "lets", "let's", "hear", "really", "like", "yeah", "s", "t",
    # Hinglish
    "hai", "haan", "ha", "han", "nahi", "nhi", "na", "toh", "to", "bhi", "ki", "ka", "ke",
    "ko", "se", "mein", "main", "me", "hoon", "hu", "ho", "kya", "kar", "kr", "raha", "rahi",
    "rahe", "tha", "thi", "the", "aur", "par", "pe", "ye", "yeh", "wo", "woh", "kyun",
    "kaun", "abhi", "bas", "ek", "sab", "hi", "ji", "acha", "accha", "achha", "theek",
    "thik", "yaar", "arre", "re", "phir", "kal", "aaj",
    # WhatsApp's own words
    "media", "omitted", "deleted", "message", "null",
}

# --- Helper: what counts as an emoji ----------------------------------------------------
# Emojis live in special number ranges in Unicode (the big list of every
# character computers know). This regex matches characters in those ranges.
#   \U0001F300-\U0001FAFF → faces, hearts, food, animals, objects...
#   ☀-➿         → older symbols like ☕ ✨ ❤ ☀
# We skip skin-tone modifiers (🏻🏼🏽🏾🏿) so "👍🏽" counts as a 👍.
EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001F3FA\U0001F400-\U0001FAFF☀-➿⭐⭕⏰-⏺]"
)

# Messages that aren't real text: media placeholders and deleted messages.
# (Android writes "<Media omitted>"; iPhone writes "image omitted", "video omitted"...)
MEDIA_PATTERN = re.compile(
    r"^(<media omitted>|<attached: .*>|(image|video|audio|sticker|gif|document) omitted)$"
)
DELETED_MESSAGES = {"this message was deleted", "you deleted this message"}


# Finds every emoji in one message.
# Older symbols like ❤ and ☀ only look colourful when followed by an invisible
# "show me as emoji" marker (️). We add it back so ❤ shows as ❤️ on the page.
def find_emojis(message_text):
    found = EMOJI_PATTERN.findall(message_text)
    return [emoji + "️" if "☀" <= emoji <= "➿" else emoji for emoji in found]


# --- Step 3: add helpful extra columns -------------------------------------------------
# Before calculating stats, we add columns that many stats need, so we only
# calculate them once. Think of it as preparing your ingredients before cooking.
def add_helper_columns(messages_table):
    lowercase_text = messages_table["message"].str.strip().str.lower()

    messages_table["is_media"] = lowercase_text.str.match(MEDIA_PATTERN)
    messages_table["is_deleted"] = lowercase_text.isin(DELETED_MESSAGES)
    # A "real text" message is one that isn't media and wasn't deleted.
    messages_table["is_text"] = ~(messages_table["is_media"] | messages_table["is_deleted"])

    # Word count: split the text on spaces and count the pieces (0 for media/deleted).
    messages_table["word_count"] = messages_table["message"].str.split().str.len()
    messages_table.loc[~messages_table["is_text"], "word_count"] = 0

    # A list of the emojis in each message, e.g. "lol 😂😂" → ["😂", "😂"]
    messages_table["emojis"] = messages_table["message"].apply(find_emojis)
    messages_table["emoji_count"] = messages_table["emojis"].str.len()

    # Pieces of the date and time, used for "busiest hour", "busiest day" etc.
    messages_table["date"] = messages_table["datetime"].dt.date
    messages_table["hour"] = messages_table["datetime"].dt.hour
    messages_table["weekday"] = messages_table["datetime"].dt.day_name()
    messages_table["month"] = messages_table["datetime"].dt.to_period("M")
    return messages_table


# --- Stat 1: the big numbers ---------------------------------------------------------------
def get_big_numbers(messages_table):
    first_moment = messages_table["datetime"].min()
    last_moment = messages_table["datetime"].max()
    return {
        "total_messages": int(len(messages_table)),
        "total_words": int(messages_table["word_count"].sum()),
        "first_date": first_moment.strftime("%d %b %Y"),
        "last_date": last_moment.strftime("%d %b %Y"),
        # +1 so a chat that starts and ends on the same day counts as 1 day
        "days_covered": int((last_moment.date() - first_moment.date()).days) + 1,
        "people_count": int(messages_table["sender"].nunique()),
    }


# --- Stat 2: leaderboard (who sends the most messages) -----------------------------------
# groupby("sender").size() counts rows per person; sort_values puts the biggest first.
def get_leaderboard(messages_table):
    messages_per_person = messages_table.groupby("sender").size().sort_values(ascending=False)
    total = len(messages_table)
    return [
        {"name": name, "messages": int(count), "percent": round(100 * count / total)}
        for name, count in messages_per_person.items()
    ]


# --- Stat 3: top 10 emojis + each person's favourite emoji ------------------------------
# .explode() turns a row holding ["😂", "😂", "🔥"] into three rows, one emoji each,
# so we can count emojis just like we count anything else.
def get_emoji_stats(messages_table):
    every_emoji = messages_table[["sender", "emojis"]].explode("emojis").dropna()

    if len(every_emoji) == 0:
        return {"top_emojis": [], "favourite_emoji_per_person": {}, "total_emojis": 0}

    top_emojis = every_emoji["emojis"].value_counts().head(10)

    favourite_emoji_per_person = {}
    for name, their_emojis in every_emoji.groupby("sender"):
        # value_counts() sorts most-used first, so .index[0] is their favourite
        favourite_emoji_per_person[name] = their_emojis["emojis"].value_counts().index[0]

    return {
        "total_emojis": int(len(every_emoji)),
        "top_emojis": [{"emoji": emoji, "count": int(count)} for emoji, count in top_emojis.items()],
        "favourite_emoji_per_person": favourite_emoji_per_person,
    }


# --- Stat 4: busiest hour of the day + busiest day of the week ----------------------------
# We also keep the full 24-hour list, because Stage 4 will draw it as a chart.
def get_time_stats(messages_table):
    messages_per_hour = messages_table.groupby("hour").size().reindex(range(24), fill_value=0)
    busiest_hour = int(messages_per_hour.idxmax())   # idxmax = "which label has the biggest value?"

    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    messages_per_weekday = messages_table.groupby("weekday").size().reindex(weekday_order, fill_value=0)

    return {
        "busiest_hour": busiest_hour,
        "busiest_hour_label": format_hour(busiest_hour),
        "busiest_hour_messages": int(messages_per_hour.max()),
        "messages_per_hour": [int(count) for count in messages_per_hour],
        "busiest_weekday": messages_per_weekday.idxmax(),
        "busiest_weekday_messages": int(messages_per_weekday.max()),
        "messages_per_weekday": {day: int(count) for day, count in messages_per_weekday.items()},
    }


# Turns 21 into "9 PM – 10 PM", which is friendlier than "21:00".
def format_hour(hour):
    def twelve_hour(h):
        h = h % 24
        suffix = "AM" if h < 12 else "PM"
        return f"{h % 12 or 12} {suffix}"
    return f"{twelve_hour(hour)} – {twelve_hour(hour + 1)}"


# --- Stat 5: most active month + messages over time (for the chart) -------------------------
def get_month_stats(messages_table):
    messages_per_month = messages_table.groupby("month").size()
    # Fill in months with zero messages, so the chart has no gaps
    all_months = pd.period_range(messages_per_month.index.min(), messages_per_month.index.max(), freq="M")
    messages_per_month = messages_per_month.reindex(all_months, fill_value=0)

    busiest_month = messages_per_month.idxmax()
    return {
        "busiest_month": busiest_month.strftime("%B %Y"),
        "busiest_month_messages": int(messages_per_month.max()),
        "messages_per_month": [
            {"month": month.strftime("%b %Y"), "messages": int(count)}
            for month, count in messages_per_month.items()
        ],
    }


# --- Stat 6: longest streak of days in a row with at least one message ----------------------
# We line up every date that had a message, in order, and walk through them:
# if today is exactly 1 day after the previous date, the streak grows;
# otherwise the streak starts again from 1.
def get_longest_streak(messages_table):
    chat_dates = sorted(messages_table["date"].unique())

    longest_streak = current_streak = 1
    longest_start = longest_end = current_start = chat_dates[0]

    for previous_date, this_date in zip(chat_dates, chat_dates[1:]):
        if (this_date - previous_date).days == 1:
            current_streak += 1
        else:
            current_streak = 1
            current_start = this_date

        if current_streak > longest_streak:
            longest_streak = current_streak
            longest_start, longest_end = current_start, this_date

    return {
        "longest_streak_days": int(longest_streak),
        "streak_start": longest_start.strftime("%d %b %Y"),
        "streak_end": longest_end.strftime("%d %b %Y"),
        "active_days": int(len(chat_dates)),
    }


# --- Stat 7: most-used words (ignoring common filler words) --------------------------------
# Steps: take all real text → make it lowercase → pull out words with a regex →
# throw away common words and tiny ones → count.
def get_top_words(messages_table, how_many=10):
    all_text = " ".join(messages_table.loc[messages_table["is_text"], "message"]).lower()
    # [a-z']+ means "one or more letters (or apostrophes) in a row" = a word
    words = re.findall(r"[a-z']+", all_text)
    interesting_words = [
        word.strip("'") for word in words
        if word.strip("'") not in COMMON_WORDS_TO_IGNORE and len(word.strip("'")) > 2
    ]
    word_counts = pd.Series(interesting_words, dtype="object").value_counts().head(how_many)
    return [{"word": word, "count": int(count)} for word, count in word_counts.items()]


# --- Stat 8: who replies fastest (and slowest) --------------------------------------------
# A "reply" = a message from someone DIFFERENT from the previous message's sender,
# sent within 2 hours. (After 2 hours it's probably a new conversation, not a reply.)
# .shift(1) looks at the row just above, i.e. the previous message.
MAX_REPLY_GAP_MINUTES = 120
MIN_REPLIES_TO_QUALIFY = 3   # so one lucky quick reply doesn't win the award

def get_reply_speed(messages_table):
    previous_sender = messages_table["sender"].shift(1)
    minutes_since_previous = messages_table["datetime"].diff().dt.total_seconds() / 60

    is_reply = (
        (messages_table["sender"] != previous_sender)
        & previous_sender.notna()
        & (minutes_since_previous <= MAX_REPLY_GAP_MINUTES)
    )
    replies = pd.DataFrame({
        "sender": messages_table.loc[is_reply, "sender"],
        "minutes": minutes_since_previous[is_reply],
    })

    reply_summary = replies.groupby("sender")["minutes"].agg(["mean", "count"])
    reply_summary = reply_summary[reply_summary["count"] >= MIN_REPLIES_TO_QUALIFY]
    if len(reply_summary) == 0:
        return {"fastest_replier": None, "slowest_replier": None, "average_reply_minutes": {}}

    reply_summary = reply_summary.sort_values("mean")
    return {
        "fastest_replier": reply_summary.index[0],
        "fastest_reply_minutes": round(float(reply_summary["mean"].iloc[0]), 1),
        "slowest_replier": reply_summary.index[-1],
        "slowest_reply_minutes": round(float(reply_summary["mean"].iloc[-1]), 1),
        "average_reply_minutes": {
            name: round(float(minutes), 1) for name, minutes in reply_summary["mean"].items()
        },
    }


# --- Stat 9: media sender + longest messages ------------------------------------------------
def get_media_and_length_stats(messages_table):
    media_per_person = messages_table.groupby("sender")["is_media"].sum().sort_values(ascending=False)

    # Average words per REAL text message, per person (only people with 5+ texts)
    text_messages = messages_table[messages_table["is_text"]]
    words_per_person = text_messages.groupby("sender")["word_count"].agg(["mean", "count"])
    words_per_person = words_per_person[words_per_person["count"] >= 5].sort_values("mean", ascending=False)

    # The single longest message in the whole chat
    longest_row = messages_table.loc[messages_table["word_count"].idxmax()]

    return {
        "top_media_sender": media_per_person.index[0] if media_per_person.iloc[0] > 0 else None,
        "top_media_count": int(media_per_person.iloc[0]),
        "total_media": int(messages_table["is_media"].sum()),
        "longest_average_writer": words_per_person.index[0] if len(words_per_person) else None,
        "longest_average_words": round(float(words_per_person["mean"].iloc[0]), 1) if len(words_per_person) else 0,
        "longest_message_sender": longest_row["sender"],
        "longest_message_words": int(longest_row["word_count"]),
    }


# --- Stat 10: the fun awards 🏅 ------------------------------------------------------------
# Each award picks a winner using a simple rule. We return None if nobody qualifies
# (e.g. no one ever texted after midnight), so the slides can skip that award.
def get_awards(messages_table, reply_stats, length_stats):
    messages_per_person = messages_table.groupby("sender").size()

    # Night Owl: most messages between midnight and 4:59 AM
    night_messages = messages_table[messages_table["hour"] < 5].groupby("sender").size()
    # Early Bird: most messages between 5 AM and 8:59 AM
    morning_messages = messages_table[messages_table["hour"].between(5, 8)].groupby("sender").size()

    # Emoji Royalty: most emojis PER MESSAGE (fairer than total, so chatty people
    # don't win just by talking more). Only people with 5+ messages qualify.
    emoji_stats = messages_table.groupby("sender")["emoji_count"].agg(["mean", "count"])
    emoji_stats = emoji_stats[emoji_stats["count"] >= 5].sort_values("mean", ascending=False)

    def winner(counts):
        """Return the name with the biggest count, or None if the list is empty."""
        if len(counts) == 0 or counts.max() == 0:
            return None
        return {"name": counts.idxmax(), "value": int(counts.max())}

    return {
        "night_owl": winner(night_messages),
        "early_bird": winner(morning_messages),
        "emoji_royalty": (
            {"name": emoji_stats.index[0], "value": round(float(emoji_stats["mean"].iloc[0]), 1)}
            if len(emoji_stats) else None
        ),
        "essay_writer": (
            {"name": length_stats["longest_average_writer"], "value": length_stats["longest_average_words"]}
            if length_stats["longest_average_writer"] else None
        ),
        "speedster": (
            {"name": reply_stats["fastest_replier"], "value": reply_stats["fastest_reply_minutes"]}
            if reply_stats["fastest_replier"] else None
        ),
        "turtle": (
            {"name": reply_stats["slowest_replier"], "value": reply_stats["slowest_reply_minutes"]}
            if reply_stats["slowest_replier"] else None
        ),
        # Ghost: the person with the FEWEST messages (idxmin = smallest)
        "ghost": {"name": messages_per_person.idxmin(), "value": int(messages_per_person.min())},
    }


# --- Putting it all together -----------------------------------------------------------
# Calls each stat function and collects the answers into one big dictionary.
def calculate_all_stats(messages_table):
    messages_table = add_helper_columns(messages_table)
    reply_stats = get_reply_speed(messages_table)
    length_stats = get_media_and_length_stats(messages_table)
    return {
        "big_numbers": get_big_numbers(messages_table),
        "leaderboard": get_leaderboard(messages_table),
        "emojis": get_emoji_stats(messages_table),
        "time": get_time_stats(messages_table),
        "months": get_month_stats(messages_table),
        "streak": get_longest_streak(messages_table),
        "top_words": get_top_words(messages_table),
        "replies": reply_stats,
        "media_and_length": length_stats,
        "awards": get_awards(messages_table, reply_stats, length_stats),
    }


# --- The main job: text in → stats out (as JSON) --------------------------------------------
# NEW CONCEPT — JSON:
#   JSON is a way to write data as plain text that BOTH Python and JavaScript
#   understand, like a universal language. A Python dictionary
#   {"name": "Zoya", "messages": 45} becomes the text '{"name": "Zoya", "messages": 45}'.
#
# We use try/except so that if ANYTHING goes wrong, we send back a cute error
# message instead of the page breaking.
def analyse_chat(raw_text):
    try:
        messages = split_into_messages(raw_text)
        if len(messages) == 0:
            return json.dumps({
                "ok": False,
                "error": "Hmm, this doesn't look like a WhatsApp chat 🥺 "
                         "Try exporting it again (Without media) and upload the .txt file.",
            }, ensure_ascii=False)

        messages_table = build_messages_table(messages)
        if len(messages_table) == 0:
            return json.dumps({
                "ok": False,
                "error": "I found messages but couldn't read their dates 😵‍💫 "
                         "Is this an unusual date format?",
            }, ensure_ascii=False)

        stats = calculate_all_stats(messages_table)
        stats["ok"] = True
        # ensure_ascii=False keeps emojis as emojis instead of codes like \ud83d.
        return json.dumps(stats, ensure_ascii=False)

    except Exception as error:
        # print() shows up in the browser console (F12) to help us debug.
        print("Something went wrong while reading the chat:", repr(error))
        return json.dumps({
            "ok": False,
            "error": "Oops, my brain got tangled reading that file 🧶 Please try another export!",
        }, ensure_ascii=False)


# =============================================================================
# THE BRIDGE: how Python and JavaScript talk to each other
# -----------------------------------------------------------------------------
# 1) JavaScript → Python: we put our Python function onto `window` (the
#    browser's big shared noticeboard that every script on the page can see),
#    under the name analyseChat. script.js can then call it like any
#    JavaScript function.
# 2) Python → JavaScript: when Python has finished loading (pandas included),
#    it calls window.onPythonReady(), a function written in script.js, to say
#    "I'm ready, turn the buttons on!"
#
# create_proxy keeps our Python function "alive" for JavaScript to use later.
# Without it, the browser could throw the function away after one use.
#
# The `try` is there so we can also test this file on a normal computer,
# where the browser-only pyscript tools don't exist.
# =============================================================================
try:
    from pyscript import window
    from pyodide.ffi import create_proxy

    window.analyseChat = create_proxy(analyse_chat)
    window.onPythonReady()
except ImportError:
    pass  # not running in a browser (e.g. testing in Codespaces) → skip the bridge
