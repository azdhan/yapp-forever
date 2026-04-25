# ═══════════════════════════════════════════════════════════
# Yapp Forever — Standalone (all modules merged for EXE packaging)
# ═══════════════════════════════════════════════════════════

import os
import sys
import subprocess as _subprocess
import threading
import time
import queue
import ctypes
import ctypes.wintypes
import webbrowser
import numpy as np

if sys.platform == 'win32':
    _real_Popen = _subprocess.Popen
    class _NoCW(_real_Popen):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault('creationflags', _subprocess.CREATE_NO_WINDOW)
            super().__init__(*args, **kwargs)
    _subprocess.Popen = _NoCW
import subprocess  # noqa: E402
import sounddevice as sd
import keyboard
import pystray
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageDraw
from scipy.io.wavfile import write as wav_write, read as wav_read
from datetime import datetime, timedelta
from groq import Groq
from win32com.client import Dispatch

# ─── App constants ───────────────────────────────────────
APP_VERSION = "0.1.0"
GITHUB_REPO = "azdhan/yapp-forever"
SAMPLE_RATE = 44100
RECORD_HOTKEY = "ctrl+shift+alt+s"
PROCESS_HOTKEY = "ctrl+shift+alt+p"
SYSTEM_DEFAULT_INPUT = "System Default"

def _clean_device_name(name):
    return " ".join((name or "").replace("\r", " ").replace("\n", " ").split()).strip()

def _should_offer_input_device(name):
    lowered = name.lower()
    blocked_terms = (
        "sound mapper", "primary sound capture driver", "stereo mix",
        "@system32\\drivers\\", "pc speaker",
    )
    if not name or name in {"Input ()", "Microphone Array 1", "Microphone Array 2", "Microphone Array 3"}:
        return False
    if any(term in lowered for term in blocked_terms):
        return False
    if lowered.startswith("input ("):
        return False
    if name.endswith("()"):
        return False
    return True

def _iter_input_device_candidates():
    for index, device in enumerate(sd.query_devices()):
        if device.get('max_input_channels', 0) <= 0:
            continue
        raw_name = _clean_device_name(device['name'])
        if not _should_offer_input_device(raw_name):
            continue
        yield index, raw_name

# ─── Single instance guard ──────────────────────────────
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\YappForeverSingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:
    print("Yapp Forever is already running.")
    sys.exit(0)

_ui_queue = queue.Queue()

# ═══════════════════════════════════════════════════════════
# FFMPEG
# ═══════════════════════════════════════════════════════════

def _init_ffmpeg():
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
        ffmpeg = os.path.join(base, 'ffmpeg.exe')
        ffprobe = os.path.join(base, 'ffprobe.exe')
        if os.path.exists(ffmpeg):
            from pydub import AudioSegment
            AudioSegment.converter = ffmpeg
            AudioSegment.ffmpeg = ffmpeg
            AudioSegment.ffprobe = ffprobe

_init_ffmpeg()

def ensure_start_menu_shortcut():
    if not getattr(sys, 'frozen', False):
        return
    try:
        programs_dir = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'Microsoft', 'Windows', 'Start Menu', 'Programs'
        )
        os.makedirs(programs_dir, exist_ok=True)
        shortcut_path = os.path.join(programs_dir, 'Yapp Forever.lnk')
        target_path = sys.executable
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.IconLocation = target_path
        shortcut.Description = 'Yapp Forever'
        shortcut.save()
    except Exception as e:
        print(f"Start Menu shortcut error: {e}")

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

def get_config_path():
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    config_dir = os.path.join(appdata, 'YappForever')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'config.txt')

def get_prompt_path():
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return os.path.join(appdata, 'YappForever', 'prompt.txt')

def get_downloads_folder():
    folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'Yapp Forever', 'text notes')
    os.makedirs(folder, exist_ok=True)
    return folder

def get_recordings_folder():
    folder = os.path.join(os.path.expanduser('~'), 'Yapp Forever Audio Archive')
    os.makedirs(folder, exist_ok=True)
    return folder

def load_config():
    config = {}
    config_path = get_config_path()
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config

def load_custom_prompt():
    path = get_prompt_path()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ''

def save_custom_prompt(prompt_text):
    path = get_prompt_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(prompt_text)

# ═══════════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════════

GROQ_MAX_SIZE_BYTES = 24 * 1024 * 1024

_DEFAULT_POLISH_PROMPT = """\
You are a precise transcript editor processing a voice note (session {session_number}) recorded on {date_str} at {time_str}.

First, generate a smart, concise heading for this section based on what was spoken. Output it as a ## heading.

Then clean the transcript following these rules:
Fix grammar, punctuation, and sentence structure — but preserve the speaker's natural, casual voice. Do not make it sound formal or robotic.
Use context to intelligently correct proper nouns — names of people, books, organisations, places, shows, technical terms.
Do NOT add information that was not spoken. Do NOT remove any ideas or sentences.
Do NOT paraphrase. Stay as close to the original words as possible.
Remove filler repetitions (e.g. "so so so", "I I I") but keep intentional repetitions used for emphasis.
Do not substitute softer alternatives. The speaker's exact word choices must be respected.
Always preferbrevity. If anything can be expressed in few words without losing meaning, do it. Remove any unnecessary words, "ums", "likes", etc. that don't add meaning.
use smart bullet points wherever it is required or appropriate according to the context. 

Format your response exactly as:

## [Smart heading based on content]

[Cleaned transcript]

---
*Session {session_number} · Generated on {date_str} at {time_str}*

Raw transcript:
{transcript}

Return only the formatted markdown. No preamble, no explanation."""

def get_active_prompt():
    custom = load_custom_prompt()
    return custom if custom else _DEFAULT_POLISH_PROMPT

def compress_to_mp3(wav_path):
    from pydub import AudioSegment
    mp3_path = wav_path.replace('.wav', '_compressed.mp3')
    audio = AudioSegment.from_wav(wav_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(mp3_path, format='mp3', bitrate='64k')
    return mp3_path

def split_audio(audio_path, max_size_bytes=GROQ_MAX_SIZE_BYTES):
    from pydub import AudioSegment
    audio = AudioSegment.from_file(audio_path)
    file_size = os.path.getsize(audio_path)
    if file_size <= max_size_bytes:
        return [audio_path]
    num_chunks = (file_size // max_size_bytes) + 1
    chunk_duration_ms = len(audio) // num_chunks
    chunks = []
    base = audio_path.replace('.mp3', '').replace('.wav', '')
    for i in range(num_chunks):
        start = i * chunk_duration_ms
        end = start + chunk_duration_ms if i < num_chunks - 1 else len(audio)
        chunk = audio[start:end]
        chunk_path = f"{base}_chunk{i+1}.mp3"
        chunk.export(chunk_path, format='mp3', bitrate='64k')
        chunks.append(chunk_path)
    return chunks

def transcribe_single(client, audio_path):
    with open(audio_path, 'rb') as f:
        result = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f.read()),
            model="whisper-large-v3",
            response_format="text"
        )
    return result

def transcribe(audio_path, groq_key, status_callback=None):
    client = Groq(api_key=groq_key)
    if status_callback: status_callback("Compressing audio...")
    mp3_path = compress_to_mp3(audio_path)
    chunks = split_audio(mp3_path)
    if len(chunks) == 1:
        if status_callback: status_callback("Transcribing...")
        result = transcribe_single(client, chunks[0])
    else:
        transcripts = []
        for i, chunk_path in enumerate(chunks):
            if status_callback: status_callback(f"Transcribing part {i+1}/{len(chunks)}...")
            transcripts.append(transcribe_single(client, chunk_path))
        result = " ".join(transcripts)
    for chunk_path in chunks:
        if chunk_path != mp3_path and os.path.exists(chunk_path):
            os.remove(chunk_path)
    if os.path.exists(mp3_path):
        os.remove(mp3_path)
    return result

def _format_provider_failure_message(provider_name, error):
    error_text = str(error)
    lowered = error_text.lower()
    title = provider_name.capitalize()
    provider = provider_name.lower()
    if provider == "gemini" and ("not found for api version" in lowered or ("models/" in lowered and "not found" in lowered)):
        return "Gemini model is outdated - update to a newer Gemini model/API setting."
    if "resource_exhausted" in lowered or "quota" in lowered or "429" in lowered:
        return f"{title} quota/rate limit hit - try again later or check billing."
    if "permission_denied" in lowered or "invalid api key" in lowered or "authentication" in lowered or "unauthorized" in lowered or "403" in lowered or "401" in lowered or "api key" in lowered:
        return f"{title} API key/access issue - check the {provider} key and account access."
    if "timeout" in lowered or "timed out" in lowered:
        return f"{title} request timed out - try again in a moment."
    if "connection" in lowered or "dns" in lowered or "network" in lowered:
        return f"{title} network error - check internet connection and try again."
    return f"{title} failed - please review the {provider} setup and try again."

def polish_gemini(raw_transcript, gemini_key, date_str, session_number=1):
    from google import genai
    client = genai.Client(api_key=gemini_key)
    prompt = get_active_prompt().format(
        date_str=date_str, time_str=datetime.now().strftime('%H:%M'),
        session_number=session_number, transcript=raw_transcript
    )
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text

def polish_claude(raw_transcript, claude_key, date_str, session_number=1, model="claude-sonnet-4-5"):
    import anthropic
    client = anthropic.Anthropic(api_key=claude_key)
    prompt = get_active_prompt().format(
        date_str=date_str, time_str=datetime.now().strftime('%H:%M'),
        session_number=session_number, transcript=raw_transcript
    )
    message = client.messages.create(
        model=model, max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def polish(raw_transcript, config, date_str, session_number=1, status_callback=None):
    gemini_key = config.get('GEMINI_API_KEY', '').strip()
    claude_key = config.get('CLAUDE_API_KEY', '').strip()
    if gemini_key:
        try:
            return polish_gemini(raw_transcript, gemini_key, date_str, session_number)
        except Exception as e:
            print(f"  Gemini failed ({e}) — falling back to Claude...")
            if status_callback and claude_key:
                status_callback("Gemini failed - using Claude fallback...")
    if claude_key:
        try:
            return polish_claude(raw_transcript, claude_key, date_str, session_number,
                                 config.get('CLAUDE_MODEL', 'claude-sonnet-4-5'))
        except Exception as e:
            print(f"  Claude failed ({e})")
            if status_callback:
                status_callback(_format_provider_failure_message("Claude", e))
            raise
    raise ValueError("No polishing API key configured — add GEMINI_API_KEY or CLAUDE_API_KEY in Settings")

def _build_fallback_section(raw_transcript, session_number, time_str):
    cleaned = (raw_transcript or '').strip()
    return (
        f"## Session {session_number} Notes\n\n"
        f"{cleaned}\n\n"
        f"---\n"
        f"*Session {session_number} · {time_str}*"
    )

def get_session_filename(date_str, session_number):
    return os.path.join(get_recordings_folder(), f"{date_str}_session{session_number}.wav")

def get_processed_marker(audio_path):
    return audio_path.replace('.wav', '.processed')

def is_chunk_processed(audio_path):
    return os.path.exists(get_processed_marker(audio_path))

def mark_chunk_processed(audio_path):
    marker = get_processed_marker(audio_path)
    with open(marker, 'w') as f:
        f.write(datetime.now().isoformat())

def get_next_session_number(date_str):
    folder = get_recordings_folder()
    prefix = f"{date_str}_session"
    nums = []
    for f in os.listdir(folder):
        if f.startswith(prefix) and f.endswith('.wav'):
            try:
                nums.append(int(f[len(prefix):-4]))
            except ValueError:
                pass
    return (max(nums) + 1) if nums else 1

def append_to_notes(section_content, date_str, config=None):
    if config is None:
        config = load_config()
    notes_folder = config.get('NOTES_FOLDER', '').strip() or get_downloads_folder()
    os.makedirs(notes_folder, exist_ok=True)
    filepath = os.path.join(notes_folder, f"{date_str}_notes.md")
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Voice Notes — {date_str}\n\n")
            f.write(section_content)
    else:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write("\n\n---\n\n")
            f.write(section_content)
    print(f"  ✓ Notes updated: {filepath}")
    return filepath

def process_chunk(session_number, date_str=None, status_callback=None):
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    audio_path = get_session_filename(date_str, session_number)
    if not os.path.exists(audio_path):
        print(f"  No audio file for session {session_number}")
        return None
    if is_chunk_processed(audio_path):
        print(f"  Session {session_number} already processed, skipping")
        return None

    config = load_config()
    groq_key = config.get('GROQ_API_KEY', '').strip()
    if not groq_key:
        raise ValueError("Groq API key not configured — open Settings to add it")

    print(f"\n{'━'*40}")
    print(f"  Processing session {session_number} ({date_str})")
    print(f"{'━'*40}")

    if status_callback: status_callback(f"Transcribing session {session_number}...")
    try:
        raw_transcript = transcribe(audio_path, groq_key, status_callback=status_callback)
    except Exception as e:
        print(f"  Groq failed ({e})")
        if status_callback:
            status_callback(_format_provider_failure_message("Groq", e))
        raise

    raw_transcript = str(raw_transcript).strip()
    if not raw_transcript:
        raise ValueError("Transcription returned empty text")

    if status_callback: status_callback("Polishing...")
    time_str = datetime.now().strftime('%H:%M')
    try:
        polished = polish(raw_transcript, config, date_str,
                          session_number=session_number, status_callback=status_callback)
        polished = str(polished).strip() if polished is not None else ""
    except Exception:
        polished = ""

    if not polished:
        polished = _build_fallback_section(raw_transcript, session_number, time_str)

    if status_callback: status_callback("Saving notes...")
    output_path = append_to_notes(polished, date_str, config)
    mark_chunk_processed(audio_path)

    print(f"  ✓ Session {session_number} complete → {output_path}")
    print(f"{'━'*40}\n")
    return output_path

def _process_all_unprocessed_chunks(date_str, status_callback=None):
    folder = get_recordings_folder()
    prefix = f"{date_str}_session"
    session_files = []
    for f in os.listdir(folder):
        if f.startswith(prefix) and f.endswith('.wav'):
            try:
                n = int(f[len(prefix):-4])
                session_files.append((n, os.path.join(folder, f)))
            except ValueError:
                pass
    session_files.sort(key=lambda x: x[0])

    output_path = None
    for session_num, audio_path in session_files:
        if not is_chunk_processed(audio_path):
            try:
                result = process_chunk(session_num, date_str, status_callback=status_callback)
                if result:
                    output_path = result
            except Exception as e:
                print(f"  Session {session_num} failed: {e}")
    return output_path

def cleanup_old_audio():
    config = load_config()
    try:
        retention_days = int(config.get('AUDIO_RETENTION_DAYS', '7'))
    except ValueError:
        retention_days = 7
    folder = get_recordings_folder()
    cutoff = datetime.now() - timedelta(days=retention_days)
    for f in os.listdir(folder):
        if not (f.endswith('.wav') or f.endswith('.processed')):
            continue
        full = os.path.join(folder, f)
        try:
            if os.path.getmtime(full) < cutoff.timestamp():
                os.remove(full)
                print(f"  Cleaned up: {f}")
        except Exception as e:
            print(f"  Could not clean {f}: {e}")

def migrate_legacy_audio():
    folder = get_recordings_folder()
    for f in os.listdir(folder):
        if not f.endswith('.wav') or '_session' in f:
            continue
        name = f[:-4]
        try:
            datetime.strptime(name, '%Y-%m-%d')
        except ValueError:
            continue
        old_path = os.path.join(folder, f)
        new_path = os.path.join(folder, f"{name}_session1.wav")
        if not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f"  Migrated {f} → {name}_session1.wav")

# ═══════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2

def apply_rounded_corners(hwnd):
    if not hwnd:
        return
    try:
        preference = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(preference), ctypes.sizeof(preference)
        )
    except Exception:
        pass

def _get_hwnd(tk_widget):
    raw = tk_widget.winfo_id()
    hwnd = ctypes.windll.user32.GetAncestor(raw, 2)
    return hwnd or raw

class RecordingIndicator:
    def __init__(self):
        self.root = None
        self._visible = False
        self._thread = None
        self._lock = threading.Lock()

    def _build_window(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        self.root.configure(bg='#111111')
        screen_w = self.root.winfo_screenwidth()
        w, h = 280, 38
        x = screen_w // 2 - w // 2
        self.root.geometry(f"{w}x{h}+{x}+{-h}")
        self._x = x
        self._y = -h
        self._w = w
        self._h = h
        self.frame = tk.Frame(self.root, bg='#111111')
        self.frame.pack(fill='both', expand=True)
        self.label = tk.Label(
            self.frame, text="Keep yapping, I'm listening",
            fg='#ffffff', bg='#111111', font=('Segoe UI', 11, 'normal')
        )
        self.label.pack(side='left', padx=(18, 8))
        self.dot = tk.Label(self.frame, text='⬤', fg='#ff3b30', bg='#111111', font=('Segoe UI', 8))
        self.dot.pack(side='left', padx=(0, 16))
        self.root.update()
        apply_rounded_corners(_get_hwnd(self.root))
        self._animate_in()
        self._blink()
        self.root.mainloop()
        self.root = None

    def _animate_in(self):
        target_y = 12
        def step():
            if self._y < target_y:
                self._y += 4
                self.root.geometry(f"{self._w}x{self._h}+{self._x}+{self._y}")
                self.root.after(8, step)
            else:
                self._float()
        self.root.after(10, step)

    def _animate_out(self):
        def step():
            if self._y > -self._h:
                self._y -= 5
                try:
                    self.root.geometry(f"{self._w}x{self._h}+{self._x}+{self._y}")
                    self.root.after(8, step)
                except Exception:
                    pass
            else:
                try:
                    self.root.quit()
                except Exception:
                    pass
        self.root.after(10, step)

    def _float(self):
        self._float_offset = 0
        self._float_dir = 1
        def step():
            if not self._visible:
                return
            self._float_offset += self._float_dir * 0.5
            if self._float_offset >= 4: self._float_dir = -1
            elif self._float_offset <= 0: self._float_dir = 1
            try:
                self.root.geometry(f"{self._w}x{self._h}+{self._x}+{int(12+self._float_offset)}")
                self.root.after(30, step)
            except Exception:
                pass
        self.root.after(30, step)

    def _blink(self):
        self._blink_state = True
        def step():
            if not self._visible:
                return
            self._blink_state = not self._blink_state
            try:
                self.dot.config(fg='#ff3b30' if self._blink_state else '#660000')
                self.root.after(900, step)
            except Exception:
                pass
        self.root.after(900, step)

    def show(self):
        with self._lock:
            if self._visible or (self._thread and self._thread.is_alive()):
                return
            self._visible = True
            self._thread = threading.Thread(target=self._build_window, daemon=True)
            self._thread.start()

    def hide(self):
        with self._lock:
            if not self._visible:
                return
            self._visible = False
            if self.root:
                try:
                    self.root.after(0, self._animate_out)
                except Exception:
                    pass
        time.sleep(0.5)


class ProcessingIndicator:
    def __init__(self):
        self.root = None
        self._visible = False
        self._thread = None
        self._current_text = "Processing..."
        self._lock = threading.Lock()

    def _build_window(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        self.root.configure(bg='#111111')
        screen_w = self.root.winfo_screenwidth()
        w, h = 280, 38
        x = screen_w // 2 - w // 2
        self.root.geometry(f"{w}x{h}+{x}+{-h}")
        self._x = x
        self._y = -h
        self._w = w
        self._h = h
        self.frame = tk.Frame(self.root, bg='#111111')
        self.frame.pack(fill='both', expand=True)
        self.spinner = tk.Label(self.frame, text='◐', fg='#ffffff', bg='#111111', font=('Segoe UI', 10))
        self.spinner.pack(side='left', padx=(16, 8))
        self.label = tk.Label(
            self.frame, text=self._current_text,
            fg='#ffffff', bg='#111111', font=('Segoe UI', 11, 'normal')
        )
        self.label.pack(side='left', padx=(0, 18))
        self.root.update()
        apply_rounded_corners(_get_hwnd(self.root))
        self._animate_in()
        self._spin()
        self.root.mainloop()
        self.root = None

    def _animate_in(self):
        target_y = 12
        def step():
            if self._y < target_y:
                self._y += 4
                self.root.geometry(f"{self._w}x{self._h}+{self._x}+{self._y}")
                self.root.after(8, step)
            else:
                self._float()
        self.root.after(10, step)

    def _animate_out(self):
        def step():
            if self._y > -self._h:
                self._y -= 5
                try:
                    self.root.geometry(f"{self._w}x{self._h}+{self._x}+{self._y}")
                    self.root.after(8, step)
                except Exception:
                    pass
            else:
                try:
                    self.root.quit()
                except Exception:
                    pass
        self.root.after(10, step)

    def _float(self):
        self._float_offset = 0
        self._float_dir = 1
        def step():
            if not self._visible:
                return
            self._float_offset += self._float_dir * 0.5
            if self._float_offset >= 4: self._float_dir = -1
            elif self._float_offset <= 0: self._float_dir = 1
            try:
                self.root.geometry(f"{self._w}x{self._h}+{self._x}+{int(12+self._float_offset)}")
                self.root.after(30, step)
            except Exception:
                pass
        self.root.after(30, step)

    def _spin(self):
        frames = ['◐', '◓', '◑', '◒']
        self._spin_index = 0
        def step():
            if not self._visible:
                return
            self._spin_index = (self._spin_index + 1) % len(frames)
            try:
                self.spinner.config(text=frames[self._spin_index])
                self.root.after(200, step)
            except Exception:
                pass
        self.root.after(200, step)

    def update_status(self, text):
        self._current_text = text
        if self.root:
            try:
                self.root.after(0, lambda: self.label.config(text=text))
            except Exception:
                pass

    def show(self, initial_text="Processing..."):
        with self._lock:
            if self._visible or (self._thread and self._thread.is_alive()):
                return
            self._current_text = initial_text
            self._visible = True
            self._thread = threading.Thread(target=self._build_window, daemon=True)
            self._thread.start()

    def hide(self):
        with self._lock:
            if not self._visible:
                return
            self._visible = False
            if self.root:
                try:
                    self.root.after(0, self._animate_out)
                except Exception:
                    pass
        time.sleep(0.5)


# ═══════════════════════════════════════════════════════════
# TRAY
# ═══════════════════════════════════════════════════════════

def create_tray_icon():
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([4, 4, size-4, size-4], fill='#111111')
    center = size // 2
    dot_size = 10
    draw.ellipse([center-dot_size, center-dot_size, center+dot_size, center+dot_size], fill='#ff3b30')
    return image

class YappTray:
    def __init__(self, on_process_now, on_quit, on_settings, on_open_notes, on_install_update):
        self.on_process_now = on_process_now
        self.on_quit = on_quit
        self.on_settings = on_settings
        self.on_open_notes = on_open_notes
        self.on_install_update = on_install_update
        self.icon = None
        self._update_version = None

    def _menu_items(self):
        items = []
        if self._update_version:
            items.append(pystray.MenuItem(
                f"Install Update (v{self._update_version})",
                self._handle_install_update
            ))
            items.append(pystray.Menu.SEPARATOR)
        items += [
            pystray.MenuItem("Settings", self._handle_settings),
            pystray.MenuItem("Open Notes Folder", self._handle_open_notes),
            pystray.MenuItem("Process Now", self._handle_process_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit Application", self._handle_quit),
        ]
        return items

    def _handle_install_update(self, icon, item):
        threading.Thread(target=self.on_install_update, daemon=True).start()

    def _handle_process_now(self, icon, item):
        threading.Thread(target=self.on_process_now, daemon=True).start()

    def _handle_settings(self, icon, item):
        self.on_settings()

    def _handle_open_notes(self, icon, item):
        threading.Thread(target=self.on_open_notes, daemon=True).start()

    def _handle_quit(self, icon, item):
        self.icon.stop()
        self.on_quit()

    def set_recording(self, is_recording):
        pass

    def set_update_available(self, version):
        self._update_version = version
        if self.icon:
            self.icon.update_menu()

    def start(self):
        try:
            image = create_tray_icon()
            self.icon = pystray.Icon(
                "Yapp Forever", image, "Yapp Forever",
                menu=pystray.Menu(self._menu_items)
            )
            self.icon.run()
        except Exception as e:
            print(f"Tray error: {e}")

    def stop(self):
        if self.icon:
            self.icon.stop()


# ═══════════════════════════════════════════════════════════
# SETUP / SETTINGS WINDOW
# ═══════════════════════════════════════════════════════════

BG = "#FAFAF8"
CARD_BG = "#FFFFFF"
TEXT_PRIMARY = "#1A1A1A"
TEXT_SECONDARY = "#4A4A4A"
TEXT_TERTIARY = "#707070"
ACCENT = "#ff3b30"
LINK = "#0066CC"
BORDER = "#E0E0DC"
OVERLAY = "#000000"

def save_config(values):
    config_path = get_config_path()
    with open(config_path, 'w') as f:
        f.write(f"GROQ_API_KEY = {values['groq']}\n")
        f.write(f"CLAUDE_API_KEY = {values['claude']}\n")
        f.write(f"GEMINI_API_KEY = {values['gemini']}\n")
        f.write(f"NOTES_FOLDER = {values['notes_folder']}\n")
        f.write(f"AUDIO_INPUT_DEVICE = {values['audio_input_device']}\n")
        f.write(f"AUTO_PROCESS_TIME = {values['time']}\n")
        f.write(f"AUDIO_RETENTION_DAYS = {values.get('retention_days', '7') or '7'}\n")
        f.write(f"RECORD_HOTKEY = {values.get('record_hotkey', 'ctrl+shift+alt+s') or 'ctrl+shift+alt+s'}\n")
        f.write(f"PROCESS_HOTKEY = {values.get('process_hotkey', 'ctrl+shift+alt+p') or 'ctrl+shift+alt+p'}\n")

def get_input_device_options(current_value=''):
    options = [SYSTEM_DEFAULT_INPUT]
    seen = {SYSTEM_DEFAULT_INPUT}
    try:
        for _, name in _iter_input_device_candidates():
            if name and name not in seen:
                options.append(name)
                seen.add(name)
    except Exception:
        pass
    current_value = _clean_device_name(current_value)
    if current_value and current_value not in seen:
        options.append(current_value)
    return options

def is_config_complete():
    config = load_config()
    has_groq = config.get('GROQ_API_KEY', '') not in ['', 'paste_your_groq_key_here']
    has_polish = (config.get('GEMINI_API_KEY', '').strip() != '' or
                  config.get('CLAUDE_API_KEY', '').strip() != '')
    return has_groq and has_polish

def show_quickstart_modal(root):
    overlay = ctk.CTkFrame(root, fg_color=OVERLAY, corner_radius=0)
    overlay.place(x=0, y=0, relwidth=1, relheight=1)
    card = ctk.CTkFrame(overlay, fg_color=BG, border_color=BORDER, border_width=1, corner_radius=14)
    card.place(relx=0.5, rely=0.5, anchor='center', relwidth=0.88, relheight=0.88)
    ctk.CTkButton(card, text="✕", width=28, height=28, fg_color="transparent",
                  hover_color=BORDER, text_color=TEXT_TERTIARY, font=("Segoe UI", 14),
                  corner_radius=6, command=lambda: overlay.destroy()
                  ).place(relx=1.0, rely=0.0, anchor='ne', x=-12, y=12)
    content = ctk.CTkScrollableFrame(card, fg_color="transparent",
                                      scrollbar_button_color=BORDER,
                                      scrollbar_button_hover_color=TEXT_TERTIARY)
    content.pack(fill='both', expand=True, padx=28, pady=(44, 24))
    ctk.CTkLabel(content, text="Quick Start", font=("Segoe UI", 18, 'bold'),
                 text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0, 6))
    ctk.CTkLabel(content, text="Four things to know and you're ready.",
                 font=("Segoe UI", 12), text_color=TEXT_SECONDARY).pack(anchor='w', pady=(0, 20))
    def item(heading, body):
        ctk.CTkLabel(content, text=heading, font=("Segoe UI", 11, 'bold'),
                     text_color=ACCENT).pack(anchor='w', pady=(4, 4))
        ctk.CTkLabel(content, text=body, font=("Segoe UI", 12), text_color=TEXT_SECONDARY,
                     wraplength=380, justify='left').pack(anchor='w', pady=(0, 14))
    item("Record hotkey", "Press to start recording. Press again to pause or resume. Your audio accumulates in the current session.")
    item("Process hotkey", "Press to send the current session to be transcribed and polished. If you're recording, it pauses first automatically. The app stays running — start a new session whenever you're ready.")
    item("Each session is a chunk", "Every time you press process, that session is appended to today's notes file with a smart AI-generated heading. Sessions build up through the day into one clean document.")
    item("The tray icon is your control panel", "Right-click the small icon in your system tray to access Settings, Process Now, Open Notes, or Quit.")
    guide_link = ctk.CTkLabel(content, text="Read the full guide →",
                               font=("Segoe UI", 11, 'underline'), text_color=LINK, cursor='hand2')
    guide_link.pack(anchor='w', pady=(8, 0))
    guide_link.bind("<Button-1>", lambda e: webbrowser.open("https://azdhan.github.io/yapp-forever-site/guide.html"))

def show_why_modal(root):
    overlay = ctk.CTkFrame(root, fg_color=OVERLAY, corner_radius=0)
    overlay.place(x=0, y=0, relwidth=1, relheight=1)
    card = ctk.CTkFrame(overlay, fg_color=BG, border_color=BORDER, border_width=1, corner_radius=14)
    card.place(relx=0.5, rely=0.5, anchor='center', relwidth=0.88, relheight=0.85)
    ctk.CTkButton(card, text="✕", width=28, height=28, fg_color="transparent",
                  hover_color=BORDER, text_color=TEXT_TERTIARY, font=("Segoe UI", 14),
                  corner_radius=6, command=lambda: overlay.destroy()
                  ).place(relx=1.0, rely=0.0, anchor='ne', x=-12, y=12)
    content = ctk.CTkScrollableFrame(card, fg_color="transparent",
                                      scrollbar_button_color=BORDER,
                                      scrollbar_button_hover_color=TEXT_TERTIARY)
    content.pack(fill='both', expand=True, padx=28, pady=(44, 24))
    ctk.CTkLabel(content, text="Why Yapp Forever", font=("Segoe UI", 18, 'bold'),
                 text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0, 18))
    def paragraph(heading, body):
        ctk.CTkLabel(content, text=heading, font=("Segoe UI", 11, 'bold'),
                     text_color=ACCENT).pack(anchor='w', pady=(6, 4))
        ctk.CTkLabel(content, text=body, font=("Segoe UI", 12), text_color=TEXT_SECONDARY,
                     wraplength=360, justify='left').pack(anchor='w', pady=(0, 14))
    paragraph("Why Yapp Forever:", "Information is everywhere. Collecting it shouldn't be note-making. What's rare is what you make of it — the thoughts and emotions it triggered, the questions that it raised.")
    paragraph("How it works:", "Click a hotkey, speak your thoughts out loud. Each session saves independently. Transcribed and structured automatically. Stored permanently on your device.")
    paragraph("Why voice notes:", "When you speak, you can only say what's actually in your mind. No copy-pasted information. No filler. Just real thought.")
    paragraph("Why yapping matters:", "One day you'll want to know how your thinking has changed. It'll all be there. So, Yapp Forever.")

def show_setup(on_complete=None, is_settings=False):
    ctk.set_appearance_mode("light")
    config = load_config()
    root = ctk.CTk(fg_color=BG)
    root.title("Yapp Forever")
    root.resizable(False, False)
    w, h = 520, 840
    root.geometry(f"{w}x{h}+{root.winfo_screenwidth()//2-w//2}+{root.winfo_screenheight()//2-h//2}")
    scrollable = ctk.CTkScrollableFrame(root, fg_color=BG, scrollbar_button_color=BORDER,
                                         scrollbar_button_hover_color=TEXT_TERTIARY, corner_radius=0)
    scrollable.pack(fill='both', expand=True)
    inner = ctk.CTkFrame(scrollable, fg_color="transparent")
    inner.pack(fill='x', padx=30, pady=(30, 24))
    ctk.CTkLabel(inner, text="Yapp Forever", font=("Segoe UI", 24, 'bold'),
                 text_color=TEXT_PRIMARY).pack(anchor='w')
    ctk.CTkLabel(inner, text="Speak your mind. Keep it forever.", font=("Segoe UI", 13),
                 text_color=TEXT_SECONDARY).pack(anchor='w', pady=(4, 10))
    links_row = ctk.CTkFrame(inner, fg_color="transparent")
    links_row.pack(anchor='w', pady=(0, 20))
    qs = ctk.CTkLabel(links_row, text="Quick start →", font=("Segoe UI", 11, 'underline'),
                      text_color=LINK, cursor='hand2')
    qs.pack(side='left', padx=(0, 16))
    qs.bind("<Button-1>", lambda e: show_quickstart_modal(root))
    why = ctk.CTkLabel(links_row, text="Why I built this →", font=("Segoe UI", 11, 'underline'),
                       text_color=LINK, cursor='hand2')
    why.pack(side='left')
    why.bind("<Button-1>", lambda e: show_why_modal(root))
    ctk.CTkFrame(inner, fg_color=BORDER, height=1).pack(fill='x', pady=(0, 20))

    entries = {}

    def make_link(parent, text, url):
        link = ctk.CTkLabel(parent, text=text, font=("Segoe UI", 11), text_color=LINK, cursor='hand2')
        link.bind("<Button-1>", lambda e: webbrowser.open(url))
        return link

    def add_field(parent, key, label, helper, link_text, link_url, default='', show=False):
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(fill='x', pady=(0, 14))
        ctk.CTkLabel(block, text=label, font=("Segoe UI", 12, 'bold'),
                     text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0, 6))
        entry = ctk.CTkEntry(block, fg_color=CARD_BG, border_color=BORDER, border_width=1,
                              corner_radius=6, height=38, font=("Segoe UI", 12),
                              text_color=TEXT_PRIMARY, show='•' if show else '')
        entry.pack(fill='x')
        entry.insert(0, default)
        helper_row = ctk.CTkFrame(block, fg_color="transparent")
        helper_row.pack(anchor='w', pady=(6, 0), fill='x')
        ctk.CTkLabel(helper_row, text=helper, font=("Segoe UI", 11), text_color=TEXT_TERTIARY,
                     wraplength=420, justify='left').pack(side='left')
        if link_text and link_url:
            make_link(helper_row, " " + link_text, link_url).pack(side='left')
        entries[key] = entry

    def add_path_field(parent, key, label, helper, default=''):
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(fill='x', pady=(0, 14))
        ctk.CTkLabel(block, text=label, font=("Segoe UI", 12, 'bold'),
                     text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0, 6))
        row = ctk.CTkFrame(block, fg_color="transparent")
        row.pack(fill='x')
        entry = ctk.CTkEntry(row, fg_color=CARD_BG, border_color=BORDER, border_width=1,
                              corner_radius=6, height=38, font=("Segoe UI", 12), text_color=TEXT_PRIMARY)
        entry.pack(side='left', fill='x', expand=True)
        entry.insert(0, default)
        def browse():
            path = filedialog.askdirectory(parent=root)
            if path:
                entry.delete(0, 'end')
                entry.insert(0, path.replace('/', '\\'))
        ctk.CTkButton(row, text="Browse", width=80, height=38, fg_color=CARD_BG,
                      hover_color=BORDER, border_color=BORDER, border_width=1, corner_radius=6,
                      text_color=TEXT_PRIMARY, font=("Segoe UI", 11), command=browse
                      ).pack(side='left', padx=(8, 0))
        ctk.CTkLabel(block, text=helper, font=("Segoe UI", 11), text_color=TEXT_TERTIARY,
                     wraplength=440, justify='left').pack(anchor='w', pady=(6, 0))
        entries[key] = entry

    def add_option_field(parent, key, label, helper, options, default=''):
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(fill='x', pady=(0, 14))
        ctk.CTkLabel(block, text=label, font=("Segoe UI", 12, 'bold'),
                     text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0, 6))
        selected = default if default in options else options[0]
        option = ctk.CTkOptionMenu(
            block, values=options, fg_color=CARD_BG, button_color=BORDER,
            button_hover_color=TEXT_TERTIARY, dropdown_fg_color=CARD_BG,
            dropdown_hover_color=BORDER, text_color=TEXT_PRIMARY,
            dropdown_text_color=TEXT_PRIMARY, corner_radius=6, height=38, font=("Segoe UI", 12)
        )
        option.pack(fill='x')
        option.set(selected)
        ctk.CTkLabel(block, text=helper, font=("Segoe UI", 11), text_color=TEXT_TERTIARY,
                     wraplength=440, justify='left').pack(anchor='w', pady=(6, 0))
        entries[key] = option

    def add_hotkey_field(parent, key, label, helper, default=''):
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(fill='x', pady=(0, 14))
        ctk.CTkLabel(block, text=label, font=("Segoe UI", 12, 'bold'),
                     text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0, 6))
        current = {'value': default or ''}
        def start_capture():
            btn.configure(text="⌨  Press your hotkey...", fg_color=ACCENT, state='disabled')
            def capture():
                try:
                    hotkey = keyboard.read_hotkey(suppress=False)
                    current['value'] = hotkey
                    root.after(0, lambda: btn.configure(
                        text=hotkey, fg_color=TEXT_PRIMARY, state='normal'))
                except Exception:
                    root.after(0, lambda: btn.configure(
                        text=current['value'] or 'Click to set hotkey',
                        fg_color=TEXT_PRIMARY, state='normal'))
            threading.Thread(target=capture, daemon=True).start()
        btn = ctk.CTkButton(block, text=default or 'Click to set hotkey',
                            command=start_capture, fg_color=TEXT_PRIMARY,
                            hover_color=ACCENT, text_color='white',
                            corner_radius=6, height=38, font=("Segoe UI", 12))
        btn.pack(fill='x')
        ctk.CTkLabel(block, text=helper, font=("Segoe UI", 11), text_color=TEXT_TERTIARY,
                     wraplength=440, justify='left').pack(anchor='w', pady=(6, 0))
        class _Proxy:
            def get(self):
                return current['value']
        entries[key] = _Proxy()

    def add_textarea_field(parent, key, label, helper, default='', height=180):
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(fill='x', pady=(0, 14))
        ctk.CTkLabel(block, text=label, font=("Segoe UI", 12, 'bold'),
                     text_color=TEXT_PRIMARY).pack(anchor='w', pady=(0, 6))
        textbox = ctk.CTkTextbox(block, height=height, fg_color=CARD_BG, border_color=BORDER,
                                  border_width=1, corner_radius=6, font=("Courier New", 10),
                                  text_color=TEXT_PRIMARY)
        textbox.pack(fill='x')
        if default:
            textbox.insert('0.0', default)
        ctk.CTkLabel(block, text=helper, font=("Segoe UI", 11), text_color=TEXT_TERTIARY,
                     wraplength=440, justify='left').pack(anchor='w', pady=(6, 0))
        class _Proxy:
            def get(self):
                return textbox.get('0.0', 'end').strip()
        entries[key] = _Proxy()

    def section_label(text):
        ctk.CTkLabel(inner, text=text, font=("Segoe UI", 10, 'bold'),
                     text_color=TEXT_TERTIARY).pack(anchor='w', pady=(8, 10))

    section_label("API KEYS")
    add_field(inner, 'groq', 'Groq API Key',
              'Turns your spoken words into raw transcript. Free at',
              'console.groq.com', 'https://console.groq.com',
              default=config.get('GROQ_API_KEY', ''), show=True)
    add_field(inner, 'claude', 'Claude API Key',
              'Shapes your transcript into structured thought. Paid — get yours at',
              'console.anthropic.com', 'https://console.anthropic.com',
              default=config.get('CLAUDE_API_KEY', ''), show=True)
    add_field(inner, 'gemini', 'Gemini API Key',
              "Free polishing option. Get yours at",
              'aistudio.google.com', 'https://aistudio.google.com',
              default=config.get('GEMINI_API_KEY', ''), show=True)

    section_label("STORAGE")
    add_path_field(inner, 'notes_folder', 'Notes Folder',
                   'Choose any folder for your notes. Point it to your Obsidian vault or leave blank for Downloads.',
                   default=config.get('NOTES_FOLDER', ''))

    section_label("AUDIO")
    add_option_field(
        inner, 'audio_input_device', 'Mic Input',
        'Choose System Default to follow Windows, or lock Yapp Forever to a specific microphone.',
        get_input_device_options(config.get('AUDIO_INPUT_DEVICE', SYSTEM_DEFAULT_INPUT)),
        default=config.get('AUDIO_INPUT_DEVICE', SYSTEM_DEFAULT_INPUT) or SYSTEM_DEFAULT_INPUT
    )
    add_field(inner, 'retention_days', 'Audio Retention (days)',
              'Audio files older than this are auto-deleted. Your text notes are never deleted.',
              '', '', default=config.get('AUDIO_RETENTION_DAYS', '7'))

    section_label("SCHEDULE")
    add_field(inner, 'time', 'Auto-Process Time',
              'Any unprocessed sessions are automatically transcribed daily at this time (24hr format).',
              '', '', default=config.get('AUTO_PROCESS_TIME', '23:55'))

    section_label("HOTKEYS")
    add_hotkey_field(inner, 'record_hotkey', 'Record / Pause Hotkey',
                     'Click, then press your desired key combination. Toggles recording on and off.',
                     default=config.get('RECORD_HOTKEY', 'ctrl+shift+alt+s'))
    add_hotkey_field(inner, 'process_hotkey', 'Process Now Hotkey',
                     'Click, then press your desired key combination. Sends the current session to transcription and polishing.',
                     default=config.get('PROCESS_HOTKEY', 'ctrl+shift+alt+p'))

    section_label("AI PROMPT")
    add_textarea_field(inner, 'polish_prompt', 'Polishing Prompt',
                       'Customise how the AI polishes your notes. Available variables: {date_str}, {time_str}, {session_number}, {transcript}. Leave blank to use the built-in default.',
                       default=load_custom_prompt(), height=180)

    status_var = ctk.StringVar()
    ctk.CTkLabel(inner, textvariable=status_var, font=("Segoe UI", 10),
                 text_color=ACCENT).pack(pady=(14, 10))

    def on_save():
        values = {k: entries[k].get().strip() for k in entries}
        if not values['groq'] or (not values['gemini'] and not values['claude']):
            status_var.set("⚠ Groq key required, plus Gemini or Claude API key.")
            return
        save_config(values)
        save_custom_prompt(values.get('polish_prompt', ''))
        status_var.set("✓ Saved.")
        if on_complete:
            root.after(600, lambda: [root.destroy(), on_complete()])
        else:
            root.after(600, root.destroy)

    ctk.CTkButton(inner, text="Save Settings" if is_settings else "Save & Start",
                  height=44, font=("Segoe UI", 12, 'bold'),
                  fg_color=TEXT_PRIMARY, hover_color=ACCENT, text_color='#FFFFFF',
                  corner_radius=8, command=on_save).pack(fill='x', pady=(0, 18))
    ctk.CTkLabel(inner, text="Yapp Forever", font=("Segoe UI", 9),
                 text_color=TEXT_TERTIARY).pack()
    root.mainloop()

# ═══════════════════════════════════════════════════════════
# AUTO-UPDATE
# ═══════════════════════════════════════════════════════════

_pending_installer_path = None

def _parse_version(v):
    try:
        return tuple(int(x) for x in v.lstrip('v').split('.'))
    except Exception:
        return (0,)

def check_for_update():
    import urllib.request, json, tempfile
    global _pending_installer_path
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'YappForever'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        latest_tag = data.get('tag_name', '')
        if not latest_tag:
            return
        latest_version = latest_tag.lstrip('v')
        if _parse_version(latest_version) <= _parse_version(APP_VERSION):
            print(f"  App is up to date (v{APP_VERSION})")
            return

        # Find the installer .exe in the release assets
        installer_url = None
        for asset in data.get('assets', []):
            name = asset['name'].lower()
            if name.endswith('.exe') and 'setup' in name:
                installer_url = asset['browser_download_url']
                break
        if not installer_url:
            print(f"  Update v{latest_version} found but no installer asset attached yet.")
            return

        print(f"  Update available: v{latest_version} (current: v{APP_VERSION})")
        notify_windows("Yapp Forever", f"Update v{latest_version} found — downloading in background...")

        tmp_dir = tempfile.mkdtemp(prefix="yapp_update_")
        installer_path = os.path.join(tmp_dir, f"YappForever-Setup-{latest_version}.exe")

        print(f"  Downloading update to {installer_path}...")
        urllib.request.urlretrieve(installer_url, installer_path)
        print(f"  Download complete.")

        _pending_installer_path = installer_path
        notify_windows(
            "Yapp Forever — Update Ready",
            f"v{latest_version} is ready to install. Right-click the tray icon and choose 'Install Update'."
        )
        if tray:
            tray.set_update_available(latest_version)

    except Exception as e:
        print(f"  Update check failed: {e}")

def on_install_update():
    global _pending_installer_path
    if not _pending_installer_path or not os.path.exists(_pending_installer_path):
        show_status_notice("Update file not found — please restart to re-check.", duration=3)
        return
    notify_windows("Yapp Forever", "Installing update... The app will restart automatically.")
    time.sleep(2)
    subprocess.Popen([
        _pending_installer_path,
        '/VERYSILENT', '/NORESTART', '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS'
    ])

# ═══════════════════════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════════════════════

def notify_windows(title, message):
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=8, threaded=True)
    except Exception:
        print(f"  [{title}] {message}")

def get_next_run_time(config):
    time_str = config.get('AUTO_PROCESS_TIME', '23:55')
    hour, minute = map(int, time_str.split(':'))
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target

def check_missed_yesterday(config):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    folder = get_recordings_folder()
    prefix = f"{yesterday}_session"
    has_unprocessed = any(
        f.startswith(prefix) and f.endswith('.wav') and
        not is_chunk_processed(os.path.join(folder, f))
        for f in os.listdir(folder)
    )
    if has_unprocessed:
        print(f"  Found unprocessed sessions from yesterday ({yesterday}), processing...")
        _process_all_unprocessed_chunks(yesterday)

def run_scheduler():
    config = load_config()
    print(f"{'━'*40}")
    print(f"  Yapp Forever — Scheduler Running")
    print(f"  Auto-process time: {config.get('AUTO_PROCESS_TIME', '23:55')}")
    print(f"{'━'*40}")
    check_missed_yesterday(config)
    while True:
        config = load_config()
        next_run = get_next_run_time(config)
        wait_seconds = (next_run - datetime.now()).total_seconds()
        print(f"  Next auto-process: {next_run.strftime('%Y-%m-%d %H:%M')} "
              f"({int(wait_seconds//3600)}h {int((wait_seconds%3600)//60)}m)")
        time.sleep(wait_seconds)
        print(f"\n  Triggering end-of-day processing...")
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            output_path = _process_all_unprocessed_chunks(date_str)
            if output_path:
                notify_windows("Yapp Forever", "Today's notes are ready.")
        except Exception as e:
            print(f"  Pipeline error: {e}")
            notify_windows("Yapp Forever — Error", f"Pipeline failed: {str(e)[:80]}")
        time.sleep(60)

# ═══════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════

recording = False
audio_chunks = []
stream = None
current_session_number = 1
indicator = None
tray = None
audio_lock = threading.Lock()
current_input_device_label = SYSTEM_DEFAULT_INPUT

def get_current_session_filename():
    return get_session_filename(datetime.now().strftime('%Y-%m-%d'), current_session_number)

def get_configured_input_device(config=None):
    if config is None:
        config = load_config()
    selected = config.get('AUDIO_INPUT_DEVICE', SYSTEM_DEFAULT_INPUT).strip()
    return selected or SYSTEM_DEFAULT_INPUT

def resolve_input_device(selected_name):
    selected_name = _clean_device_name(selected_name or SYSTEM_DEFAULT_INPUT)
    if selected_name == SYSTEM_DEFAULT_INPUT:
        default_input = sd.default.device[0]
        try:
            if default_input is not None and default_input >= 0:
                default_name = _clean_device_name(sd.query_devices(default_input)['name'])
                if _should_offer_input_device(default_name):
                    return None, default_name
        except Exception:
            pass
        return None, SYSTEM_DEFAULT_INPUT
    for index, device_name in _iter_input_device_candidates():
        if device_name == selected_name:
            return index, selected_name
    return None, f"{selected_name} unavailable - using System Default"

def show_status_notice(message, duration=1.8):
    pill = ProcessingIndicator()
    pill.show(message)
    time.sleep(duration)
    pill.hide()

def _open_input_stream(device):
    global SAMPLE_RATE
    wasapi_candidates = []
    try:
        hostapis = sd.query_hostapis()
        for api_idx, api in enumerate(hostapis):
            if 'WASAPI' in api['name']:
                for dev_idx, dev in enumerate(sd.query_devices()):
                    if dev['hostapi'] == api_idx and dev['max_input_channels'] > 0:
                        wasapi_candidates.append(dev_idx)
    except Exception:
        pass
    seen = set()
    candidates = []
    for d in wasapi_candidates + ([device] if device is not None else []) + [None]:
        key = d if d is not None else 'default'
        if key not in seen:
            seen.add(key)
            candidates.append(d)
    failures = []
    for dev in candidates:
        rates = [SAMPLE_RATE]
        try:
            native = int(sd.query_devices(dev)['default_samplerate'])
            if native not in rates:
                rates.append(native)
        except Exception:
            if 48000 not in rates:
                rates.append(48000)
        try:
            dev_name = sd.query_devices(dev)['name'] if dev is not None else 'system default'
        except Exception:
            dev_name = str(dev)
        for rate in rates:
            for latency in [None, 'high']:
                try:
                    kwargs = dict(samplerate=rate, channels=1, callback=audio_callback, device=dev)
                    if latency:
                        kwargs['latency'] = latency
                    s = sd.InputStream(**kwargs)
                    if rate != SAMPLE_RATE:
                        print(f"  Note: opened at {rate}Hz (device native, was {SAMPLE_RATE}Hz)")
                        SAMPLE_RATE = rate
                    return s
                except sd.PortAudioError as e:
                    failures.append(f"  Audio open failed [{dev_name}, {rate}Hz, latency={latency}]: {e}")
    for msg in failures:
        print(msg)
    return None

def restart_input_stream(config=None, show_notice=False):
    global stream, current_input_device_label
    selected_name = get_configured_input_device(config)
    device, active_label = resolve_input_device(selected_name)
    if stream:
        try:
            stream.stop()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass
    new_stream = _open_input_stream(device)
    if new_stream is None:
        print("WARNING: Could not open any microphone input.")
        notify_windows("Yapp Forever", "Could not open microphone. Close other audio apps then press the record hotkey to retry.")
        current_input_device_label = "No microphone available"
        return current_input_device_label
    stream = new_stream
    stream.start()
    current_input_device_label = active_label
    print(f"Active input: {active_label}")
    if show_notice:
        show_status_notice(f"Mic input changed: {active_label}")
    return active_label

def apply_updated_audio_input(previous_setting):
    config = load_config()
    new_setting = get_configured_input_device(config)
    if new_setting == previous_setting:
        return
    if recording:
        flush_audio_chunks()
    restart_input_stream(config=config, show_notice=True)

def apply_updated_hotkeys():
    global RECORD_HOTKEY, PROCESS_HOTKEY
    config = load_config()
    RECORD_HOTKEY = (config.get('RECORD_HOTKEY', 'ctrl+shift+alt+s') or 'ctrl+shift+alt+s').lower()
    PROCESS_HOTKEY = (config.get('PROCESS_HOTKEY', 'ctrl+shift+alt+p') or 'ctrl+shift+alt+p').lower()
    print(f"Hotkeys: record={RECORD_HOTKEY}  process={PROCESS_HOTKEY}")

def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"Audio stream status: {status}")
    if recording:
        with audio_lock:
            audio_chunks.append(indata.copy())

def save_audio(filepath, chunks):
    if not chunks:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    normalized = []
    for chunk in chunks:
        if chunk.ndim == 1:
            chunk = chunk.reshape(-1, 1)
        normalized.append(chunk.astype(np.float32))
    new_audio = np.concatenate(normalized, axis=0)
    if os.path.exists(filepath):
        rate, existing = wav_read(filepath)
        if existing.ndim == 1:
            existing = existing.reshape(-1, 1)
        if existing.dtype == np.int16:
            existing = existing.astype(np.float32) / 32768.0
        elif existing.dtype == np.int32:
            existing = existing.astype(np.float32) / 2147483648.0
        else:
            existing = existing.astype(np.float32)
        new_audio = np.concatenate([existing, new_audio], axis=0)
    wav_write(filepath, SAMPLE_RATE, new_audio)

def flush_audio_chunks():
    filepath = get_current_session_filename()
    with audio_lock:
        if not audio_chunks:
            return False
        pending_chunks = list(audio_chunks)
        audio_chunks.clear()
    save_audio(filepath, pending_chunks)
    return True

def media_play_pause():
    VK_MEDIA_PLAY_PAUSE = 0xB3
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)

def _do_process_now():
    global recording, indicator, current_session_number
    was_recording = recording
    if was_recording:
        recording = False
        indicator.hide()
        indicator = RecordingIndicator()
        media_play_pause()
        if tray:
            tray.set_recording(False)

    wrote = flush_audio_chunks()
    session_to_process = current_session_number
    date_str = datetime.now().strftime('%Y-%m-%d')
    audio_path = get_session_filename(date_str, session_to_process)

    if not wrote and not os.path.exists(audio_path):
        show_status_notice("No audio to process", duration=1.5)
        return

    current_session_number += 1
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatching session {session_to_process} for processing → next session: {current_session_number}")
    threading.Thread(target=_run_process_background,
                     args=(session_to_process, date_str), daemon=True).start()

def _run_process_background(session_number, date_str):
    pill = ProcessingIndicator()
    pill.show(f"Processing session {session_number}...")
    try:
        output_path = process_chunk(session_number, date_str, status_callback=pill.update_status)
        pill.update_status("✓ Notes saved" if output_path else "Nothing to process")
        time.sleep(1.8)
    except Exception as e:
        pill.update_status(f"⚠ {str(e)[:45]}")
        time.sleep(4)
        print(f"Pipeline error (session {session_number}): {e}")
    finally:
        pill.hide()

def keyboard_listener():
    global recording, indicator
    while True:
        if keyboard.is_pressed(RECORD_HOTKEY):
            if stream is None:
                restart_input_stream()
                time.sleep(0.3)
                if stream is None:
                    continue
            recording = not recording
            if recording:
                media_play_pause()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ● Recording (session {current_session_number})...")
                indicator.show()
                if tray:
                    tray.set_recording(True)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] || Paused")
                indicator.hide()
                indicator = RecordingIndicator()
                media_play_pause()
                flush_audio_chunks()
                if tray:
                    tray.set_recording(False)
            time.sleep(0.3)

        if keyboard.is_pressed(PROCESS_HOTKEY):
            _do_process_now()
            time.sleep(0.3)

        time.sleep(0.01)

def on_process_now():
    _do_process_now()

def on_quit():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Quitting Yapp Forever...")
    flush_audio_chunks()
    if stream:
        stream.stop()
    os._exit(0)

def on_settings():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Opening Settings...")
    _ui_queue.put('settings')

def on_open_notes():
    config = load_config()
    notes_folder = config.get('NOTES_FOLDER', '').strip() or get_downloads_folder()
    os.makedirs(notes_folder, exist_ok=True)
    os.startfile(notes_folder)


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    config_path = os.path.join(appdata, 'YappForever', 'config.txt')
    ensure_start_menu_shortcut()

    if not os.path.exists(config_path):
        print("First-time setup required — launching setup window...")
        show_setup()
        if not os.path.exists(config_path):
            print("Setup not completed. Exiting.")
            sys.exit(0)

    migrate_legacy_audio()
    cleanup_old_audio()

    date_str = datetime.now().strftime('%Y-%m-%d')
    current_session_number = get_next_session_number(date_str)

    apply_updated_hotkeys()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("        Yapp Forever")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Date:    {date_str}")
    print(f"  Session: {current_session_number}")
    print(f"  {RECORD_HOTKEY} — Record / Pause")
    print(f"  {PROCESS_HOTKEY} — Process Now")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    restart_input_stream(load_config())

    _warmup = tk.Tk()
    _warmup.withdraw()
    _warmup.after(100, _warmup.destroy)
    _warmup.mainloop()

    indicator = RecordingIndicator()

    threading.Thread(target=run_scheduler, daemon=True).start()
    threading.Thread(target=keyboard_listener, daemon=True).start()
    threading.Thread(target=lambda: (time.sleep(10), check_for_update()), daemon=True).start()

    tray = YappTray(on_process_now=on_process_now, on_quit=on_quit,
                    on_settings=on_settings, on_open_notes=on_open_notes,
                    on_install_update=on_install_update)
    tray_thread = threading.Thread(target=tray.start, daemon=True)
    tray_thread.start()

    notify_windows("Yapp Forever",
                   f"Running. {RECORD_HOTKEY.upper()} to record · {PROCESS_HOTKEY.upper()} to process")

    while tray_thread.is_alive():
        try:
            task = _ui_queue.get(timeout=0.5)
            if task == 'settings':
                tk._default_root = None
                previous_setting = get_configured_input_device(load_config())
                show_setup(is_settings=True)
                apply_updated_audio_input(previous_setting)
                apply_updated_hotkeys()
        except queue.Empty:
            pass
