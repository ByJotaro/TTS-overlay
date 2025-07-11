# TTS Overlay

Приложение для преобразования текста в речь с функцией наложения на микрофон.
https://youtu.be/XkhJQhSlNck?si=JYilih4QKGbC_3rL

## Возможности

- Преобразование текста в речь с использованием Google TTS или локальных голосов Windows
- Выбор устройства вывода звука
- Передача звука в виртуальный микрофон (требуется Virtual Audio Cable или аналог)
- Настройка громкости вывода и микрофона
- Кэширование сгенерированных аудиофайлов
- Сохранение истории фраз с быстрым доступом через горячие клавиши
- Кастомная полоса заголовка с кнопками управления
- Возможность скрывать/показывать окно с помощью горячей клавиши

## Требования

- Python 3.7 или выше
- Установленные зависимости (будут установлены автоматически при запуске)
- Для функции передачи звука в микрофон: Virtual Audio Cable или аналогичное ПО

## Запуск

Для запуска приложения с автоматической установкой зависимостей:

```
python run_tts_overlay.py
```
ИЛИ
Запуск через ехе

## Горячие клавиши

- **Alt+T** - скрыть/показать окно приложения
- **Ctrl+0..9** - воспроизвести сохраненную фразу из истории (Ctrl+1 для последней фразы)

## Настройки

Настройки приложения сохраняются в файле `settings.json` и включают:

- Выбранное устройство вывода
- Выбранный виртуальный микрофон
- Громкость вывода и микрофона
- Выбранный движок TTS (Google или локальный)
- Выбранный голос

## Устранение неполадок

### Проблемы с виртуальным микрофоном

Для работы функции передачи звука в микрофон необходимо:

1. Установить Virtual Audio Cable или аналогичное ПО
2. Выбрать виртуальный микрофон в настройках приложения
3. В настройках игры или приложения выбрать виртуальный микрофон как устройство ввода

### Ошибки при установке PyAudio

Если возникают проблемы с установкой PyAudio, попробуйте:

1. Установить предварительно скомпилированную версию:
   ```
   pip install pipwin
   pipwin install pyaudio
   ```

2. Или установить необходимые зависимости:
   - Windows: установите [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Linux: `sudo apt-get install python3-dev portaudio19-dev` 
