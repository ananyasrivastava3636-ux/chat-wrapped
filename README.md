# 🎀 Chat Wrapped

**Spotify Wrapped, but for your WhatsApp group chat.**

Export a WhatsApp group chat, upload the `.txt` file, and get a set of cute, animated, story-style slides about your chat: who never stops texting, who's the night owl, your group's favourite emoji, your longest streak, and more.

🔗 **Live site:** https://ananyasrivastava3636-ux.github.io/chat-wrapped/

![Chat Wrapped demo](assets/demo.gif)
<!-- Add a screenshot or screen-recording GIF later as assets/demo.gif -->

---

## ✨ What it does

Upload your chat (or tap **Try with sample chat**) and Chat Wrapped finds:

- 📊 **The big numbers:** total messages, total words, and the chat's date range
- 🏆 **Leaderboard:** who sends the most messages
- 😂 **Top 10 emojis**, plus each person's favourite emoji
- 🕰️ **Busiest hour of the day** and **busiest day of the week**
- 📈 **Most active month**, with a messages-over-time chart
- 🔥 **Longest streak** of days in a row with at least one message
- 💬 **Most-used words** (ignoring filler like "the", "is", "hai", "ok", "haan")
- ⚡ **Fastest replier** on average
- 📸 **Media sender** (most `<Media omitted>`) and **longest messages**
- 🏅 **Fun awards:** Night Owl 🦉, Early Bird 🐦, Emoji Queen/King 👑, Essay Writer ✍️, Ghost 👻

Each stat gets its own slide with a big number, a playful one-liner and hand-drawn stickers. You can tap, swipe or use the arrow keys to move through them, Instagram-stories style. The final summary card can be downloaded as an image to share with the group.

---

## 🔒 Privacy

**Your chat never leaves your device.**

All the analysis runs *inside your browser* using Python (via PyScript). The chat file is never uploaded, stored or sent to any server, not even to this website. Close the tab and it's gone.

Want to try it without using a real chat? Click **Try with sample chat**. It uses a completely made-up group, "Chai & Chaos ☕".

---

## 📲 How to export a WhatsApp chat

**Android**
1. Open the group chat.
2. Tap **⋮** (top right) → **More** → **Export chat**.
3. Choose **Without media**.
4. Save the `.txt` file to your phone or send it to yourself.

**iPhone**
1. Open the group chat.
2. Tap the **group name** at the top.
3. Scroll down and tap **Export Chat** → **Without Media**.
4. Save to Files. If you get a `.zip`, open it to get the `.txt` file inside.

Then open Chat Wrapped and upload the `.txt` file.

Supports Android and iPhone exports, Indian date format (dd/mm/yy), 12-hour and 24-hour times, Hinglish, emojis, and messages that span multiple lines.

---

## 🛠️ Tech used

| Tool | What it does here |
|---|---|
| **Python** | All the data analysis |
| **pandas** | Turns the chat into a table and calculates the stats |
| **PyScript (Pyodide)** | Runs Python directly in the browser, so no server is needed |
| **JavaScript** | Buttons, file reading, slides and navigation |
| **Chart.js** | Messages-over-time and busiest-hours charts |
| **HTML / CSS** | Structure, palette, animations and the phone-first layout |
| **GitHub Pages** | Free hosting |

### How Python and JavaScript talk to each other
1. JavaScript reads the chat file on your device.
2. It passes the text to Python through `window.parseChatToTable(text)`.
3. Python (pandas) analyses it and sends the results back as **JSON**.
4. JavaScript turns that JSON into slides.

---

## 📁 Project structure

```
chat-wrapped/
├── index.html          → page structure
├── style.css           → colours, fonts, layout, animations
├── script.js           → buttons, slides, talking to Python
├── analysis.py         → all the Python + pandas analysis
├── sample-chat.txt     → a fake demo chat (made-up names)
└── assets/
    ├── background.jpg  → watercolour background
    └── stickers/       → the 7 hand-drawn stickers
```

---

## 🎨 Design

A soft, whimsical palette:

| Colour | Hex | Used for |
|---|---|---|
| Amaranth | `#933B5B` | Headings, big numbers, buttons |
| Thulian Pink | `#B5728A` | Accents, progress bars, highlights |
| Brook Green | `#AABAAE` | Soft sections, charts, borders |
| Chalk | `#E3D6BF` | Cards and panels |
| Pomelo Olive | `#9F9679` | Small details and lines |

---

## 🗺️ Build progress

- [x] **Stage 1:** Upload page, sample chat, Python reads the chat into a pandas table
- [x] **Stage 2:** All stats and awards calculated in Python
- [x] **Stage 3:** Story slides with navigation and progress bars
- [ ] **Stage 4:** Palette, background, stickers, charts and animations
- [ ] **Stage 5:** Summary card download, loading screen, error messages, mobile testing

---

## 💖 Credits

The stickers and background are made by these wonderful artists:

| Sticker | Artist | Link |
|---|---|---|
| `apple.png` | [Artist name] | [Link] |
| `banana-cat.png` | [Artist name] | [Link] |
| `bunny-headphones.png` | [Artist name] | [Link] |
| `cherries.png` | [Artist name] | [Link] |
| `lilies.png` | [Artist name] | [Link] |
| `strawberry-bunny.png` | rosarrie | [Link] |
| `turtle.png` | [Artist name] | [Link] |
| `background.jpg` | [Artist name] | [Link] |

All artwork belongs to its creators and is used here for a personal, non-commercial project.

---

## 👩‍💻 About

Built by **Drishti Srivastava** as a learning project, designing and building a full web app step by step, entirely in the browser with GitHub.
