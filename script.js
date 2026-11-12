// =============================================================================
// script.js — the JAVASCRIPT side of Chat Wrapped (buttons + story slides)
// -----------------------------------------------------------------------------
// What this file is responsible for:
//   Everything the visitor clicks or sees change: turning buttons on, reading
//   the chosen file, asking Python to analyse it, and then running the
//   story slides (building them, moving between them, the progress bars).
//
// How it connects to the other files:
//   • index.html has the upload screen and an empty story screen this file fills.
//   • analysis.py does the data work. We talk to it through `window`:
//       - we CALL Python with   window.analyseChat(text)
//       - Python CALLS US with  window.onPythonReady()  when it has loaded
//   • Python replies with JSON text, which we turn back into data with JSON.parse.
//   • style.css decides how the slides and progress bars look.
// =============================================================================


// --- Find the parts of the page we need ------------------------------------------
// document.getElementById("x") finds the HTML element that has id="x",
// so we can change its text, hide it, show it, etc.
const uploadScreen  = document.getElementById("upload-screen");
const statusText    = document.getElementById("status");
const fileInput     = document.getElementById("file-input");
const uploadLabel   = document.getElementById("upload-label");
const sampleButton  = document.getElementById("sample-btn");
const errorBox      = document.getElementById("error-box");

const storyScreen   = document.getElementById("story-screen");
const progressBars  = document.getElementById("progress-bars");
const slideArea     = document.getElementById("slide-area");
const closeButton   = document.getElementById("close-btn");


// --- Python calls this when it has finished loading ---------------------------------
// We attach the function to `window` so Python can find it (window is the
// shared noticeboard both languages can read). It switches the buttons on.
window.onPythonReady = function () {
  fileInput.disabled = false;
  sampleButton.disabled = false;
  uploadLabel.classList.remove("btn-disabled");
  statusText.textContent = "🐍 Python is awake! Pick a chat to begin.";
};


// --- When someone chooses a file ----------------------------------------------------
// NEW CONCEPT — event listener:
//   An event listener says "WHEN this thing happens, DO this". Like telling a
//   friend "when the pizza arrives, call me". Here: when the file input
//   "changes" (a file was picked), run the function.
//
// `async` / `await`: reading a file takes a moment, so `await` means
// "wait for this to finish, then carry on" without freezing the page.
fileInput.addEventListener("change", async function () {
  const chosenFile = fileInput.files[0];
  if (!chosenFile) return;              // they opened the picker but cancelled

  const chatText = await chosenFile.text();   // read the file ON THIS DEVICE only
  fileInput.value = "";                 // reset, so picking the same file again still works
  analyseAndShow(chatText);
});


// --- When someone clicks "Try with sample chat" ----------------------------------
// fetch() loads sample-chat.txt from OUR OWN website (it sits next to index.html).
// This is our fake demo chat, so no one's real messages are involved.
sampleButton.addEventListener("click", async function () {
  try {
    const response = await fetch("sample-chat.txt");
    const chatText = await response.text();
    analyseAndShow(chatText);
  } catch (error) {
    showError("Couldn't find the sample chat 🙈 Is sample-chat.txt uploaded to GitHub?");
  }
});


// --- Send the text to Python, then start the story -------------------------------------
async function analyseAndShow(chatText) {
  hideError();
  statusText.textContent = "👀 Reading your gossip…";

  // Tiny pause so the browser can show the message above before Python gets busy.
  await new Promise(function (resolve) { setTimeout(resolve, 50); });

  // JavaScript → Python: call the Python function and get JSON text back...
  const jsonText = window.analyseChat(chatText);
  // ...then turn that JSON text into a real JavaScript object.
  const stats = JSON.parse(jsonText);

  statusText.textContent = "🐍 Python is awake! Pick a chat to begin.";

  if (!stats.ok) {
    showError(stats.error);
    return;
  }

  startStory(stats);
}


// =============================================================================
// THE STORY SLIDES
// -----------------------------------------------------------------------------
// NEW CONCEPT — an array of objects:
//   An array is a list: ["a", "b", "c"]. An object is a labelled bundle:
//   { title: "Night Owl", name: "Kabir" }. An array OF objects is a list of
//   bundles, like a stack of index cards where every card has the same boxes
//   to fill in. Each slide is one card:
//     { emoji, label, big, line, list }
//       emoji → a big emoji at the top
//       label → small heading ("You sent…")
//       big   → the BIG number or name
//       line  → the playful sentence underneath
//       list  → (optional) extra lines, e.g. the leaderboard
// =============================================================================

let slides = [];          // all the slide cards for this chat
let currentSlide = 0;     // which slide we're on (0 = the first one)


// --- Build the list of slides from Python's stats ------------------------------------
// We read from `stats` (the JSON from Python) and write one card per stat.
// Awards that nobody won come back as null from Python, so we skip them.
function buildSlides(stats) {
  const big = stats.big_numbers;
  const builtSlides = [];

  // 1) Welcome slide
  builtSlides.push({
    emoji: "🎀",
    label: "Your group chat, wrapped",
    big: `${big.people_count} people`,
    line: `${big.first_date} → ${big.last_date}. Let's see what you lot got up to…`,
  });

  // 2) Total messages
  builtSlides.push({
    emoji: "💬",
    label: "Together, you sent",
    big: big.total_messages.toLocaleString(),     // 1234 → "1,234"
    line: `messages. Your thumbs need a holiday 💅`,
  });

  // 3) Total words (about 250 words fit on a page of a book)
  const bookPages = Math.max(1, Math.round(big.total_words / 250));
  builtSlides.push({
    emoji: "📚",
    label: "That's a total of",
    big: `${big.total_words.toLocaleString()} words`,
    line: `About ${bookPages} pages of a book. Bestseller when? ✍️`,
  });

  // 4) Leaderboard
  const topPerson = stats.leaderboard[0];
  builtSlides.push({
    emoji: "🏆",
    label: "Chattiest of them all",
    big: topPerson.name,
    line: `${topPerson.messages} messages: that's ${topPerson.percent}% of the whole chat 👑`,
    list: stats.leaderboard.slice(0, 5).map(function (person, index) {
      return `${index + 1}. ${person.name}: ${person.messages}`;
    }),
  });

  // 5) Top emojis (only if the chat has any emojis)
  const emojis = stats.emojis;
  if (emojis.top_emojis.length > 0) {
    const topEmoji = emojis.top_emojis[0];
    builtSlides.push({
      emoji: "✨",
      label: "Your group's favourite emoji",
      big: topEmoji.emoji,
      line: `Used ${topEmoji.count} times. It's basically your group's logo.`,
      list: [emojis.top_emojis.slice(1, 10).map(function (item) { return item.emoji; }).join(" ")],
    });

    // 6) Each person's favourite emoji
    // Object.entries turns {"Zoya": "💖"} into [["Zoya", "💖"]] so we can loop over it.
    builtSlides.push({
      emoji: "🫶",
      label: "Everyone has a signature",
      big: "Your emojis",
      line: "If you were an emoji, you'd be…",
      list: Object.entries(emojis.favourite_emoji_per_person).map(function (pair) {
        return `${pair[0]}  ${pair[1]}`;
      }),
    });
  }

  // 7) Busiest hour, with a line that depends on the time of day
  const hour = stats.time.busiest_hour;
  let hourLine = "Prime gossip time ☕";
  if (hour < 5) hourLine = "Why is everyone awake?? Go to sleep 🌙";
  else if (hour < 12) hourLine = "Morning people. Suspicious, but okay ☀️";
  else if (hour >= 21) hourLine = "Late-night chats hit different 🌙";
  builtSlides.push({
    emoji: "🎧",
    label: "Your busiest hour",
    big: stats.time.busiest_hour_label,
    line: `${stats.time.busiest_hour_messages} messages in this hour. ${hourLine}`,
  });

  // 8) Busiest day of the week
  builtSlides.push({
    emoji: "📅",
    label: "Your favourite day to chat",
    big: stats.time.busiest_weekday,
    line: `${stats.time.busiest_weekday_messages} messages. ${stats.time.busiest_weekday}s are for the group chat.`,
  });

  // 9) Busiest month (the chart arrives in Stage 4)
  builtSlides.push({
    emoji: "📈",
    label: "Your most chaotic month",
    big: stats.months.busiest_month,
    line: `${stats.months.busiest_month_messages} messages. What happened?? 👀`,
  });

  // 10) Longest streak
  const streak = stats.streak;
  builtSlides.push({
    emoji: "🔥",
    label: "Longest streak",
    big: `${streak.longest_streak_days} days`,
    line: `In a row, without missing a day (${streak.streak_start} → ${streak.streak_end}). Commitment!`,
  });

  // 11) Most-used words
  if (stats.top_words.length > 0) {
    builtSlides.push({
      emoji: "🗣️",
      label: "The word you couldn't stop saying",
      big: `"${stats.top_words[0].word}"`,
      line: `Said ${stats.top_words[0].count} times. Runners-up:`,
      list: [stats.top_words.slice(1, 8).map(function (item) { return item.word; }).join(" · ")],
    });
  }

  // 12) Media sender
  const media = stats.media_and_length;
  if (media.top_media_sender) {
    builtSlides.push({
      emoji: "📸",
      label: "The Paparazzi award",
      big: media.top_media_sender,
      line: `Sent ${media.top_media_count} of the ${media.total_media} photos, videos and memes 📷`,
    });
  }

  // 13+) The awards: [emoji, award name, winner data, how to describe it]
  const awards = stats.awards;
  const awardSlides = [
    ["🦉", "Night Owl", awards.night_owl,
      function (w) { return `${w.value} messages between midnight and 5 AM. Do you ever sleep?`; }],
    ["🐦", "Early Bird", awards.early_bird,
      function (w) { return `${w.value} messages before 9 AM. Chai first, then chat ☕`; }],
    ["👑", "Emoji Royalty", awards.emoji_royalty,
      function (w) { return `${w.value} emojis per message. Words are overrated ✨`; }],
    ["✍️", "Essay Writer", awards.essay_writer,
      function (w) { return `${w.value} words per message on average. TL;DR please 📜`; }],
    ["⚡", "Speedster", awards.speedster,
      function (w) { return `Replies in ${w.value} min on average. Phone permanently in hand.`; }],
    ["🐢", "Turtle", awards.turtle,
      function (w) { return `Takes ${w.value} min on average to reply. Slow and steady 🐢`; }],
    ["👻", "Ghost", awards.ghost,
      function (w) { return `Only ${w.value} messages. We know you're reading this 👀`; }],
  ];
  awardSlides.forEach(function (award) {
    const [emoji, title, winner, describe] = award;   // unpack the four parts
    if (!winner) return;                              // nobody won → skip this award
    builtSlides.push({
      emoji: emoji,
      label: `🏅 ${title}`,
      big: winner.name,
      line: describe(winner),
    });
  });

  // Last slide: a mini summary (Stage 5 turns this into a downloadable card)
  builtSlides.push({
    emoji: "🎁",
    label: "That's a wrap!",
    big: "Chat Wrapped",
    line: "Screenshot this and send it to the group 💌",
    list: [
      `💬 ${big.total_messages.toLocaleString()} messages`,
      `🏆 Chattiest: ${topPerson.name}`,
      `🔥 Longest streak: ${streak.longest_streak_days} days`,
      `🎧 Busiest hour: ${stats.time.busiest_hour_label}`,
    ],
    isLast: true,
  });

  return builtSlides;
}


// --- Start the story: build slides, swap screens, show slide 1 --------------------------
function startStory(stats) {
  slides = buildSlides(stats);
  currentSlide = 0;
  buildProgressBars();

  uploadScreen.hidden = true;
  storyScreen.hidden = false;
  showSlide(0);
}


// --- Close the story and go back to the upload screen ------------------------------
function closeStory() {
  storyScreen.hidden = true;
  uploadScreen.hidden = false;
}


// --- Make one empty progress bar per slide -------------------------------------------
// Each bar is a grey "track" with a pink "fill" inside. showSlide() later decides
// how full each fill is.
function buildProgressBars() {
  progressBars.innerHTML = "";
  slides.forEach(function () {
    const track = document.createElement("div");
    track.className = "progress-track";
    const fill = document.createElement("div");
    fill.className = "progress-fill";
    track.appendChild(fill);
    progressBars.appendChild(track);
  });
}


// --- Draw slide number `index` on the screen --------------------------------------------
function showSlide(index) {
  currentSlide = index;
  const slide = slides[index];

  // Update the progress bars: slides before this one are full, this one fills
  // up (with a CSS animation), slides after it stay empty.
  const allFills = progressBars.querySelectorAll(".progress-fill");
  allFills.forEach(function (fill, fillIndex) {
    fill.classList.remove("is-done", "is-current");
    if (fillIndex < index) fill.classList.add("is-done");
    if (fillIndex === index) {
      void fill.offsetWidth;   // tiny trick: makes the browser restart the fill animation
      fill.classList.add("is-current");
    }
  });

  // Build the slide card. We use textContent (not innerHTML) because names and
  // words come from the chat: textContent shows them as plain text, so nothing
  // inside a chat can change our page.
  slideArea.innerHTML = "";
  const card = document.createElement("article");
  card.className = "slide-card";

  addText(card, "div", "slide-emoji", slide.emoji);
  addText(card, "p", "slide-label", slide.label);
  addText(card, "h2", "slide-big", slide.big);
  addText(card, "p", "slide-line", slide.line);

  if (slide.list) {
    const list = document.createElement("ul");
    list.className = "slide-list";
    slide.list.forEach(function (line) { addText(list, "li", "", line); });
    card.appendChild(list);
  }

  // The last slide gets a "start again" button instead of "tap to continue".
  if (slide.isLast) {
    const againButton = addText(card, "button", "btn", "🔁 Try another chat");
    // stopPropagation: stop this click from ALSO counting as a "tap to go back/next"
    againButton.addEventListener("click", function (event) {
      event.stopPropagation();
      closeStory();
    });
  } else {
    addText(card, "p", "slide-hint", "Tap → next   ·   ← back");
  }

  slideArea.appendChild(card);
}


// Small helper: make an element, give it a class and some text, add it to `parent`.
function addText(parent, tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
}


// --- Moving between slides ---------------------------------------------------------------
// We never go below slide 0 or past the last slide.
function nextSlide() {
  if (currentSlide < slides.length - 1) showSlide(currentSlide + 1);
}

function previousSlide() {
  if (currentSlide > 0) showSlide(currentSlide - 1);
}


// --- 1) TAP / CLICK: left third of the screen = back, the rest = next -----------------------
// Just like Instagram stories. event.clientX is how far from the left edge you tapped.
storyScreen.addEventListener("click", function (event) {
  if (event.clientX < window.innerWidth / 3) previousSlide();
  else nextSlide();
});

// The ✕ button closes the story (stopPropagation so it doesn't also count as a tap).
closeButton.addEventListener("click", function (event) {
  event.stopPropagation();
  closeStory();
});


// --- 2) KEYBOARD: arrow keys and space bar (for laptops) -----------------------------------
// NEW CONCEPT — keyboard event:
//   "keydown" fires whenever a key is pressed. event.key tells us WHICH key,
//   like "ArrowRight" or "Escape". We only listen while the story is open.
document.addEventListener("keydown", function (event) {
  if (storyScreen.hidden) return;
  if (event.key === "ArrowRight" || event.key === " ") { event.preventDefault(); nextSlide(); }
  if (event.key === "ArrowLeft") previousSlide();
  if (event.key === "Escape") closeStory();
});


// --- 3) SWIPE: for phones ---------------------------------------------------------------------
// NEW CONCEPT — touch events:
//   "touchstart" fires when a finger lands, "touchend" when it lifts. If the finger
//   moved more than 50 pixels sideways, it was a swipe, not a tap.
//   Swipe left (finger moves left) = next, swipe right = back.
let touchStartX = 0;

storyScreen.addEventListener("touchstart", function (event) {
  touchStartX = event.changedTouches[0].clientX;
}, { passive: true });

storyScreen.addEventListener("touchend", function (event) {
  const distanceMoved = event.changedTouches[0].clientX - touchStartX;
  if (Math.abs(distanceMoved) > 50) {
    // preventDefault stops the phone from ALSO firing a "click" (which would move twice)
    event.preventDefault();
    if (distanceMoved < 0) nextSlide();
    else previousSlide();
  }
}, { passive: false });


// --- Small helpers for the cute error box ----------------------------------------------
function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function hideError() {
  errorBox.hidden = true;
}
