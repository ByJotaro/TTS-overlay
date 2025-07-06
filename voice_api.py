#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для интеграции с VoiceRSS API
Предоставляет доступ к большему количеству голосов для TTS Overlay
"""

import os
import requests
import json
import hashlib
import tempfile
from urllib.parse import urlencode
from typing import Dict, List, Optional, Any, Union, Tuple

class VoiceRSSAPI:
    """Класс для работы с VoiceRSS API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Инициализация API ключа"""
        # Если ключ не указан, используем бесплатный демо-ключ (ограниченное количество запросов)
        self.api_key = api_key or "c7497b03d1c8437c90d1f50d2a9698d0"
        self.base_url = "https://api.voicerss.org/"
        self.cache_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "voicerss")
        
        # Создаем папку для кэша, если её нет
        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)
    
    def get_available_languages(self) -> Dict[str, str]:
        """Получение списка доступных языков"""
        return {
            "ru-ru": "Русский",
            "en-us": "Английский (США)",
            "en-gb": "Английский (Великобритания)",
            "en-au": "Английский (Австралия)",
            "en-ca": "Английский (Канада)",
            "en-in": "Английский (Индия)",
            "en-ie": "Английский (Ирландия)",
            "fr-fr": "Французский",
            "fr-ca": "Французский (Канада)",
            "fr-ch": "Французский (Швейцария)",
            "de-de": "Немецкий",
            "it-it": "Итальянский",
            "es-es": "Испанский",
            "es-mx": "Испанский (Мексика)",
            "ja-jp": "Японский",
            "ko-kr": "Корейский",
            "zh-cn": "Китайский (материковый)",
            "zh-hk": "Китайский (Гонконг)",
            "zh-tw": "Китайский (Тайвань)",
            "pt-br": "Португальский (Бразилия)",
            "pt-pt": "Португальский",
            "ar-sa": "Арабский",
            "ar-eg": "Арабский (Египет)",
            "cs-cz": "Чешский",
            "da-dk": "Датский",
            "fi-fi": "Финский",
            "hi-in": "Хинди",
            "id-id": "Индонезийский",
            "nl-nl": "Голландский",
            "nl-be": "Голландский (Бельгия)",
            "no-no": "Норвежский",
            "pl-pl": "Польский",
            "sv-se": "Шведский",
            "tr-tr": "Турецкий",
            "th-th": "Тайский",
            "vi-vn": "Вьетнамский",
            "el-gr": "Греческий",
            "hu-hu": "Венгерский",
            "ro-ro": "Румынский",
            "sk-sk": "Словацкий",
            "uk-ua": "Украинский"
        }
    
    def get_available_voices(self, language_code: Optional[str] = None) -> Union[Dict[str, List[Dict[str, str]]], List[Dict[str, str]]]:
        """Получение списка доступных голосов для указанного языка"""
        voices = {
            "ru-ru": [
                {"name": "Maxim", "gender": "male"},
                {"name": "Tatyana", "gender": "female"}
            ],
            "en-us": [
                {"name": "Linda", "gender": "female"},
                {"name": "Amy", "gender": "female"},
                {"name": "Mary", "gender": "female"},
                {"name": "John", "gender": "male"},
                {"name": "Mike", "gender": "male"}
            ],
            "en-gb": [
                {"name": "Alice", "gender": "female"},
                {"name": "Nancy", "gender": "female"},
                {"name": "Lily", "gender": "female"},
                {"name": "Harry", "gender": "male"}
            ],
            "en-au": [
                {"name": "Evie", "gender": "female"},
                {"name": "Jack", "gender": "male"}
            ],
            "fr-fr": [
                {"name": "Bette", "gender": "female"},
                {"name": "Iva", "gender": "female"},
                {"name": "Zola", "gender": "female"},
                {"name": "Axel", "gender": "male"}
            ],
            "de-de": [
                {"name": "Hilda", "gender": "female"},
                {"name": "Ralf", "gender": "male"}
            ],
            "it-it": [
                {"name": "Elisa", "gender": "female"},
                {"name": "Vittorio", "gender": "male"}
            ],
            "es-es": [
                {"name": "Camila", "gender": "female"},
                {"name": "Sofia", "gender": "female"},
                {"name": "Luna", "gender": "female"},
                {"name": "Diego", "gender": "male"},
                {"name": "Pedro", "gender": "male"}
            ]
        }
        
        # Для других языков добавляем стандартные голоса
        all_languages = self.get_available_languages()
        for lang_code in all_languages:
            if lang_code not in voices:
                voices[lang_code] = [
                    {"name": "Female", "gender": "female"},
                    {"name": "Male", "gender": "male"}
                ]
        
        if language_code:
            return voices.get(language_code, [])
        
        return voices
    
    def text_to_speech(self, text: str, language: str = "ru-ru", voice: Optional[str] = None, speed: int = 0) -> Optional[str]:
        """
        Преобразование текста в речь с помощью VoiceRSS API
        
        Args:
            text (str): Текст для преобразования
            language (str): Код языка (например, "ru-ru")
            voice (str): Имя голоса (если None, будет использован стандартный)
            speed (int): Скорость речи (-10 до 10)
            
        Returns:
            str: Путь к аудиофайлу или None в случае ошибки
        """
        # Создаем хэш для кэширования
        text_hash = hashlib.md5(f"{text}_{language}_{voice}_{speed}".encode()).hexdigest()
        cache_path = os.path.join(self.cache_folder, f"{text_hash}.mp3")
        
        # Проверяем, есть ли файл в кэше
        if os.path.exists(cache_path):
            print(f"Используется кэшированный файл VoiceRSS: {cache_path}")
            return cache_path
        
        # Формируем параметры запроса
        params = {
            "key": self.api_key,
            "src": text,
            "hl": language,
            "r": str(speed),
            "c": "MP3",
            "f": "16khz_16bit_stereo"
        }
        
        # Добавляем голос, если указан
        if voice:
            params["v"] = voice
        
        try:
            # Отправляем запрос к API
            response = requests.get(self.base_url, params=params)
            
            # Проверяем успешность запроса
            if response.status_code == 200 and not response.content.startswith(b"ERROR"):
                # Сохраняем аудио в кэш
                if response.content:
                    try:
                        with open(cache_path, "wb") as f:
                            f.write(response.content)
                        print(f"Аудио сохранено в кэш VoiceRSS: {cache_path}")
                        return cache_path
                    except Exception as e:
                        print(f"Ошибка при сохранении аудио в файл: {e}")
                        return None
                else:
                    print("Пустой ответ от VoiceRSS API")
                    return None
            else:
                error_message = response.content.decode("utf-8") if response.content.startswith(b"ERROR") else f"HTTP error {response.status_code}"
                print(f"Ошибка VoiceRSS API: {error_message}")
                return None
        except Exception as e:
            print(f"Ошибка при запросе к VoiceRSS API: {e}")
            return None
    
    def get_demo_key(self) -> str:
        """Получение демо-ключа для VoiceRSS API"""
        return "c7497b03d1c8437c90d1f50d2a9698d0"

# Пример использования
if __name__ == "__main__":
    api = VoiceRSSAPI()
    languages = api.get_available_languages()
    print(f"Доступные языки: {len(languages)}")
    
    # Выводим список голосов для русского языка
    ru_voices = api.get_available_voices("ru-ru")
    print(f"Голоса для русского языка: {ru_voices}")
    
    # Тестовый синтез
    audio_file = api.text_to_speech("Привет, это тест синтеза речи через VoiceRSS API", "ru-ru", "Maxim")
    if audio_file:
        print(f"Аудиофайл создан: {audio_file}") 