#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для запуска TTS Overlay с автоматической установкой зависимостей
"""

import os
import sys
import subprocess
import importlib
import platform
import shutil
import zipfile
import urllib.request
import tempfile
from pathlib import Path

# Список необходимых библиотек
REQUIRED_PACKAGES = [
    "pygame",
    "pyaudio",
    "numpy",
    "gtts",
    "pyttsx3",
    "TKinterModernThemes",
    "keyboard",
    "pydub"
]

def install_package(package):
    """Установка пакета через pip"""
    print(f"Установка {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_and_install_dependencies():
    """Проверка и установка зависимостей"""
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package)
            print(f"✓ {package} уже установлен")
        except ImportError:
            print(f"✗ {package} не установлен")
            install_package(package)
    
    # Проверка наличия ffmpeg для pydub
    if not check_ffmpeg():
        print("✗ ffmpeg не установлен")
        install_ffmpeg()
    else:
        print("✓ ffmpeg уже установлен")

def check_ffmpeg():
    """Проверка наличия ffmpeg в системе"""
    try:
        # Проверяем, доступен ли ffmpeg в системе
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        # Проверяем, есть ли ffmpeg в папке приложения
        ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", "bin")
        if os.path.exists(os.path.join(ffmpeg_path, "ffmpeg.exe")):
            # Добавляем путь к ffmpeg в PATH
            os.environ["PATH"] += os.pathsep + ffmpeg_path
            return True
        return False

def install_ffmpeg():
    """Установка ffmpeg для Windows"""
    if platform.system() != "Windows":
        print("Автоматическая установка ffmpeg поддерживается только для Windows.")
        print("Пожалуйста, установите ffmpeg вручную: https://ffmpeg.org/download.html")
        return
    
    try:
        print("Загрузка ffmpeg...")
        
        # Используем прямую ссылку на официальный релиз ffmpeg для Windows
        ffmpeg_url = "https://github.com/GyanD/codexffmpeg/releases/download/6.0/ffmpeg-6.0-essentials_build.zip"
        temp_zip = os.path.join(tempfile.gettempdir(), "ffmpeg.zip")
        
        # Загружаем архив
        urllib.request.urlretrieve(ffmpeg_url, temp_zip)
        print(f"Архив загружен: {temp_zip}")
        
        # Создаем папку для ffmpeg
        ffmpeg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg")
        if not os.path.exists(ffmpeg_dir):
            os.makedirs(ffmpeg_dir)
            print(f"Создана папка: {ffmpeg_dir}")
        
        # Распаковываем архив
        print("Распаковка ffmpeg...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        
        # Перемещаем файлы из подпапки в корневую папку ffmpeg
        extracted_dir = next(Path(ffmpeg_dir).glob("ffmpeg-*"))
        print(f"Извлеченная директория: {extracted_dir}")
        
        # Создаем папку bin, если её нет
        bin_dir = os.path.join(ffmpeg_dir, "bin")
        if not os.path.exists(bin_dir):
            os.makedirs(bin_dir)
        
        # Перемещаем файлы ffmpeg.exe, ffplay.exe и ffprobe.exe в папку bin
        for file in ["ffmpeg.exe", "ffplay.exe", "ffprobe.exe"]:
            src_file = os.path.join(extracted_dir, "bin", file)
            dst_file = os.path.join(bin_dir, file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                print(f"Файл {file} скопирован в {dst_file}")
        
        # Удаляем временные файлы
        shutil.rmtree(str(extracted_dir), ignore_errors=True)
        os.remove(temp_zip)
        
        # Добавляем путь к ffmpeg в PATH
        os.environ["PATH"] += os.pathsep + bin_dir
        print(f"Путь {bin_dir} добавлен в переменную PATH")
        
        print("✓ ffmpeg успешно установлен")
        
        # Проверяем установку
        try:
            result = subprocess.run([os.path.join(bin_dir, "ffmpeg"), "-version"], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Версия ffmpeg: {result.stdout.decode('utf-8', errors='ignore').splitlines()[0]}")
        except Exception as e:
            print(f"Ошибка при проверке установки ffmpeg: {e}")
        
    except Exception as e:
        print(f"Ошибка при установке ffmpeg: {e}")
        print("Пожалуйста, установите ffmpeg вручную: https://ffmpeg.org/download.html")

def main():
    """Основная функция запуска приложения"""
    print("Проверка зависимостей...")
    check_and_install_dependencies()
    
    print("\nЗапуск TTS Overlay...")
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_overlay.py")
    
    try:
        # Запуск основного приложения
        subprocess.run([sys.executable, script_path])
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
        input("Нажмите Enter для выхода...")
        sys.exit(1)

if __name__ == "__main__":
    main() 