# --- Стандартные библиотеки ---
import os
import sys
import json
import time
import tempfile
import threading
from dataclasses import dataclass, asdict, field
from typing import Optional, List

# --- GUI и взаимодействие ---
import tkinter as tk
from tkinter import ttk, messagebox
import TKinterModernThemes as TKMT

# --- Аудио и TTS ---
import pygame
import pyaudio
import wave
import numpy as np
from gtts import gTTS
import pyttsx3
from pydub import AudioSegment

# --- Сторонние утилиты ---
import keyboard
import ctypes
from ctypes import wintypes

# --- Внешние модули проекта ---
try:
    from voice_api import VoiceRSSAPI
except ImportError:
    print("Модуль voice_api.py не найден. Функции VoiceRSS будут недоступны.")
    VoiceRSSAPI = None

import logging
logging.basicConfig(
    filename="tts_overlay_debug.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)
logging.debug("=== TTS Overlay стартует ===")

# Константы для Windows API
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004

# Коды виртуальных клавиш
VK_CODE = {
    'backspace': 0x08, 'tab': 0x09, 'clear': 0x0C, 'enter': 0x0D, 'shift': 0x10,
    'ctrl': 0x11, 'alt': 0x12, 'pause': 0x13, 'caps_lock': 0x14, 'esc': 0x1B,
    'spacebar': 0x20, 'page_up': 0x21, 'page_down': 0x22, 'end': 0x23, 'home': 0x24,
    'left_arrow': 0x25, 'up_arrow': 0x26, 'right_arrow': 0x27, 'down_arrow': 0x28,
    'select': 0x29, 'print': 0x2A, 'execute': 0x2B, 'print_screen': 0x2C,
    'ins': 0x2D, 'del': 0x2E, 'help': 0x2F,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
    'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
    'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
    's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A,
    'numpad_0': 0x60, 'numpad_1': 0x61, 'numpad_2': 0x62, 'numpad_3': 0x63,
    'numpad_4': 0x64, 'numpad_5': 0x65, 'numpad_6': 0x66, 'numpad_7': 0x67,
    'numpad_8': 0x68, 'numpad_9': 0x69,
    'multiply_key': 0x6A, 'add_key': 0x6B, 'separator_key': 0x6C,
    'subtract_key': 0x6D, 'decimal_key': 0x6E, 'divide_key': 0x6F,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74,
    'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79,
    'f11': 0x7A, 'f12': 0x7B, 'f13': 0x7C, 'f14': 0x7D, 'f15': 0x7E,
    'f16': 0x7F, 'f17': 0x80, 'f18': 0x81, 'f19': 0x82, 'f20': 0x83,
    'f21': 0x84, 'f22': 0x85, 'f23': 0x86, 'f24': 0x87,
    'num_lock': 0x90, 'scroll_lock': 0x91, 'space': 0x20,
    # Специальные клавиши
    'left_shift': 0xA0, 'right_shift': 0xA1, 'left_control': 0xA2,
    'right_control': 0xA3, 'left_menu': 0xA4, 'right_menu': 0xA5
}

@dataclass
class TTSSettings:
    output_device_index: int = 0
    mic_device_index: int = -1
    output_volume: float = 0.8
    mic_volume: float = 0.8
    voice_id: Optional[str] = None
    tts_engine: str = "google"
    voicerss_language: str = "ru-ru"
    voicerss_voice: Optional[str] = None
    voicerss_api_key: Optional[str] = ""
    voice_chat_key: Optional[str] = None
    history_hotkey_modifier: str = "ctrl"
    remove_queue: bool = False
    toggle_visibility_key: str = "alt+t"  # Клавиша для открытия/закрытия меню (по умолчанию alt+t)
    focus_window_key: Optional[str] = None  # Дополнительная клавиша для открытия окна (по умолчанию не задана)
    settings_path: str = field(default_factory=lambda: os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), "settings.json"), repr=False)

    def load_settings(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key in asdict(self):
                    if key in data:
                        setattr(self, key, data[key] if data[key] is not None else None)
            except Exception as e:
                print(f"Ошибка при загрузке настроек: {e}")

    def save_settings(self):
        try:
            data = asdict(self)
            data.pop('settings_path', None)
            # Приводим все None к пустой строке для корректного сохранения в json
            for k, v in data.items():
                if v is None:
                    data[k] = ""
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении настроек: {e}")

class TTSOverlay(TKMT.ThemedTKinterFrame):
    def __init__(self):
        logging.debug("TTSOverlay.__init__() стартует")
        print("Инициализация приложения...")
        # Инициализация главного окна с темой
        super().__init__("TTS Overlay", "azure", "dark", useconfigfile=False, usecommandlineargs=False)
        
        # Убираем стандартную рамку окна
        self.root.overrideredirect(True)
        
        # Устанавливаем окно поверх всех других окон
        self.root.attributes('-topmost', True)
        
        # Инициализация pygame для проигрывания звука
        pygame.mixer.init()
        
        # Инициализация PyAudio для работы с аудиоустройствами
        self.p = pyaudio.PyAudio()
        logging.debug("PyAudio инициализирован")
        print("PyAudio инициализирован")
        
        # Инициализация локального движка TTS
        self.engine = pyttsx3.init()
        
        # Загружаем настройки
        self.settings = TTSSettings()
        self.settings.load_settings()
        
        # Создание кастомной полосы заголовка
        self.create_title_bar()
        
        # Создание главного интерфейса
        self.create_widgets()
        
        # Получение списка аудиоустройств
        self.get_audio_devices()
        
        # Регистрация горячих клавиш
        self.register_hotkeys()
        
        # Создание папки для кэша, если её нет
        self.cache_folder = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), "cache")
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)
        
        # Очередь для хранения временных файлов
        self.temp_files = []
        
        # Запуск потока для очистки временных файлов
        self.cleanup_thread = threading.Thread(target=self.cleanup_temp_files, daemon=True)
        self.cleanup_thread.start()
        print("Рабочий поток запущен")
        
        # Запуск потока для очистки старых файлов кэша
        self.cache_cleanup_thread = threading.Thread(target=self.cleanup_cache, daemon=True)
        self.cache_cleanup_thread.start()
        print("Рабочий поток запущен")
        
        # Буфер для хранения истории фраз
        self.phrase_history = [""] * 10
        
        # Флаг для отслеживания состояния воспроизведения
        self.is_playing = False
        
        # Последний воспроизведенный текст (для предотвращения дублирования)
        self.last_played_text = ""
        
        # Запускаем проверку, что окно всегда поверх других окон
        self.check_topmost()
        
        self.mic_thread = None
        self._stop_mic = False
        self.active_tts_threads = []
        self._tts_stop_flag = False
        self._tts_engines = []
        self._tts_events = []
        self.tts_lock = threading.Lock()
    
    def create_title_bar(self):
        """Создание кастомной полосы заголовка"""
        # Создаем фрейм для полосы заголовка
        self.title_bar = tk.Frame(self.root, bg="#1f1f1f", height=30)
        self.title_bar.pack(fill='x', side='top')
        self.title_bar.pack_propagate(False)
        
        # Добавляем логотип
        self.logo_label = tk.Label(self.title_bar, text="🔊 TTS Overlay", bg="#1f1f1f", fg="white", font=("Arial", 10, "bold"))
        self.logo_label.pack(side='left', padx=10)
        
        # Добавляем кнопки управления окном
        # Кнопка закрытия
        self.close_button = tk.Button(self.title_bar, text="✕", bg="#1f1f1f", fg="white", 
                                     borderwidth=0, highlightthickness=0, width=3, height=1, 
                                     activebackground="#e81123", activeforeground="white",
                                     command=self.on_close)
        self.close_button.pack(side='right')
        
        # Кнопка сворачивания
        self.minimize_button = tk.Button(self.title_bar, text="—", bg="#1f1f1f", fg="white", 
                                        borderwidth=0, highlightthickness=0, width=3, height=1,
                                        activebackground="#333333", activeforeground="white",
                                        command=self.minimize_window)
        self.minimize_button.pack(side='right')
        
        # Кнопка настроек
        self.settings_button = tk.Button(self.title_bar, text="⚙", bg="#1f1f1f", fg="white", 
                                       borderwidth=0, highlightthickness=0, width=3, height=1,
                                       activebackground="#333333", activeforeground="white",
                                       command=self.open_settings)
        self.settings_button.pack(side='right')
        
        # Привязка событий для перетаскивания окна
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<ButtonRelease-1>", self.stop_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        
        # Привязка событий для перетаскивания окна через логотип
        self.logo_label.bind("<ButtonPress-1>", self.start_move)
        self.logo_label.bind("<ButtonRelease-1>", self.stop_move)
        self.logo_label.bind("<B1-Motion>", self.do_move)
    
    def start_move(self, event):
        """Начало перетаскивания окна"""
        self.x = event.x
        self.y = event.y
    
    def stop_move(self, event):
        """Окончание перетаскивания окна"""
        self.x = None
        self.y = None
    
    def do_move(self, event):
        """Перемещение окна"""
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")
    
    def on_close(self):
        """Обработка закрытия приложения"""
        # Останавливаем воспроизведение, если оно идет
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        # Удаляем временные файлы
        for file in self.temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except:
                pass
        
        # Отменяем регистрацию горячих клавиш
        keyboard.unhook_all()
        
        # Закрываем PyAudio
        self.p.terminate()
        
        # Закрываем приложение
        self.root.destroy()
        sys.exit(0)
    
    def minimize_window(self):
        """Сворачивает окно как Alt+T"""
        self.toggle_visibility()
    
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Создаем главный фрейм под полосой заголовка
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Текстовое поле для ввода текста
        self.text_entry = tk.Text(main_frame, height=5, width=50, wrap="word", bg="#2a2a2a", fg="white", 
                                 insertbackground="white", relief="flat", font=("Arial", 10))
        self.text_entry.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Добавляем скроллбар для текстового поля
        scrollbar = ttk.Scrollbar(self.text_entry, command=self.text_entry.yview)
        scrollbar.pack(side='right', fill='y')
        self.text_entry.config(yscrollcommand=scrollbar.set)
        
        # Фрейм для кнопок
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=5)
        
        # Кнопка воспроизведения
        self.speak_button = ttk.Button(button_frame, text="🔊 Воспроизвести", command=self.speak_text)
        self.speak_button.pack(side='left', padx=5)
        
        # Кнопка настроек
        self.settings_button = ttk.Button(button_frame, text="⚙ Настройки", command=self.open_settings)
        self.settings_button.pack(side='left', padx=5)
        
        # Строка статуса
        self.status_var = tk.StringVar(value="Готово")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor='w')
        self.status_label.pack(fill='x', pady=5)
        
        # Привязка горячих клавиш для текстового поля
        self.text_entry.bind("<Control-Return>", lambda e: self.speak_text())
        self.text_entry.bind("<Return>", lambda e: self.speak_text())  # Добавляем воспроизведение по Enter
    
    def get_audio_devices(self):
        """Получение списка аудиоустройств"""
        devices = []
        
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            # Преобразуем значение в int для корректного сравнения
            max_output_channels = int(device_info['maxOutputChannels'])
            if max_output_channels > 0:
                devices.append((i, device_info['name']))
        
        self.output_devices = devices
        logging.debug(f"Найдено устройств вывода: {len(self.output_devices)}")
        
        # Получаем список устройств ввода для микрофона
        input_devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            # Преобразуем значение в int для корректного сравнения
            max_input_channels = int(device_info['maxInputChannels'])
            if max_input_channels > 0:
                input_devices.append((i, device_info['name']))
        
        self.mic_devices = input_devices
        logging.debug(f"Найдено устройств ввода: {len(self.mic_devices)}")
    
    def register_hotkeys(self):
        try:
            keyboard.unhook_all()
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Ошибка при отмене хоткеев: {e}")
        toggle_key = self.settings.toggle_visibility_key or "alt+t"
        try:
            keyboard.add_hotkey(toggle_key, lambda: (self.root.after(0, self._toggle_visibility_mainthread), None)[1], suppress=True)
            logging.debug(f"Зарегистрирован хоткей для переключения видимости: {toggle_key}")
        except Exception as e:
            logging.warning(f"Не удалось зарегистрировать хоткей для переключения видимости {toggle_key}: {e}")
            try:
                keyboard.add_hotkey("alt+t", lambda: (self.root.after(0, self._toggle_visibility_mainthread), None)[1], suppress=True)
                logging.debug("Зарегистрирован стандартный хоткей для переключения видимости: alt+t")
            except Exception as e2:
                logging.error(f"Не удалось зарегистрировать стандартный хоткей: {e2}")
        focus_key = self.settings.focus_window_key
        if focus_key:
            try:
                keyboard.add_hotkey(focus_key, lambda: (self.root.after(0, self.show_and_focus_window), None)[1], suppress=True)
                logging.debug(f"Зарегистрирован хоткей для открытия окна: {focus_key}")
            except Exception as e:
                logging.warning(f"Не удалось зарегистрировать хоткей для открытия окна {focus_key}: {e}")
        modifier = self.settings.history_hotkey_modifier or "ctrl"
        for i in range(10):
            hotkey = f"{modifier}+{i}"
            try:
                def create_handler(num):
                    return lambda: (self.root.after(0, self._play_saved_phrase_mainthread, num), None)[1]
                keyboard.add_hotkey(hotkey, create_handler(i), suppress=True)
                logging.debug(f"Зарегистрирован хоткей для истории: {hotkey}")
            except Exception as e:
                logging.warning(f"Не удалось зарегистрировать хоткей для истории {hotkey}: {e}")
        if self.settings.voice_chat_key and self.settings.voice_chat_key != toggle_key:
            try:
                keyboard.add_hotkey(self.settings.voice_chat_key, lambda: (self.root.after(0, self.show_and_focus_window), None)[1], suppress=False)
                logging.debug(f"Зарегистрирован хоткей для микрофона: {self.settings.voice_chat_key}")
            except Exception as e:
                logging.warning(f"Не удалось зарегистрировать хоткей для voice_chat_key: {e}")
    
    def toggle_visibility(self):
        self.root.after(0, self._toggle_visibility_mainthread)

    def _toggle_visibility_mainthread(self):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.root.update()
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            logging.debug("Окно показано")
        else:
            self.root.withdraw()
            self.root.update()
            logging.debug("Окно скрыто")
    
    def show_and_focus_window(self):
        def do_focus():
            self.root.deiconify()
            self.root.update()
            self.root.attributes('-topmost', True)
            self.root.lift()
            self.root.focus_force()
            self.text_entry.focus_set()
            self.text_entry.mark_set("insert", "end")
            self.root.after(100, self._ensure_focus)
            self.set_status("Введите текст и нажмите Enter")
        if threading.current_thread() is threading.main_thread():
            do_focus()
        else:
            self.root.after(0, do_focus)
    
    def _ensure_focus(self):
        """Дополнительная проверка и установка фокуса"""
        if not self.root.focus_get():
            self.root.focus_force()
            self.text_entry.focus_set()
            self.text_entry.focus_force()
    
    def speak_text(self):
        def do_speak():
            text = self.text_entry.get("1.0", tk.END).strip()
            if not text:
                self.set_status("⚠️ Введите текст для озвучивания")
                return
            if text != self.last_played_text:
                self.add_to_history(text)
                self.last_played_text = text
            self.text_entry.delete("1.0", tk.END)
            self.root.withdraw()
            self.set_status("Озвучивание...")
            self.check_and_fix_key_stuck()
            if getattr(self.settings, 'remove_queue', False):
                self.stop_playback()
            self._tts_stop_flag = False
            tts_event = threading.Event()
            def tts_job():
                try:
                    self.text_to_speech(text, tts_event)
                finally:
                    with self.tts_lock:
                        if threading.current_thread() in self.active_tts_threads:
                            self.active_tts_threads.remove(threading.current_thread())
            tts_thread = threading.Thread(target=tts_job, daemon=True)
            tts_thread.start()
            with self.tts_lock:
                self.active_tts_threads.append(tts_thread)
                self._tts_events.append(tts_event)
        if threading.current_thread() is threading.main_thread():
            do_speak()
        else:
            self.root.after(0, do_speak)
        return "break"
    
    def add_to_history(self, text):
        # Проверяем, нет ли уже такого текста в начале истории
        if not self.phrase_history or text != self.phrase_history[0]:
            # Сдвигаем все фразы на одну позицию вперед (новая фраза будет под индексом 0)
            self.phrase_history = [text] + self.phrase_history[:-1]
    
    def play_saved_phrase(self, index):
        self.root.after(0, self._play_saved_phrase_mainthread, index)

    def _play_saved_phrase_mainthread(self, index):
        real_index = index - 1 if index > 0 else 9
        if 0 <= real_index < len(self.phrase_history) and self.phrase_history[real_index]:
            phrase = self.phrase_history[real_index]
            if getattr(self.settings, 'remove_queue', False):
                self.stop_playback()
            self.check_and_fix_key_stuck()
            self.set_status(f"🔊 Воспроизведение фразы #{index}")
            self._tts_stop_flag = False
            tts_event = threading.Event()
            def tts_job():
                try:
                    self.text_to_speech(phrase, tts_event)
                finally:
                    with self.tts_lock:
                        if threading.current_thread() in self.active_tts_threads:
                            self.active_tts_threads.remove(threading.current_thread())
            tts_thread = threading.Thread(target=tts_job, daemon=True)
            tts_thread.start()
            with self.tts_lock:
                self.active_tts_threads.append(tts_thread)
                self._tts_events.append(tts_event)
    
    def cleanup_temp_files(self):
        """Фоновый поток для очистки временных файлов"""
        while True:
            time.sleep(5)  # Проверяем каждые 5 секунд
            if self.temp_files:
                for file_path in list(self.temp_files):
                    try:
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                            self.temp_files.remove(file_path)
                    except Exception as e:
                        # Если файл еще занят, пробуем позже
                        print(f"Не удалось удалить временный файл {file_path}: {e}")
                        continue
    
    def generate_audio_google(self, text):
        """Генерация аудио через Google TTS"""
        # Проверяем, есть ли в кэше
        text_hash = hash(text)
        cache_path = os.path.join(self.cache_folder, f"{text_hash}.mp3")
        
        if os.path.exists(cache_path):
            print(f"Используется кэшированный файл: {cache_path}")
            return cache_path
        
        # Если нет в кэше, генерируем новый
        try:
            tts = gTTS(text=text, lang='ru', slow=False)
            tts.save(cache_path)
            print(f"Аудио сохранено в кэш: {cache_path}")
            return cache_path
        except Exception as e:
            print(f"Ошибка при генерации аудио через Google: {e}")
            return None
    
    def generate_audio_local(self, text):
        """Генерация аудио через локальный движок pyttsx3"""
        # Получаем список доступных голосов
        voices = self.engine.getProperty('voices')
        
        # Если задан конкретный ID голоса, используем его
        if self.settings.voice_id:
            for voice in voices:
                if voice.id == self.settings.voice_id:
                    self.engine.setProperty('voice', voice.id)
                    break
        
        # Генерируем во временный файл
        temp_file = tempfile.mktemp(suffix='.wav')
        
        try:
            self.engine.save_to_file(text, temp_file)
            self.engine.runAndWait()
            print(f"Локальный аудио файл создан: {temp_file}")
            
            # Добавляем во временные файлы для очистки
            self.temp_files.append(temp_file)
            
            return temp_file
        except Exception as e:
            print(f"Ошибка при генерации аудио локально: {e}")
            return None
    
    def generate_audio_voicerss(self, text):
        """Генерация аудио через VoiceRSS API"""
        if VoiceRSSAPI is None:
            print("Модуль VoiceRSS API не загружен")
            return None
        
        try:
            # Создаем экземпляр API с ключом из настроек или демо-ключом
            api_key = self.settings.voicerss_api_key
            if not api_key:
                api = VoiceRSSAPI()
                api_key = api.get_demo_key()
                print("Используется демо-ключ VoiceRSS API")
            else:
                api = VoiceRSSAPI(api_key)
            
            # Получаем язык и голос из настроек
            language = self.settings.voicerss_language or "ru-ru"
            voice = self.settings.voicerss_voice
            
            # Генерируем аудио
            audio_file = api.text_to_speech(text, language, voice)
            if audio_file and os.path.exists(audio_file):
                print(f"VoiceRSS аудио файл создан: {audio_file}")
                return audio_file
            else:
                print("Ошибка при генерации аудио через VoiceRSS API или файл не создан")
                return None
        except Exception as e:
            print(f"Ошибка при генерации аудио через VoiceRSS: {e}")
            return None
    
    def text_to_speech(self, text, tts_event):
        tts_engine = self.settings.tts_engine
        if self._tts_stop_flag or tts_event.is_set():
            return
        try:
            if tts_engine == "google":
                audio_file = self.generate_audio_google(text)
                if self._tts_stop_flag or tts_event.is_set():
                    return
                if audio_file:
                    self.play_audio_output(audio_file)
                    if self.settings.mic_device_index != -1:
                        self.play_audio_mic(audio_file)
            elif tts_engine == "local":
                import pyttsx3
                engine = pyttsx3.init()
                self._tts_engines.append(engine)
                voices = engine.getProperty('voices')
                if self.settings.voice_id:
                    for voice in voices:
                        if voice.id == self.settings.voice_id:
                            engine.setProperty('voice', voice.id)
                            break
                temp_file = tempfile.mktemp(suffix='.wav')
                try:
                    engine.save_to_file(text, temp_file)
                    engine.runAndWait()
                    if self._tts_stop_flag or tts_event.is_set():
                        return
                    self.play_audio_output(temp_file)
                    if self.settings.mic_device_index != -1:
                        self.play_audio_mic(temp_file)
                finally:
                    engine.stop()
                    if engine in self._tts_engines:
                        self._tts_engines.remove(engine)
            elif tts_engine == "voicerss":
                audio_file = self.generate_audio_voicerss(text)
                if self._tts_stop_flag or tts_event.is_set():
                    return
                if audio_file:
                    self.play_audio_output(audio_file)
                    if self.settings.mic_device_index != -1:
                        self.play_audio_mic(audio_file)
        finally:
            try:
                self.active_tts_threads.remove(threading.current_thread())
            except Exception:
                pass
            try:
                self._tts_events.remove(tts_event)
            except Exception:
                pass
    
    def play_audio_output(self, audio_file):
        """Воспроизведение аудиофайла через pygame (Sound.play, чтобы stop_playback всегда останавливал всё)"""
        import pygame
        pygame.mixer.init()
        sound = pygame.mixer.Sound(audio_file)
        # Восстанавливаем громкость для всех каналов
        for i in range(pygame.mixer.get_num_channels()):
            ch = pygame.mixer.Channel(i)
            ch.set_volume(min(self.settings.output_volume, 1.0))
        # Усиление громкости выше 100% через numpy
        if self.settings.output_volume > 1.0:
            try:
                arr = pygame.sndarray.array(sound)
                arr = np.clip(arr * self.settings.output_volume, -32768, 32767).astype(arr.dtype)
                sound = pygame.sndarray.make_sound(arr)
            except Exception as e:
                logging.warning(f"Не удалось усилить громкость выше 100%: {e}")
        sound.set_volume(min(self.settings.output_volume, 1.0))
        sound.play()
    
    def _press_mic_key(self):
        """Оптимизированное нажатие клавиши микрофона"""
        if not self.settings.voice_chat_key:
            return False
        
        key = self.settings.voice_chat_key
        try:
            # Основной метод через SendInput API
            success = self._send_input_key(key, press=True)
            if success:
                logging.debug(f"Клавиша микрофона '{key}' успешно нажата")
                return True
                
            # Резервный метод через keyboard
            keyboard.press(key)
            return keyboard.is_pressed(key)
        except Exception as e:
            logging.error(f"Ошибка при нажатии клавиши микрофона: {e}")
            return False
        
    def _release_mic_key(self):
        """Оптимизированное освобождение клавиши микрофона"""
        if not self.settings.voice_chat_key:
            return False
        
        key = self.settings.voice_chat_key
        try:
            # Основной метод через SendInput API
            success = self._send_input_key(key, press=False)
            
            # Проверяем, освободилась ли клавиша
            if success and not keyboard.is_pressed(key):
                logging.debug(f"Клавиша микрофона '{key}' успешно освобождена")
                return True
            
            # Резервный метод через keyboard
            keyboard.release(key)
            return not keyboard.is_pressed(key)
        except Exception as e:
            logging.error(f"Ошибка при освобождении клавиши микрофона: {e}")
            return False
        
    def play_audio_mic(self, audio_file):
        # Для передачи аудио в микрофон, нужно использовать Virtual Audio Cable или аналог
        mic_index = self.settings.mic_device_index
        if isinstance(mic_index, int) and mic_index >= 0:
            key_pressed = False
            try:
                print(f"Начало воспроизведения через микрофон (устройство {mic_index})")
                # Конвертируем в WAV, если это MP3
                if audio_file.endswith('.mp3'):
                    wav_file = self._convert_mp3_to_wav(audio_file)
                else:
                    wav_file = audio_file
                # Проверка на None
                if not wav_file or not os.path.exists(wav_file):
                    print(f"Файл для воспроизведения через микрофон не найден: {wav_file}")
                    return
                wf = wave.open(wav_file, 'rb')
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                rate = wf.getframerate()
                stream = self.p.open(format=self.p.get_format_from_width(width),
                                    channels=channels,
                                    rate=rate,
                                    output=True,
                                    output_device_index=mic_index)
                chunk_size = 1024
                data = wf.readframes(chunk_size)
                
                # Проверяем наличие аудиоданных перед нажатием клавиши
                if len(data) > 0 and self.settings.voice_chat_key:
                    key = self.settings.voice_chat_key
                    logging.info(f"[MIC KEY] Нажимаем клавишу микрофона '{key}'")
                    
                    # Нажимаем клавишу микрофона оптимизированным методом
                    key_pressed = self._press_mic_key()
                    logging.info(f"[MIC KEY] Клавиша микрофона активирована: {key_pressed}")
                
                try:
                    while len(data) > 0:
                        audio_data = np.frombuffer(data, dtype=np.int16)
                        # Усиление громкости выше 100%
                        audio_data = np.clip(audio_data * self.settings.mic_volume, -32768, 32767).astype(np.int16)
                        stream.write(audio_data.tobytes())
                        data = wf.readframes(chunk_size)
                finally:
                    # Гарантированное освобождение клавиши только если она была нажата
                    if key_pressed and self.settings.voice_chat_key:
                        # Отпускаем клавишу микрофона
                        self._release_mic_key()
                        logging.info(f"[MIC KEY] Клавиша микрофона деактивирована")
                
                stream.stop_stream()
                stream.close()
                wf.close()
                print("Воспроизведение через микрофон завершено")
            except Exception as e:
                print(f"Ошибка при воспроизведении через микрофон: {e}")
                logging.error(f"Ошибка при воспроизведении через микрофон: {e}")
                # Гарантированное освобождение клавиши в случае ошибки
                if key_pressed and self.settings.voice_chat_key:
                    self._release_mic_key()
                    logging.info(f"[MIC KEY] Клавиша микрофона деактивирована после ошибки")
    
    def _convert_mp3_to_wav(self, mp3_file):
        # Используем pydub для конвертации из mp3 в wav
        try:
            print("Конвертация MP3 в WAV...")
            # Создаем временный wav файл
            temp_wav = tempfile.mktemp(suffix='.wav')
            # Конвертируем MP3 в WAV с помощью pydub
            try:
                # Проверяем наличие ffmpeg в системе или в папке приложения
                ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin")
                if os.path.exists(os.path.join(ffmpeg_path, "ffmpeg.exe")):
                    # Если ffmpeg есть в папке приложения, добавляем путь в PATH
                    os.environ["PATH"] += os.pathsep + ffmpeg_path
                    print(f"Путь к ffmpeg добавлен в PATH: {ffmpeg_path}")
                sound = AudioSegment.from_mp3(mp3_file)
                sound.export(temp_wav, format="wav")
                print(f"Файл успешно конвертирован в {temp_wav}")
                return temp_wav
            except Exception as e:
                print(f"Ошибка при конвертации с помощью pydub: {e}")
                return None
        except Exception as e:
            print(f"Ошибка при конвертации MP3 в WAV: {e}")
            return None
    
    def open_settings(self):
        print("Открытие окна настроек")
        self._check_topmost_enabled = False
        keyboard.unhook_all()
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройки TTS Overlay")
        settings_window.geometry("600x470")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        settings_window.attributes('-topmost', True)
        settings_window.configure(bg="#2d2d2d")
        
        def on_close_settings():
            settings_window.destroy()
            self._check_topmost_enabled = True
            self.check_topmost()
            self.register_hotkeys()
        settings_window.protocol("WM_DELETE_WINDOW", on_close_settings)
        
        # Создаем фрейм для содержимого
        content_frame = ttk.Frame(settings_window, padding=10)
        content_frame.pack(fill='both', expand=True)
        
        # Создаем вкладки
        notebook = ttk.Notebook(content_frame)
        # Добавляем отступы между вкладками
        style = ttk.Style()
        style.configure("TNotebook.Tab", padding=[12, 6])
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Вкладка "Устройства"
        devices_frame = ttk.Frame(notebook, padding=10)
        notebook.add(devices_frame, text="Устройства")
        
        # Вкладка "Движок TTS"
        engine_frame = ttk.Frame(notebook, padding=10)
        notebook.add(engine_frame, text="Движок TTS")
        
        # Вкладка "Горячие клавиши"
        hotkeys_frame = ttk.Frame(notebook, padding=10)
        notebook.add(hotkeys_frame, text="Горячие клавиши")
        
        # Вкладка "О программе"
        about_frame = ttk.Frame(notebook, padding=10)
        notebook.add(about_frame, text="О программе")
        
        # === Настройки устройств ===
        ttk.Label(devices_frame, text="Устройство вывода:").grid(row=0, column=0, sticky='w', pady=5)
        
        # Получаем список устройств вывода
        output_device_var = tk.StringVar()
        output_device_combo = ttk.Combobox(devices_frame, textvariable=output_device_var, width=50, state="readonly")
        output_device_combo['values'] = [device[1] for device in self.output_devices]
        
        # Устанавливаем текущее устройство
        current_device_index = self.settings.output_device_index
        if 0 <= current_device_index < len(self.output_devices):
            output_device_var.set(self.output_devices[current_device_index][1])
        
        output_device_combo.grid(row=0, column=1, sticky='w', pady=5)
        
        # Громкость вывода
        ttk.Label(devices_frame, text="Громкость вывода:").grid(row=1, column=0, sticky='w', pady=5)
        
        output_volume_var = tk.DoubleVar(value=self.settings.output_volume)
        output_volume_slider = ttk.Scale(devices_frame, from_=0.0, to=2.0, orient='horizontal', 
                                        variable=output_volume_var, length=300)
        output_volume_slider.grid(row=1, column=1, sticky='w', pady=5)
        
        output_volume_label = ttk.Label(devices_frame, text=f"{int(output_volume_var.get() * 100)}%")
        output_volume_label.grid(row=1, column=2, sticky='w', pady=5)
        
        def update_output_volume(*args):
            output_volume_label.config(text=f"{int(output_volume_var.get() * 100)}%")
        
        output_volume_var.trace('w', update_output_volume)
        
        # Виртуальный микрофон
        ttk.Label(devices_frame, text="Виртуальный микрофон:").grid(row=2, column=0, sticky='w', pady=5)
        
        # Получаем список устройств микрофона
        mic_devices = []
        mic_devices.append((-1, "Отключено"))
        
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            max_output_channels = int(device_info['maxOutputChannels'])
            if max_output_channels > 0:
                name = device_info['name']
                mic_devices.append((i, name))
        
        mic_device_var = tk.StringVar()
        mic_device_combo = ttk.Combobox(devices_frame, textvariable=mic_device_var, width=50, state="readonly")
        mic_device_combo['values'] = [device[1] for device in mic_devices]
        
        # Устанавливаем текущий микрофон
        current_mic_index = self.settings.mic_device_index
        for i, device in enumerate(mic_devices):
            if device[0] == current_mic_index:
                mic_device_var.set(device[1])
                break
        else:
            mic_device_var.set(mic_devices[0][1])  # По умолчанию "Отключено"
        
        mic_device_combo.grid(row=2, column=1, sticky='w', pady=5)
        
        # Громкость микрофона
        ttk.Label(devices_frame, text="Громкость микрофона:").grid(row=3, column=0, sticky='w', pady=5)
        
        mic_volume_var = tk.DoubleVar(value=self.settings.mic_volume)
        mic_volume_slider = ttk.Scale(devices_frame, from_=0.0, to=2.0, orient='horizontal', 
                                     variable=mic_volume_var, length=300)
        mic_volume_slider.grid(row=3, column=1, sticky='w', pady=5)
        
        mic_volume_label = ttk.Label(devices_frame, text=f"{int(mic_volume_var.get() * 100)}%")
        mic_volume_label.grid(row=3, column=2, sticky='w', pady=5)
        
        def update_mic_volume(*args):
            mic_volume_label.config(text=f"{int(mic_volume_var.get() * 100)}%")
        
        mic_volume_var.trace('w', update_mic_volume)
        
        # === Настройки движка TTS ===
        ttk.Label(engine_frame, text="Движок TTS:").grid(row=0, column=0, sticky='w', pady=5)
        
        engine_var = tk.StringVar(value=self.settings.tts_engine)
        
        engines = [
            ("Google TTS", "google"),
            ("Локальный TTS", "local"),
            ("VoiceRSS TTS", "voicerss")
        ]
        
        for i, (text, value) in enumerate(engines):
            ttk.Radiobutton(engine_frame, text=text, value=value, variable=engine_var).grid(
                row=i, column=0, sticky='w', pady=2)
        
        # Функция для переключения отображения настроек в зависимости от выбранного движка
        def toggle_engine():
            selected = engine_var.get()
            
            # Скрываем все фреймы настроек
            local_frame.grid_forget()
            voicerss_frame.grid_forget()
            
            # Показываем соответствующий фрейм
            if selected == "local":
                local_frame.grid(row=len(engines), column=0, columnspan=2, sticky='w', pady=10)
            elif selected == "voicerss":
                voicerss_frame.grid(row=len(engines), column=0, columnspan=2, sticky='w', pady=10)
        
        # Привязываем функцию к изменению переменной
        engine_var.trace('w', lambda *args: toggle_engine())
        
        # === Настройки локального движка ===
        local_frame = ttk.LabelFrame(engine_frame, text="Настройки локального движка", padding=10)
        
        ttk.Label(local_frame, text="Голос:").grid(row=0, column=0, sticky='w', pady=5)
        
        # Получаем список доступных голосов
        voices = self.engine.getProperty('voices')
        voice_var = tk.StringVar()
        voice_combo = ttk.Combobox(local_frame, textvariable=voice_var, width=50, state="readonly")
        voice_combo['values'] = [f"{voice.name} ({voice.id})" for voice in voices]
        
        # Устанавливаем текущий голос
        current_voice_id = self.settings.voice_id
        for i, voice in enumerate(voices):
            if voice.id == current_voice_id:
                voice_var.set(f"{voice.name} ({voice.id})")
                break
        else:
            if voices:
                voice_var.set(f"{voices[0].name} ({voices[0].id})")
        
        voice_combo.grid(row=0, column=1, sticky='w', pady=5)
        
        # === Настройки VoiceRSS ===
        voicerss_frame = ttk.LabelFrame(engine_frame, text="Настройки VoiceRSS", padding=10)
        
        ttk.Label(voicerss_frame, text="API ключ:").grid(row=0, column=0, sticky='w', pady=5)
        
        voicerss_api_var = tk.StringVar(value=self.settings.voicerss_api_key)
        voicerss_api_entry = ttk.Entry(voicerss_frame, textvariable=voicerss_api_var, width=50)
        voicerss_api_entry.grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(voicerss_frame, text="Язык:").grid(row=1, column=0, sticky='w', pady=5)
        
        # Получаем список доступных языков
        languages = {}
        if VoiceRSSAPI is not None:
            api = VoiceRSSAPI()
            languages = api.get_available_languages()
        
        voicerss_language_var = tk.StringVar()
        voicerss_language_combo = ttk.Combobox(voicerss_frame, textvariable=voicerss_language_var, width=50, state="readonly")
        voicerss_language_combo['values'] = [f"{code}: {name}" for code, name in languages.items()]
        
        # Устанавливаем текущий язык
        current_language = self.settings.voicerss_language
        for code, name in languages.items():
            if code == current_language:
                voicerss_language_var.set(f"{code}: {name}")
                break
        else:
            if languages:
                first_code = next(iter(languages.keys()))
                voicerss_language_var.set(f"{first_code}: {languages[first_code]}")
        
        voicerss_language_combo.grid(row=1, column=1, sticky='w', pady=5)
        
        ttk.Label(voicerss_frame, text="Голос:").grid(row=2, column=0, sticky='w', pady=5)
        
        voicerss_voice_var = tk.StringVar()
        voicerss_voice_combo = ttk.Combobox(voicerss_frame, textvariable=voicerss_voice_var, width=50, state="readonly")
        
        # Функция для обновления списка голосов при изменении языка
        def update_voicerss_voices(*args):
            if VoiceRSSAPI is None:
                return
            
            try:
                api = VoiceRSSAPI()
                language_selection = voicerss_language_var.get()
                
                if ":" in language_selection:
                    language_code = language_selection.split(":")[0].strip()
                    voices_list = api.get_available_voices(language_code)
                    
                    if isinstance(voices_list, list):
                        voicerss_voice_combo['values'] = [f"{voice.get('name', '')} ({voice.get('gender', '')})" for voice in voices_list]
                        
                        # Устанавливаем текущий голос
                        current_voice = self.settings.voicerss_voice
                        for voice in voices_list:
                            if voice.get('name', '') == current_voice:
                                voicerss_voice_var.set(f"{voice.get('name', '')} ({voice.get('gender', '')})")
                                break
                        else:
                            if voices_list:
                                first_voice = voices_list[0]
                                voicerss_voice_var.set(f"{first_voice.get('name', '')} ({first_voice.get('gender', '')})")
            except Exception as e:
                print(f"Ошибка при обновлении списка голосов: {e}")
        
        voicerss_language_var.trace('w', update_voicerss_voices)
        
        # Вызываем функцию для начальной загрузки голосов
        update_voicerss_voices()
        
        voicerss_voice_combo.grid(row=2, column=1, sticky='w', pady=5)
        
        # === Настройки горячих клавиш ===
        # Валидация ввода: только латиница, цифры и спецклавиши
        allowed_keys = set([
            'ctrl', 'alt', 'shift', 'tab', 'space', 'enter', 'esc', 'backspace', 'capslock',
            'left', 'right', 'up', 'down', 'insert', 'delete', 'home', 'end', 'pageup', 'pagedown',
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12'
        ] + [chr(c) for c in range(ord('a'), ord('z')+1)] + [str(d) for d in range(0,10)])
        
        # Функция для создания поля ввода горячей клавиши
        def create_hotkey_field(parent, row, label_text, default_value, tooltip_text=None):
            ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky='w', pady=5, padx=0)
            
            # Создаем фрейм для поля ввода и кнопки
            frame = ttk.Frame(parent)
            frame.grid(row=row, column=1, columnspan=3, sticky='w', pady=5, padx=(2,0))
            
            # Создаем переменную и поле ввода
            var = tk.StringVar(value=default_value)
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(side='left', padx=(0,2), pady=0)
            
            # Функция валидации
            def validate(event=None):
                key_text = var.get().strip().lower()
                # Проверяем комбинации клавиш (например, alt+t)
                if "+" in key_text:
                    parts = key_text.split("+")
                    valid = all(part in allowed_keys for part in parts)
                else:
                    valid = key_text in allowed_keys or not key_text
                
                if key_text and not valid:
                    messagebox.showwarning("Недопустимая клавиша", 
                                          "Разрешены только английские буквы, цифры и спецклавиши (ctrl, alt, shift, tab, ...)\n"
                                          "Для комбинаций используйте формат: alt+t, ctrl+shift+f и т.д.")
                    var.set("")
            
            # Привязываем валидацию
            entry.bind('<FocusOut>', validate)
            entry.bind('<Return>', validate)
            
            # Кнопка очистки
            def clear():
                var.set("")
            
            clear_button = ttk.Button(frame, text="Х", width=2, command=clear)
            clear_button.pack(side='left', padx=(0,0), pady=0)
            
            # Добавляем подсказку, если она указана
            if tooltip_text:
                ttk.Label(parent, text=tooltip_text, foreground="#666666", font=("Arial", 8)).grid(
                    row=row+1, column=0, columnspan=4, sticky='w', pady=(0,5), padx=(15,0))
            
            return var
        
        # Клавиша для переключения видимости окна
        toggle_visibility_var = create_hotkey_field(
            hotkeys_frame, 0, 
            "Клавиша для открытия/закрытия окна:", 
            self.settings.toggle_visibility_key or "alt+t",
            "Нажатие этой клавиши будет открывать или закрывать окно программы (по умолчанию alt+t)"
        )
        
        # Клавиша для открытия окна
        focus_window_var = create_hotkey_field(
            hotkeys_frame, 2, 
            "Дополнительная клавиша для открытия окна:", 
            self.settings.focus_window_key or "",
            "Нажатие этой клавиши будет только открывать окно программы, не закрывая его (опционально)"
        )
        
        # Клавиша для голосового чата
        voice_chat_key_var = create_hotkey_field(
            hotkeys_frame, 4, 
            "Клавиша для голосового чата в игре:", 
            self.settings.voice_chat_key or "",
            "Эта клавиша будет автоматически нажиматься при озвучивании текста"
        )
        
        # Модификатор для истории
        ttk.Label(hotkeys_frame, text="Модификатор для истории (по умолчанию Ctrl):").grid(row=6, column=0, sticky='w', pady=5)
        modifiers = ["ctrl", "alt", "shift"] + [chr(c) for c in range(ord('a'), ord('z')+1)]
        history_modifier_var = tk.StringVar(value=self.settings.history_hotkey_modifier or "ctrl")
        history_modifier_combo = ttk.Combobox(hotkeys_frame, textvariable=history_modifier_var, width=10, state="readonly")
        history_modifier_combo['values'] = modifiers
        history_modifier_combo.grid(row=6, column=1, sticky='w', pady=5, padx=(40,0))
        ttk.Label(hotkeys_frame, text="Используется для комбинаций с цифрами для воспроизведения истории фраз", 
                 foreground="#666666", font=("Arial", 8)).grid(
            row=7, column=0, columnspan=4, sticky='w', pady=(0,5), padx=(15,0))
        
        # Чекбокс "Убрать очередь"
        remove_queue_var = tk.BooleanVar(value=getattr(self.settings, 'remove_queue', False))
        remove_queue_check = ttk.Checkbutton(hotkeys_frame, text="Убрать очередь (спамить ГС без задержки)", variable=remove_queue_var)
        remove_queue_check.grid(row=8, column=0, columnspan=2, sticky='w', pady=8)
        
        # === О программе ===
        ttk.Label(about_frame, text="TTS Overlay", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(about_frame, text="Версия 1.3.0").pack(pady=5)
        ttk.Label(about_frame, text="© 2023-2024").pack(pady=5)
        
        # Информация о кэше
        cache_size = self.get_cache_size()
        ttk.Label(about_frame, text=f"Размер кэша: {cache_size:.2f} МБ").pack(pady=5)
        
        # Кнопка очистки кэша
        clear_cache_button = ttk.Button(about_frame, text="Очистить кэш", 
                                       command=lambda: clear_cache())
        clear_cache_button.pack(pady=10)
        
        def clear_cache():
            try:
                # Очищаем папку кэша
                cache_folder = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), "cache")
                for root, dirs, files in os.walk(cache_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            os.unlink(file_path)
                        except Exception as e:
                            print(f"Ошибка при удалении файла {file_path}: {e}")
                
                messagebox.showinfo("Очистка кэша", "Кэш успешно очищен")
                
                # Обновляем информацию о размере кэша
                cache_size = self.get_cache_size()
                ttk.Label(about_frame, text=f"Размер кэша: {cache_size:.2f} МБ").pack(pady=5)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось очистить кэш: {e}")
        
        # Кнопки внизу окна
        buttons_frame = ttk.Frame(settings_window)
        buttons_frame.pack(fill='x', pady=10, padx=10)
        
        # Настраиваем стиль кнопок, чтобы они были более заметными
        style = ttk.Style()
        style.configure("SaveButton.TButton", font=("Arial", 10, "bold"), padding=6)
        style.configure("CancelButton.TButton", font=("Arial", 10), padding=6)
        
        save_button = ttk.Button(buttons_frame, text="Сохранить", style="SaveButton.TButton",
                                command=lambda: save_settings())
        save_button.pack(side='right', padx=5)
        
        cancel_button = ttk.Button(buttons_frame, text="Отмена", style="CancelButton.TButton", 
                                  command=on_close_settings)
        cancel_button.pack(side='right', padx=5)
        
        def save_settings():
            try:
                # Сохраняем громкость
                self.settings.output_volume = output_volume_var.get()
                self.settings.mic_volume = mic_volume_var.get()
                
                # Сохраняем движок
                self.settings.tts_engine = engine_var.get()
                
                # Сохраняем выбранный голос для локального движка
                if self.settings.tts_engine == "local":
                    selected_voice = voice_var.get()
                    for voice in voices:
                        if f"{voice.name} ({voice.id})" == selected_voice:
                            self.settings.voice_id = voice.id
                            break
                
                # Сохраняем настройки VoiceRSS
                if self.settings.tts_engine == "voicerss":
                    # Сохраняем язык
                    language_selection = voicerss_language_var.get()
                    if ":" in language_selection:
                        self.settings.voicerss_language = language_selection.split(":")[0].strip()
                    
                    # Сохраняем голос
                    voice_selection = voicerss_voice_var.get()
                    if "(" in voice_selection:
                        self.settings.voicerss_voice = voice_selection.split("(")[0].strip()
                    
                    # Сохраняем API ключ
                    self.settings.voicerss_api_key = voicerss_api_var.get()
                
                # Сохраняем устройство вывода
                output_device_name = output_device_var.get()
                for i, device in enumerate(self.output_devices):
                    if device[1] == output_device_name:
                        self.settings.output_device_index = i
                        break
                
                # Сохраняем устройство микрофона
                mic_device_name = mic_device_var.get()
                for device in mic_devices:
                    if device[1] == mic_device_name:
                        self.settings.mic_device_index = device[0]
                        break
                
                # Сохраняем клавишу для переключения видимости окна
                toggle_key = toggle_visibility_var.get().strip().lower()
                if toggle_key and toggle_key != "alt+t":
                    self.settings.toggle_visibility_key = toggle_key
                else:
                    self.settings.toggle_visibility_key = "alt+t"  # Значение по умолчанию
                
                # Сохраняем клавишу для открытия окна
                focus_key = focus_window_var.get().strip().lower()
                if focus_key == "не задано" or not focus_key:
                    self.settings.focus_window_key = None
                else:
                    self.settings.focus_window_key = focus_key
                
                # Сохраняем клавишу для голосового чата
                voice_chat_key = voice_chat_key_var.get().strip().lower()
                if voice_chat_key == "не задано" or not voice_chat_key:
                    self.settings.voice_chat_key = None
                else:
                    self.settings.voice_chat_key = voice_chat_key
                
                # Сохраняем модификатор для истории
                self.settings.history_hotkey_modifier = history_modifier_var.get()
                self.settings.remove_queue = remove_queue_var.get()
                
                # Сохраняем настройки в файл
                self.settings.save_settings()
                
                # Закрываем окно настроек
                on_close_settings()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")
        
        # Показываем соответствующий фрейм настроек при открытии окна
        toggle_engine()
    
    def open_url(self, url):
        """Открывает URL в браузере по умолчанию"""
        import webbrowser
        webbrowser.open(url)
    
    def get_cache_size(self):
        """Получение размера кэша в MB"""
        total_size = 0
        if os.path.exists(self.cache_folder):
            for file in os.listdir(self.cache_folder):
                file_path = os.path.join(self.cache_folder, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
        
        # Конвертируем байты в мегабайты
        return total_size / (1024 * 1024)
    
    def cleanup_cache(self):
        """Фоновый поток для очистки старых файлов кэша"""
        while True:
            try:
                # Проверяем каждые 6 часов
                time.sleep(6 * 60 * 60)
                
                # Максимальный размер кэша (в байтах) - 100 МБ
                max_cache_size = 100 * 1024 * 1024
                
                if os.path.exists(self.cache_folder):
                    # Получаем список файлов в кэше с их размерами и временем изменения
                    files = []
                    total_size = 0
                    
                    for file_name in os.listdir(self.cache_folder):
                        file_path = os.path.join(self.cache_folder, file_name)
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            file_time = os.path.getmtime(file_path)
                            files.append((file_path, file_size, file_time))
                            total_size += file_size
                    
                    # Если размер кэша превышает максимальный, удаляем старые файлы
                    if total_size > max_cache_size:
                        # Сортируем файлы по времени изменения (от старых к новым)
                        files.sort(key=lambda x: x[2])
                        
                        # Удаляем старые файлы, пока размер кэша не станет меньше максимального
                        for file_path, file_size, _ in files:
                            try:
                                os.remove(file_path)
                                total_size -= file_size
                                print(f"Удален старый файл кэша: {file_path}")
                                
                                if total_size <= max_cache_size:
                                    break
                            except Exception as e:
                                print(f"Ошибка при удалении файла кэша {file_path}: {e}")
            except Exception as e:
                print(f"Ошибка в потоке очистки кэша: {e}")
    
    def stop_playback(self):
        """Быстрая остановка воспроизведения"""
        import pygame
        self._tts_stop_flag = True
        
        # Отпускаем клавишу микрофона, если она нажата
        if self.settings.voice_chat_key:
            self._release_mic_key()
        
        # Глушим звук
        if pygame.mixer.get_init():
            pygame.mixer.stop()
        
        # Останавливаем все движки pyttsx3
        for engine in list(self._tts_engines):
            try:
                engine.stop()
                self._tts_engines.remove(engine)
            except Exception:
                pass
        
        # Сигнализируем потокам завершиться
        for ev in list(self._tts_events):
            ev.set()
        
        # Очищаем активные потоки
        self.active_tts_threads.clear()
        self._tts_events.clear()
        self.set_status("⏹ Воспроизведение остановлено")
        
    def check_and_fix_key_stuck(self):
        if self.settings.voice_chat_key:
            try:
                if keyboard.is_pressed(self.settings.voice_chat_key):
                    with self.tts_lock:
                        self._release_mic_key()
            except Exception as e:
                logging.error(f"Ошибка при проверке залипшей клавиши: {e}")
    
    def load_phrase(self, index):
        """Загрузка фразы из истории по индексу (только для вставки в поле, не для воспроизведения)"""
        if 0 <= index < len(self.phrase_history) and self.phrase_history[index]:
            # Очищаем текущий текст
            self.text_entry.delete("1.0", tk.END)
            # Вставляем текст из истории
            self.text_entry.insert("1.0", self.phrase_history[index])
            self.set_status(f"Загружена фраза {index+1}: {self.phrase_history[index][:20]}...")
            # Не воспроизводим и не добавляем в историю
    
    def set_status(self, text):
        """Установка текста в строке статуса"""
        self.status_var.set(text)
    
    def check_topmost(self):
        if getattr(self, '_check_topmost_enabled', True):
            if self.root.state() != 'withdrawn':
                self.root.attributes('-topmost', True)
                self.root.lift()
            
            # Периодически проверяем, не "залипла" ли клавиша микрофона
            self.check_and_fix_key_stuck()
            
        self.root.after(2000, self.check_topmost)

    def _send_input_key(self, key_code, press=True):
        """
        Оптимизированная эмуляция нажатия/отпускания клавиши через SendInput API.
        """
        try:
            # Преобразуем строковый ключ в код виртуальной клавиши
            if isinstance(key_code, str):
                if key_code.lower() in VK_CODE:
                    key_code = VK_CODE[key_code.lower()]
                elif len(key_code) == 1 and key_code.isalpha():
                    key_code = ord(key_code.upper())
                else:
                    logging.error(f"Неизвестный код клавиши: {key_code}")
                    return False
            
            # Определяем структуры для SendInput
            LONG = ctypes.c_long
            DWORD = ctypes.c_ulong
            ULONG_PTR = ctypes.POINTER(DWORD)
            WORD = ctypes.c_ushort
            
            class MOUSEINPUT(ctypes.Structure):
                _fields_ = (("dx", LONG), ("dy", LONG), ("mouseData", DWORD),
                           ("dwFlags", DWORD), ("time", DWORD), ("dwExtraInfo", ULONG_PTR))
            
            class KEYBDINPUT(ctypes.Structure):
                _fields_ = (("wVk", WORD), ("wScan", WORD), ("dwFlags", DWORD),
                           ("time", DWORD), ("dwExtraInfo", ULONG_PTR))
            
            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = (("uMsg", DWORD), ("wParamL", WORD), ("wParamH", WORD))
            
            class _INPUTunion(ctypes.Union):
                _fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))
            
            class INPUT(ctypes.Structure):
                _fields_ = (("type", DWORD), ("_input", _INPUTunion))
            
            # Константы
            INPUT_KEYBOARD = 1
            KEY_KEYUP = 0x0002
            
            # Создаем структуру для нажатия/отпускания клавиши
            x = INPUT(type=INPUT_KEYBOARD, 
                     _input=_INPUTunion(ki=KEYBDINPUT(wVk=key_code, 
                                                     wScan=0, 
                                                     dwFlags=0 if press else KEY_KEYUP, 
                                                     time=0, 
                                                     dwExtraInfo=None)))
            
            # Отправляем ввод
            ctypes.windll.user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
            return True
        except Exception as e:
            logging.error(f"Ошибка при использовании SendInput API: {e}")
            try:
                # Резервный метод через keyboard
                if press:
                    keyboard.press(key_code)
                else:
                    keyboard.release(key_code)
                return True
            except:
                return False

    def _test_key_methods(self):
        """
        Упрощенный тест эмуляции клавиш при запуске приложения.
        """
        if not self.settings.voice_chat_key:
            logging.warning("Клавиша микрофона не задана, тестирование пропущено")
            return
        
        key = self.settings.voice_chat_key
        logging.info(f"Тестирование методов эмуляции клавиши '{key}'...")
        
        # Тест SendInput API
        try:
            logging.debug("Тест SendInput API...")
            success = self._send_input_key(key, press=True)
            time.sleep(0.05)
            self._send_input_key(key, press=False)
            if success:
                logging.info("SendInput API работает")
            else:
                logging.warning("SendInput API не работает")
        except Exception as e:
            logging.error(f"Ошибка при тестировании SendInput API: {e}")
        
        # Тест библиотеки keyboard
        try:
            logging.debug("Тест библиотеки keyboard...")
            keyboard.press(key)
            time.sleep(0.05)
            is_pressed = keyboard.is_pressed(key)
            keyboard.release(key)
            if is_pressed:
                logging.info("Библиотека keyboard работает")
            else:
                logging.warning("Библиотека keyboard не работает")
        except Exception as e:
            logging.error(f"Ошибка при тестировании библиотеки keyboard: {e}")
        
        logging.info("Тестирование методов эмуляции клавиш завершено")
    


if __name__ == "__main__":
    logging.debug("Запуск приложения")
    try:
        app = TTSOverlay()
        app.run()
    except Exception as e:
        logging.exception("Критическая ошибка при запуске приложения:")
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc() 