import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk, Scale
import speech_recognition as sr
from deep_translator import GoogleTranslator
import threading
import pyttsx3
import time
from datetime import datetime
import sv_ttk


class SmoothTextWidget(scrolledtext.ScrolledText):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_configure("fade", foreground=self.cget("fg"))
        self.tag_configure(
            "english", foreground="#007acc", font=("Segoe UI", 11, "bold")
        )
        self.tag_configure(
            "urdu", foreground="#4b8b3b", font=("Jameel Noori Nastaleeq", 12)
        )
        self.tag_configure(
            "timestamp", foreground="#999999", font=("Segoe UI", 9, "italic")
        )

    def smooth_insert(self, text, duration=1000, step_count=20):
        lines = text.split("\n")
        for line in lines:
            if not line:
                continue
            timestamp = time.strftime("%H:%M:%S")
            if "English:" in line:
                self.insert(tk.END, f"[{timestamp}] ", "timestamp")
                self.insert(tk.END, line.split("English:")[1].strip() + "\n", "english")
            elif "Urdu:" in line:
                self.insert(tk.END, f"[{timestamp}] ", "timestamp")
                self.insert(tk.END, line.split("Urdu:")[1].strip() + "\n", "urdu")
            else:
                self.insert(tk.END, line + "\n", "fade")


class LiveSpeechToTextTranslatorApp:
    def __init__(self, master=None):
        self.root = master or tk.Tk()
        self.root.title("🎙 Live Speech-to-Text Converter")
        self.root.geometry("960x760")
        self.root.minsize(850, 700)

        # Recognizer and translator
        self.recognizer = sr.Recognizer()
        self.translator = GoogleTranslator()
        self.transcription_history = []
        self.continuous_mode = False
        self.current_lang = tk.StringVar(value="en-US")
        self.tts_engine = pyttsx3.init()

        # Voice settings
        self.voice_rate = tk.IntVar(value=150)
        self.voice_volume = tk.DoubleVar(value=0.9)

        self.create_ui()
        sv_ttk.set_theme("light")

    def create_ui(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(
            main_frame,
            text="🌐 Live Speech-to-Text Converter",
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(0, 15))

        lang_frame = ttk.LabelFrame(
            main_frame,
            text="  🗣️ LANGUAGE SETTINGS  ",
            padding=(20, 15),
            style="Card.TLabelframe",
        )
        lang_frame.pack(fill=tk.X, pady=(0, 15), padx=20)

        # Current language display with icon
        self.lang_display = ttk.Label(
            lang_frame,
            text="● Current Input: ENGLISH",
            font=("Segoe UI", 11, "bold"),
            foreground="#3b82f6",  # Blue accent color
            style="LangDisplay.TLabel",
        )
        self.lang_display.pack(pady=(0, 10))

        # Language toggle button with modern styling
        self.lang_btn = ttk.Button(
            lang_frame,
            text="🔄  SWITCH TO URDU",
            command=self.toggle_language,
            style="Accent.TButton",
            width=50,
            cursor="hand2",
        )
        self.lang_btn.pack(pady=(0, 5), ipady=5)

        # Voice settings
        voice_frame = ttk.LabelFrame(main_frame, text="🔊 Voice Settings", padding=15)
        voice_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(voice_frame, text="Speech Rate:").grid(
            row=0, column=0, padx=5, sticky=tk.W
        )
        ttk.Scale(
            voice_frame,
            from_=100,
            to=200,
            variable=self.voice_rate,
            command=lambda v: self.tts_engine.setProperty("rate", int(float(v))),
        ).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(voice_frame, text="Volume:").grid(
            row=0, column=2, padx=5, sticky=tk.W
        )
        Scale(
            voice_frame,
            from_=0,
            to=1,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.voice_volume,
            command=lambda v: self.tts_engine.setProperty("volume", float(v)),
        ).grid(row=0, column=3, sticky="ew", padx=5)

        voice_frame.columnconfigure(1, weight=1)
        voice_frame.columnconfigure(3, weight=1)

        # Status
        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_label = ttk.Label(
            self.status_frame, text="Status: Ready", style="Status.TLabel"
        )
        self.status_label.pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(
            self.status_frame, mode="indeterminate", length=100
        )
        self.progress.pack(side=tk.RIGHT)

        # Buttons - Added Help button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        buttons = [
            ("🎤 Start Listening", self.start_listening),
            ("⏹ Stop Listening", self.stop_listening),
            ("💾 Save Transcript", self.save_transcript),
            ("📜 View History", self.show_history),
            ("🎨 Toggle Theme", self.toggle_theme),
            ("❓ Help", self.show_help),  # New Help button
        ]

        for i, (label, command) in enumerate(buttons):
            btn = ttk.Button(button_frame, text=label, command=command)
            btn.grid(row=0, column=i, padx=6, sticky=tk.EW)
            button_frame.columnconfigure(i, weight=1)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Transcription tab
        transcribe_frame = ttk.Frame(self.notebook)
        self.notebook.add(transcribe_frame, text="Live Transcription")

        self.result_text = SmoothTextWidget(
            transcribe_frame, wrap=tk.WORD, font=("Segoe UI", 12), padx=10, pady=10
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Help tab
        help_frame = ttk.Frame(self.notebook)
        self.notebook.add(help_frame, text="Help & Info")

        help_text = """Live Speech-to-Text Converter - User Guide

1. Select your input language (English/Urdu)
2. Click 'Start Listening' to begin transcription
3. The translated text will appear automatically
4. Use 'Save Transcript' to save your conversations

Tips for best results:
- Speak clearly in a quiet environment
- Pause briefly between sentences
- Adjust voice settings as needed

Troubleshooting:
- If translation fails, check your internet connection
- Ensure microphone permissions are granted
- Try speaking closer to the microphone
"""
        help_label = ttk.Label(help_frame, text=help_text, justify=tk.LEFT, padding=20)
        help_label.pack(fill=tk.BOTH, expand=True)

    def show_help(self):
        """Switch to the help tab when help button is clicked"""
        self.notebook.select(1)  # Select the help tab (index 1)

    def toggle_language(self):
        current = self.current_lang.get()
        new_lang = "ur-PK" if current == "en-US" else "en-US"
        self.current_lang.set(new_lang)
        lang_name = "Urdu" if new_lang == "ur-PK" else "English"
        self.lang_display.config(text=f"Current Input: {lang_name}")
        self.lang_btn.config(
            text=f"🔁 Switch to {'Urdu' if new_lang == 'en-US' else 'English'}"
        )

    def toggle_theme(self):
        current = sv_ttk.get_theme()
        new_theme = "dark" if current == "light" else "light"
        sv_ttk.set_theme(new_theme)
        self.status_label.config(text=f"Theme switched to {new_theme.capitalize()}")

    def start_listening(self):
        if not self.continuous_mode:
            self.continuous_mode = True
            self.status_label.config(text="Status: Listening...")
            self.progress.start()
            threading.Thread(target=self.background_listen, daemon=True).start()

    def stop_listening(self):
        if self.continuous_mode:
            self.continuous_mode = False
            self.status_label.config(text="Status: Ready")
            self.progress.stop()

    def background_listen(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self.continuous_mode:
                try:
                    audio = self.recognizer.listen(
                        source, timeout=3, phrase_time_limit=8
                    )
                    threading.Thread(
                        target=self.process_audio, args=(audio,), daemon=True
                    ).start()
                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    self.root.after(0, self.result_text.smooth_insert, f"Error: {e}")

    def process_audio(self, audio):
        try:
            current_lang = self.current_lang.get()
            target_lang = "ur" if current_lang == "en-US" else "en"

            retry_count = 3
            recognized = None
            for _ in range(retry_count):
                try:
                    recognized = self.recognizer.recognize_google(
                        audio, language=current_lang
                    )
                    break
                except sr.UnknownValueError:
                    continue

            if recognized:
                translated_text = self.translator.translate(
                    recognized,
                    source="en" if current_lang == "en-US" else "ur",
                    target=target_lang,
                )

                timestamp = time.strftime("%H:%M:%S")
                original_label = "English:" if current_lang == "en-US" else "Urdu:"
                translated_label = "Urdu:" if target_lang == "ur" else "English:"
                formatted_result = (
                    f"[{timestamp}] {original_label} {recognized}\n"
                    f"[{timestamp}] {translated_label} {translated_text}\n"
                )

                self.root.after(0, self.result_text.smooth_insert, formatted_result)
                self.transcription_history.append(formatted_result)
                self.root.after(0, self.speak_text, translated_text)

        except sr.RequestError as e:
            self.root.after(0, self.result_text.smooth_insert, f"API Error: {e}")
        except Exception as e:
            self.root.after(0, self.result_text.smooth_insert, f"Error: {e}")

    def speak_text(self, text):
        self.tts_engine.setProperty("rate", self.voice_rate.get())
        self.tts_engine.setProperty("volume", self.voice_volume.get())
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def save_transcript(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Text files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for line in self.transcription_history:
                        f.write(line + "\n")
                messagebox.showinfo("Save", "Transcript saved successfully!")
            except Exception as e:
                messagebox.showerror("Save Error", f"Error saving transcript: {e}")

    def show_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("📜 Transcription History")
        history_window.geometry("600x400")
        history_text = tk.Text(
            history_window, wrap=tk.WORD, font=("Segoe UI", 10), padx=10, pady=10
        )
        history_text.pack(fill=tk.BOTH, expand=True)
        for line in self.transcription_history:
            history_text.insert(tk.END, line + "\n")
        history_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    app = LiveSpeechToTextTranslatorApp()
    app.root.mainloop()
