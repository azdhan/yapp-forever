# Yapp Forever — The Complete Guide

**Speak your mind. Keep it forever.**

This guide walks you through everything — from installing Yapp Forever to getting the most out of it. No coding knowledge needed. Read top to bottom once, keep it open while you set up, and you'll be running in about 10 minutes.

---

## Table of Contents

1. [What is Yapp Forever?](#what-is-yapp-forever)
2. [Before you install](#before-you-install)
3. [Getting your API keys](#getting-your-api-keys)
4. [Installing Yapp Forever](#installing-yapp-forever)
5. [First-time setup](#first-time-setup)
6. [Your first recording](#your-first-recording)
7. [The "new session" trick](#the-new-session-trick)
8. [Daily workflow](#daily-workflow)
9. [Understanding your notes](#understanding-your-notes)
10. [Connecting to Obsidian](#connecting-to-obsidian)
11. [Querying your second brain](#querying-your-second-brain)
12. [Settings you can change](#settings-you-can-change)
13. [Tips and tricks](#tips-and-tricks)
14. [Troubleshooting](#troubleshooting)
15. [FAQ](#faq)

---

## What is Yapp Forever?

Yapp Forever is a small app that lives quietly in your Windows system tray. Throughout the day, whenever you have a thought, question, observation, or idea worth keeping, you press a hotkey and speak it out loud. At the end of the day, everything you said gets automatically transcribed, cleaned up by AI, and saved as beautifully structured notes you own forever.

**Why it exists.** Typing breaks your flow. Most thoughts die between having them and writing them down. Voice capture removes that friction. You speak like you'd speak to a friend. The AI handles the cleanup.

**Who it's for.** Journalists, researchers, writers, students, thinkers — anyone whose best ideas happen while reading, walking, watching, or just living. Anyone who wants their thinking preserved in a format they'll actually revisit.

**What it is not.** It's not a note-taking app you open and stare at. It's not Evernote. It's not a journal. It's a background capture tool that turns fleeting thoughts into permanent structured records.

---

## Before you install

You need three things before starting:

- A **Windows 10 or 11** computer
- A working **microphone** (laptop mic is fine)
- About **30 minutes** for first-time setup, mostly waiting for API signups

You do **not** need:
- Python
- Any technical background
- A paid subscription — Yapp Forever itself is free
- Good handwriting, typing speed, or note-taking discipline

---

## Getting your API keys

Yapp Forever uses two AI services to do its work — one to transcribe your voice, one to polish the transcript into clean notes. You get your own keys for each (free or nearly free) and paste them into the app once. After that you never think about them again.

### 1. Groq API key (free — for transcription)

Groq runs OpenAI's Whisper model in the cloud. It turns your voice recordings into raw text. They have a generous free tier that is more than enough for this use.

1. Go to **console.groq.com**
2. Sign up with Google, GitHub, or email — takes 30 seconds
3. Once logged in, look for **API Keys** in the left sidebar
4. Click **Create API Key**
5. Give it a name like "Yapp Forever"
6. **Copy the key immediately** — it starts with `gsk_` and you won't be able to see it again
7. Paste it somewhere safe temporarily (a notes app, sticky note, anywhere)

### 2. Claude API key (paid — for polishing)

Claude by Anthropic takes your raw transcript and shapes it into structured, readable notes. It's the quality layer. You need to add credits, but $5 lasts most people over a year.

1. Go to **console.anthropic.com**
2. Sign up with Google or email
3. Go to **Settings → Billing** and add a payment method
4. Add **$5 in credits** to start (minimum)
5. Then go to **API Keys** in the sidebar
6. Click **Create Key**, name it "Yapp Forever"
7. **Copy the key** — it starts with `sk-ant-` — save it somewhere safe

*Don't worry about runaway costs. Yapp Forever uses roughly ₹2-3 per day at heavy use. $5 will last around a year.*

### 3. Gemini API key (free — backup)

Gemini by Google is a fallback for polishing if Claude is ever unavailable. Free tier is enough.

1. Go to **aistudio.google.com**
2. Sign in with your Google account
3. Click **Get API key** in the sidebar
4. Click **Create API key in new project**
5. **Copy the key** — save it somewhere safe

---

## Installing Yapp Forever

1. Download `YappForever.exe` from wherever the creator shared it
2. Create a folder somewhere convenient — for example `C:\YappForever\`
3. Move `YappForever.exe` into that folder
4. Double-click to run it for the first time

The first time you run it, Windows may show a warning like "Windows protected your PC." This happens with any app that isn't signed by a major publisher. Click **More info**, then **Run anyway**. This is safe — it's just Windows being cautious about unknown apps.

---

## First-time setup

The first time you launch Yapp Forever, a setup window opens automatically. Fill in these fields:

| Field | What to paste |
|-------|---------------|
| **Groq API Key** | The `gsk_...` key you copied from console.groq.com |
| **Claude API Key** | The `sk-ant-...` key you copied from console.anthropic.com |
| **Gemini API Key** | The key from aistudio.google.com (optional but recommended) |
| **Obsidian Vault Path** | Where your polished notes will be saved (see next section) |
| **Auto-Process Time** | What time each night your day's recordings get processed (default 23:55 = 11:55 PM) |

### The Obsidian Vault Path

Obsidian is a free note-taking app that reads markdown files from a folder. Your Yapp Forever notes are saved as markdown, which means Obsidian can display them beautifully.

**If you already use Obsidian** — point this path to your vault folder, or ideally a subfolder inside it specifically for Yapp Forever.

**If you don't use Obsidian** — that's fine. Point this path to any folder where you want your notes saved. You can install Obsidian later and point it at the same folder.

**If you have no idea what Obsidian is** — skip that for now, just put any folder path like `C:\Users\YourName\Documents\YappNotes`. We'll explain Obsidian in a section below.

Click **Save & Start**. The setup window closes. That's the last time you'll see it unless you go into Settings.

You should see a small dark circle icon with a red dot appear in your system tray (bottom right of screen, near the clock). That's Yapp Forever running. It is now ready.

---

## Your first recording

### The hotkey

**Ctrl + Shift + Alt + S** — this is your record/pause toggle. It's the only hotkey you need to remember.

Press it once → a small black pill appears at the top of your screen saying "Keep yapping, I'm listening" with a red pulsing dot. You're recording.

Press it again → the pill disappears. Recording is paused.

Press it again → recording resumes. Everything gets added to the same file.

### Do a test recording

1. Press **Ctrl + Shift + Alt + S**
2. Say: *"Testing Yapp Forever. This is my first recording. I want to see if this thing actually works."*
3. Press **Ctrl + Shift + Alt + S** again to pause

That's it. The recording is saved. Throughout the day, every time you have a thought, press the hotkey, speak, press again to pause. All of those fragments go into one single audio file for the day.

### A note on media

If you're playing music or watching a video when you press the record hotkey, Yapp Forever will automatically pause whatever is playing so you can speak clearly. When you press the hotkey again to pause recording, your music resumes. You don't have to manually pause Spotify or YouTube.

---

## The "new session" trick

Here's where Yapp Forever gets powerful.

Throughout the day you'll capture thoughts about different things — a podcast, an article, a project idea, a random observation. You don't want all of those mixed together as one blob of text.

The solution is simple: **say "new session" or "next session" followed by the topic name** while you're recording.

Example workflow:

Press hotkey, speak:
> *"New session — Lex Fridman podcast episode 450. So I just started listening to this and the first point he makes is interesting. He says that..."*

Pause. Later you're reading an article:

Press hotkey, speak:
> *"Next session — The Atlantic article on AI regulation. So the main argument in this piece is that..."*

When Yapp Forever processes your day, it splits everything into clean sections with headings. Your final note file will look like:

```markdown
# Voice Notes — April 20, 2026

## Lex Fridman Podcast Episode 450
[Your cleaned-up thoughts about the episode]

## The Atlantic Article on AI Regulation  
[Your cleaned-up thoughts about the article]
```

**Tips for session markers:**

- Say "new session" or "next session" clearly, then pause briefly, then say the topic
- Keep topic names short — "Lex Fridman EP 450" is better than a long sentence
- If you forget to say it, everything still gets captured as one section called "General Notes"
- You can use it as many times as you want in a single day

---

## Daily workflow

Here's what an actual day looks like once Yapp Forever is running:

**Morning**
- You turn on your PC
- Launch Yapp Forever (double-click the exe, or it auto-starts if configured)
- Tray icon appears, you see nothing else

**Throughout the day**
- You're reading an article → press hotkey, speak your reactions, press again
- You're watching a video → say "next session - [video name]", speak, pause
- A random thought hits you on the couch → press hotkey, speak, pause
- Meeting with a colleague triggers an idea → press hotkey, speak, pause
- All of this goes into one file

**Late night (23:55 by default)**
- While you sleep, Yapp Forever automatically processes the day's audio
- Sends it to Groq for transcription
- Sends the transcript to Claude for cleaning and structuring
- Saves the final markdown file
- Copies it to your Obsidian vault

**Next morning**
- You open Obsidian (or the folder)
- Yesterday's notes are waiting — clean, structured, readable

### If you forget to keep your PC on past 23:55

Yapp Forever checks every time it launches whether yesterday's file was processed. If it wasn't (because your PC was off), it processes yesterday first before starting today. You never lose a day.

### If you want to process right now instead of waiting

Right-click the tray icon → click **Process Now**. The current day's audio is processed immediately. Useful for testing or if you're closing shop early.

---

## Understanding your notes

Your final markdown file will contain two parts.

### Part 1 — The cleaned transcript

Your thoughts, organized by session, with:
- Filler words removed ("uh", "um", "so so so")
- Grammar fixed but your natural voice preserved
- Proper nouns auto-corrected (if you said "Lex Freedman" it becomes "Lex Fridman" from context)
- No paraphrasing or invented content — just your words, cleaner

### Part 2 — FLAGS

A section at the bottom listing every non-trivial change the AI made. Each flag is marked:

- **MAJOR** — proper noun corrections, meaning-altering changes, uncertain guesses
- **MINOR** — structural fixes, filler removal, light rewording

This means you can always see what was changed and why. You're never guessing whether the AI edited something you didn't want edited.

---

## Connecting to Obsidian

Obsidian is a free note-taking app that's perfect for reading your Yapp Forever notes.

### Install Obsidian

1. Go to **obsidian.md**
2. Download the free Windows version
3. Install it

### Point Obsidian at your notes

1. Open Obsidian
2. Click **Open folder as vault**
3. Select the folder you set as your Obsidian Vault Path in Yapp Forever setup
4. Your notes appear in the left panel

Now every morning, when Yapp Forever processes yesterday's audio, the note automatically appears in your Obsidian vault. You just open Obsidian to read.

---

## Querying your second brain

This is where the real value compounds. Over weeks and months, you build up a searchable archive of your actual thinking. You can ask questions of your own notes using any AI.

### Option 1 — Obsidian Smart Connections plugin (recommended)

1. In Obsidian, go to **Settings → Community plugins**
2. Turn on community plugins
3. Search for **Smart Connections**
4. Install and enable it
5. In the plugin settings, paste your Claude or OpenAI API key
6. A chat interface opens inside Obsidian
7. Ask questions like: *"What did I think about AI regulation in April?"* or *"Summarize everything I said about Lex Fridman episodes this month"*

### Option 2 — Paste notes into any AI chat

Copy the content of a note file, paste into Claude, ChatGPT, or Gemini, ask your question. Works for quick questions.

### Option 3 — Advanced setup with cloud server

If you want a chat interface that queries all your notes at once from any device, you can set up a cloud vector database. This is beyond the scope of this guide but the Yapp Forever files are standard markdown so any such system works with them.

---

## Settings you can change

Right-click the tray icon → **Settings** to change:

- API keys (if one expires or you get a new one)
- Obsidian vault path (if you move your vault)
- Auto-process time (if 23:55 doesn't suit you)

After saving settings, changes take effect immediately. You don't need to restart the app.

---

## Tips and tricks

**Speak at normal pace, not slowly.** Whisper transcribes fast casual speech fine. Speaking artificially slowly actually makes transcription worse.

**Don't edit yourself while recording.** If you start a sentence wrong, just start over. The AI cleanup handles false starts beautifully. Forcing yourself to speak perfectly defeats the whole point.

**Use session markers liberally.** Every distinct topic deserves its own session. This makes your final notes much more useful.

**Record your own voice memos too.** Driving? Walking? Press the hotkey, speak, pause. You don't need to be at your PC as long as the app is running in the background.

**Read your notes weekly.** The best system falls apart if you never revisit what you captured. Block 15 minutes on Sunday to scan the week's notes.

**Use the "why you think that" prompt.** When you capture a thought, push yourself to also say *why* you think that. The reasoning is more valuable than the conclusion, and it's the part you'll forget fastest.

---

## Troubleshooting

### The tray icon doesn't appear

- Make sure only one `YappForever.exe` is running. Check Task Manager (Ctrl+Shift+Esc), end any duplicate processes.
- The icon might be hidden behind the **^** arrow in your system tray. Click the arrow to show hidden icons.
- Try restarting the app — close it from Task Manager and double-click the exe again.

### The hotkey doesn't do anything

- Another app might be using the same hotkey. Close other running apps one by one to find the conflict.
- Try running Yapp Forever as administrator — right-click the exe → Run as administrator.

### The recording indicator shows but no audio is captured

- Check your microphone is set as the default input device in Windows sound settings
- Try unplugging and replugging your microphone
- Test by recording a brief clip and checking the file in your `recordings` folder plays back correctly

### Processing fails at night

- Check your internet connection — the app needs internet to reach Groq and Claude
- Check your API keys haven't expired — open Settings and verify they're still valid
- Check your Claude account has credit remaining — low balance will block processing
- The app will try again next time it launches. You won't lose data.

### I'm running out of Claude credits

- Groq has a free Llama model that can replace Claude for polishing. Ask the creator for a config option to swap.
- Gemini free tier also works as a complete replacement if you configure it as primary.

### Audio file from yesterday never got processed

- Launch the app — it automatically detects and processes unprocessed yesterday files on startup
- Or right-click tray → Process Now after switching to yesterday's date

### Notes aren't appearing in my Obsidian vault

- Verify the Obsidian Vault Path in Settings is correct
- The notes go into a subfolder called "Yapp Forever" inside that path
- Make sure the folder actually exists and isn't in a synced location with a conflict

---

## FAQ

**Is my voice data private?**

Yes and no, honestly. Your audio files stay on your computer and are never uploaded anywhere except temporarily to Groq for transcription. Groq's terms say they don't train on API audio. Claude receives only the text transcript, not audio. If you're doing sensitive work, use your judgment.

**Can I use this on Mac or Linux?**

Not currently. Yapp Forever is Windows only right now.

**Will this work offline?**

The recording part works offline. The transcription and polishing both need internet. If you record offline, everything is saved locally and processes the next time you're online.

**How much does this cost per month?**

Realistically for a heavy user — under $1 per month in API costs. Groq and Gemini are free. Claude is the only paid service and a $5 credit lasts most people over a year.

**Can I back up my notes?**

Yes — everything is plain markdown files. Copy the folder anywhere — Google Drive, Dropbox, GitHub, USB stick. Your data is yours, in a format that lives forever.

**What happens if Anthropic or Groq shuts down?**

Your audio files and past notes stay exactly where they are — nothing is taken away. Future processing would need a different AI provider, but the tool is designed to be swappable. One config change points it at a different service.

**Can I record for 8 hours straight?**

Yes. The app handles long sessions fine. The resulting audio file will be large (maybe 500MB for 8 hours) but Groq processes it without issue.

**What if I say something I don't want kept?**

Open the audio file or markdown file and delete that section manually. Both are standard files on your computer — fully editable.

**Can multiple people share one installation?**

No — each person should have their own installation with their own API keys. Each install stores one set of notes in one vault.

**How do I uninstall?**

Quit the app from the tray icon. Delete the folder containing `YappForever.exe`. That's it. If you want to remove your notes too, delete your recordings and Obsidian vault folders as well.

---

*Built by azdhan. If you find a bug, have a feature request, or want to share what you've built with your notes, reach out.*