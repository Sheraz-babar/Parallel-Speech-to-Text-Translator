import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import concurrent.futures
from moviepy import VideoFileClip
from pydub import AudioSegment
import speech_recognition as sr
import os
import datetime
import pygame
from deep_translator import GoogleTranslator
import threading

ctk.set_default_color_theme("blue")


class VideoToTextTranslatorApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Dark")
        self.title("Video Transcription App")
        self.geometry("1400x900")
        self.minsize(1200, 800)

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main container
        self.main_container = ctk.CTkFrame(self, corner_radius=12)
        self.main_container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # Header section
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Video Transcription App",
            font=ctk.CTkFont("Arial", size=28, weight="bold"),
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="☀️/🌙",
            command=self.toggle_theme,
            width=50,
            fg_color="transparent",
            hover_color=("gray70", "gray30"),
        )
        self.toggle_btn.grid(row=0, column=1, sticky="e")

        # Create main content area with tabs
        self.tabview = ctk.CTkTabview(self.main_container)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Add tabs
        self.tabview.add("Transcription")
        self.tabview.add("Settings")
        self.tabview.tab("Transcription").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Settings").grid_columnconfigure(0, weight=1)

        # Transcription tab content
        self.setup_transcription_tab()

        # Settings tab content
        self.setup_settings_tab()

        # Status bar
        self.status_bar = ctk.CTkLabel(
            self.main_container,
            text="Ready",
            anchor="w",
            font=ctk.CTkFont(size=12),
            fg_color=("gray85", "gray20"),
            corner_radius=5,
        )
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        # Initialize variables
        self.chunk_total = 0
        self.chunk_done = 0
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.translations = {}
        self.translated_text = ""

        pygame.mixer.init()

    def setup_transcription_tab(self):
        tab = self.tabview.tab("Transcription")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)  # Text area gets expansion space

        # File input section - now in one row
        self.file_frame = ctk.CTkFrame(tab, corner_radius=8)
        self.file_frame.grid(row=0, column=0, padx=10, pady=(0, 15), sticky="ew")
        self.file_frame.grid_columnconfigure(0, weight=1)
        self.file_frame.grid_columnconfigure(2, weight=1)

        # Drag area (left side)
        self.drop_area = ctk.CTkLabel(
            self.file_frame,
            text="📁 Drag & Drop Video File Here",
            height=100,
            corner_radius=8,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=("gray90", "gray20"),
            text_color=("gray40", "gray60"),
        )
        self.drop_area.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=10)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind("<<Drop>>", self.drop_video)

        # "or" label centered vertically
        self.or_label = ctk.CTkLabel(
            self.file_frame,
            text="or",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray50"),
        )
        self.or_label.grid(row=0, column=1, sticky="ns", padx=5)

        # Browse button (right side)
        self.select_button = ctk.CTkButton(
            self.file_frame,
            text="Browse Video File",
            command=self.handle_video_selection,
            height=100,  # Match drop area height
            font=ctk.CTkFont(size=14, weight="bold"),
            border_width=1,
            border_color=("gray70", "gray30"),
        )
        self.select_button.grid(row=0, column=2, sticky="nsew", padx=(5, 0), pady=10)

        # Progress section
        self.progress_frame = ctk.CTkFrame(tab, corner_radius=8)
        self.progress_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 15))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, mode="determinate", height=20, corner_radius=10
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=10, padx=10)

        self.progress_text = ctk.CTkLabel(
            self.progress_frame, text="0%", font=ctk.CTkFont(size=12), anchor="e"
        )
        self.progress_text.pack(fill="x", pady=(0, 10), padx=10)

        # Text results section with fixed height
        self.text_tabview = ctk.CTkTabview(tab, height=400)  # Fixed height
        self.text_tabview.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 15))

        self.text_tabview.add("Original")
        self.text_tabview.add("Translation")
        self.text_tabview.add("Logs")

        # Configure tab weights
        for tab_name in ["Original", "Translation", "Logs"]:
            self.text_tabview.tab(tab_name).grid_columnconfigure(0, weight=1)
            self.text_tabview.tab(tab_name).grid_rowconfigure(0, weight=1)

        # Original text tab
        self.result_text = ctk.CTkTextbox(
            self.text_tabview.tab("Original"),
            font=ctk.CTkFont("Consolas", size=12),
            wrap="word",
        )
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Translation tab
        self.translation_tab = self.text_tabview.tab("Translation")
        self.translation_tab.grid_columnconfigure(0, weight=1)
        self.translation_tab.grid_rowconfigure(0, weight=1)

        # Translation text box
        self.translation_text = ctk.CTkTextbox(
            self.translation_tab, font=ctk.CTkFont("Consolas", size=12), wrap="word"
        )
        self.translation_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Logs tab
        self.log_text = ctk.CTkTextbox(
            self.text_tabview.tab("Logs"),
            font=ctk.CTkFont("Consolas", size=12),
            wrap="word",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Action buttons - now with translation controls in the middle
        self.button_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Clear button on left
        self.clear_button = ctk.CTkButton(
            self.button_frame,
            text="🗑️ Clear All",
            command=self.clear_all,
            height=40,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=14),
        )
        self.clear_button.pack(side="left")

        # Translation controls in center
        self.translation_controls = ctk.CTkFrame(
            self.button_frame, fg_color="transparent"
        )
        self.translation_controls.pack(side="left", padx=10, expand=True)

        self.language_label = ctk.CTkLabel(
            self.translation_controls, text="Translate to:", font=ctk.CTkFont(size=12)
        )
        self.language_label.pack(side="left", padx=(0, 5))

        self.language_option = ctk.CTkOptionMenu(
            self.translation_controls,
            values=["Spanish", "French", "German", "Urdu", "Arabic", "Hindi"],
            dynamic_resizing=False,
            width=120,
        )
        self.language_option.set("Select language")
        self.language_option.pack(side="left", padx=(0, 10))

        self.translate_button = ctk.CTkButton(
            self.translation_controls,
            text="Translate",
            command=self.translate_text,
            width=100,
            fg_color="#2e8b57",
            hover_color="#3cb371",
        )
        self.translate_button.pack(side="left")

        # Export button on right
        self.export_button = ctk.CTkButton(
            self.button_frame,
            text="📤 Export Transcripts",
            command=self.export_transcripts,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.export_button.pack(side="right")

    def setup_settings_tab(self):
        tab = self.tabview.tab("Settings")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Settings container
        self.settings_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.settings_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        settings_label = ctk.CTkLabel(
            self.settings_container,
            text="Application Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        settings_label.grid(row=0, column=0, pady=(0, 20), sticky="w")

        # Settings form
        self.settings_form = ctk.CTkFrame(
            self.settings_container, fg_color="transparent"
        )
        self.settings_form.grid(row=1, column=0, sticky="ew")

        # Chunk size setting
        chunk_label = ctk.CTkLabel(
            self.settings_form, text="Audio Chunk Size (ms):", font=ctk.CTkFont(size=14)
        )
        chunk_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.chunk_size = ctk.CTkEntry(self.settings_form, placeholder_text="5000")
        self.chunk_size.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Worker threads setting
        worker_label = ctk.CTkLabel(
            self.settings_form, text="Max Worker Threads:", font=ctk.CTkFont(size=14)
        )
        worker_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.worker_threads = ctk.CTkEntry(self.settings_form, placeholder_text="8")
        self.worker_threads.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Save button
        save_btn = ctk.CTkButton(
            self.settings_container,
            text="Save Settings",
            command=self.save_settings,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        save_btn.grid(row=2, column=0, pady=20, sticky="e")

    def toggle_theme(self):
        mode = ctk.get_appearance_mode()
        new_mode = "Light" if mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.toggle_btn.configure(text="☀️" if new_mode == "Light" else "🌙")
        self.update_status(f"Switched to {new_mode} mode")

    def update_status(self, message):
        """Update both status systems for compatibility"""
        self.status_bar.configure(text=message)

    def update_progress(self):
        if self.chunk_total:
            percent = self.chunk_done / self.chunk_total
            self.progress_bar.set(percent)
            progress_text = f"{int(percent*100)}% - {self.chunk_done}/{self.chunk_total} chunks processed"
            self.progress_text.configure(text=progress_text)
            self.update_status(progress_text)

    def clear_all(self):
        self.result_text.delete("1.0", tk.END)
        self.translation_text.delete("1.0", tk.END)
        self.log_text.delete("1.0", tk.END)
        self.progress_bar.set(0)
        self.progress_text.configure(text="0%")
        self.update_status("Ready")

    def save_settings(self):
        try:
            new_chunk_size = int(self.chunk_size.get())
            new_workers = int(self.worker_threads.get())
            self.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=new_workers
            )
            self.update_status(
                f"Settings saved: Chunk size={new_chunk_size}ms, Workers={new_workers}"
            )
        except ValueError:
            self.update_status("Invalid settings values")

    def drop_video(self, event):
        video_path = event.data.strip("{}")
        self.start_transcription(video_path)

    def handle_video_selection(self):
        video_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.flv")],
        )
        if video_path:
            self.start_transcription(video_path)

    def start_transcription(self, video_path):
        self.result_text.delete("1.0", tk.END)
        self.translation_text.delete("1.0", tk.END)
        self.translations.clear()
        self.translated_text = ""
        self.log(f"Selected video file: {video_path}")
        threading.Thread(
            target=self.process_video, args=(video_path,), daemon=True
        ).start()

    def log(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        print(msg)

    def process_video(self, video_path):
        try:
            self.progress_bar.set(0)
            self.chunk_done = 0
            self.update_status("Extracting audio...")

            base_output_dir = "Video Chunks Outputs"
            os.makedirs(base_output_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.output_dir = os.path.join(base_output_dir, f"Run_{timestamp}")
            os.makedirs(self.output_dir)

            video = VideoFileClip(video_path)
            audio_path = os.path.join(self.output_dir, "temp_audio.wav")
            video.audio.write_audiofile(audio_path, codec="pcm_s16le")

            chunk_size = int(self.chunk_size.get()) if self.chunk_size.get() else 5000
            chunks = self.chunk_audio(audio_path, self.output_dir, chunk_size)
            self.chunk_total = len(chunks)

            self.log(f"{self.chunk_total} chunks to process.")

            for idx, chunk in enumerate(chunks):
                self.executor.submit(self.recognize_audio, chunk, idx)

        except Exception as e:
            self.result_text.insert(tk.END, f"Error: {e}\n")
            self.log(f"Error: {e}")
            self.update_status("Failed during transcription.")

    def chunk_audio(self, audio_path, output_dir, chunk_duration_ms=5000):
        audio = AudioSegment.from_wav(audio_path)
        chunks = []
        for start_ms in range(0, len(audio), chunk_duration_ms):
            end_ms = min(start_ms + chunk_duration_ms, len(audio))
            chunk = audio[start_ms:end_ms]
            chunk_filename = os.path.join(output_dir, f"chunk_{start_ms // 1000}.wav")
            chunk.export(chunk_filename, format="wav")
            chunks.append(chunk_filename)
        return chunks

    def recognize_audio(self, path, index):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(path) as source:
                audio = recognizer.record(source)
                text = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            text = "[Unintelligible audio]"
        except sr.RequestError as e:
            text = f"[API error: {e}]"
        except Exception as e:
            text = f"[Error: {e}]"

        self.chunk_done += 1
        self.translations[index] = text
        self.after(0, self.update_progress)
        self.after(0, self.append_result, index, text)

    def append_result(self, index, text):
        self.result_text.insert(tk.END, f"Chunk {index} Result:\n{text}\n\n")
        self.result_text.see(tk.END)
        self.log(f"Chunk {index} complete.")
        if self.chunk_done == self.chunk_total:
            self.update_status("Transcription complete!")

    def translate_text(self):
        target_lang = self.language_option.get()
        if target_lang == "Select language":
            return

        try:
            full_text = self.result_text.get("1.0", tk.END).strip()
            if not full_text:
                return

            self.translate_button.configure(state="disabled", text="Translating...")
            self.update_status(f"Translating to {target_lang}...")

            threading.Thread(
                target=self._perform_translation,
                args=(full_text, target_lang),
                daemon=True,
            ).start()

        except Exception as e:
            self.log(f"Translation initialization error: {e}")
            self.update_status("Translation failed to start")
            self.translate_button.configure(state="normal", text="Translate")

    def _perform_translation(self, text, target_lang):
        try:
            lang_code = (
                GoogleTranslator()
                .get_supported_languages(as_dict=True)
                .get(target_lang.lower(), target_lang.lower())
            )
            translated = GoogleTranslator(source="auto", target=lang_code).translate(
                text
            )

            self.after(0, self._update_translation_ui, translated, target_lang)

        except Exception as e:
            self.after(0, self._handle_translation_error, e)

    def _update_translation_ui(self, translated_text, target_lang):
        self.translated_text = translated_text
        self.translation_text.delete("1.0", tk.END)
        self.translation_text.insert(tk.END, translated_text)
        self.translate_button.configure(state="normal", text="Translate")
        self.update_status(f"Translated to {target_lang}")

    def _handle_translation_error(self, error):
        self.translation_text.insert(tk.END, f"Error during translation: {error}")
        self.log(f"Translation error: {error}")
        self.update_status("Translation failed")
        self.translate_button.configure(state="normal", text="Translate")

    def export_transcripts(self):
        try:
            if not hasattr(self, "output_dir"):
                return

            english_path = os.path.join(self.output_dir, "transcription_english.txt")
            with open(english_path, "w", encoding="utf-8") as f:
                f.write(self.result_text.get("1.0", tk.END))

            if self.translated_text:
                target_lang = self.language_option.get()
                if target_lang != "Select language":
                    translated_path = os.path.join(
                        self.output_dir, f"transcription_{target_lang.lower()}.txt"
                    )
                    with open(translated_path, "w", encoding="utf-8") as f:
                        f.write(self.translated_text)

            self.log("Transcriptions exported")
            self.update_status(f"Transcripts saved to {self.output_dir}")
        except Exception as e:
            self.log(f"Export error: {e}")
            self.update_status("Export failed")


if __name__ == "__main__":
    app = VideoToTextTranslatorApp()
    app.mainloop()
