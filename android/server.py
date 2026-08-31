# -*- coding: utf-8 -*-
from __future__ import annotations

#!/usr/bin/env python3
"""Лёгкий веб-интерфейс PolGen для Android (Termux).

Работает на чистой стандартной библиотеке Python — без gradio, fastapi и
других зависимостей с бинарными расширениями, которые не собираются на
Android. Интерфейс открывается в браузере телефона по адресу
http://127.0.0.1:4000

Запуск:  python android/server.py  (или ./android/run.sh)
"""

import asyncio
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

# Каталоги. При запуске из репозитория (ПК/Termux) данные лежат в корне
# репозитория; в автономном APK (Chaquopy) код хранится внутри APK, а данные —
# в каталоге приложения, который передаётся через POLGEN_DATA_DIR.
HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("POLGEN_DATA_DIR"):
    ROOT = os.environ["POLGEN_DATA_DIR"]
    sys.path.insert(0, HERE)
    STATIC_DIR = os.path.join(HERE, "static")
else:
    ROOT = os.path.dirname(HERE)
    sys.path.insert(0, ROOT)
    STATIC_DIR = os.path.join(ROOT, "android", "static")
os.makedirs(ROOT, exist_ok=True)
os.chdir(ROOT)

HOST = os.environ.get("POLGEN_HOST", "127.0.0.1")
PORT = int(os.environ.get("POLGEN_PORT", "4000"))
UPLOAD_DIR = os.path.join(ROOT, "output", "uploads")
OUTPUT_DIR = os.path.join(ROOT, "output", "RVC_output")
MODELS_DIR = os.path.join(ROOT, "models", "RVC_models")
MUSIC_DIR = os.environ.get("POLGEN_MUSIC_DIR", os.path.join(os.path.expanduser("~"), "storage", "music", "PolGen"))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Резервный список голосов, если сеть недоступна при старте
FALLBACK_VOICES = [
    {"ShortName": "ru-RU-DmitryNeural", "Gender": "Male", "Locale": "ru-RU"},
    {"ShortName": "ru-RU-SvetlanaNeural", "Gender": "Female", "Locale": "ru-RU"},
    {"ShortName": "ru-RU-DariyaNeural", "Gender": "Female", "Locale": "ru-RU"},
    {"ShortName": "ru-RU-PavelNeural", "Gender": "Male", "Locale": "ru-RU"},
    {"ShortName": "en-US-GuyNeural", "Gender": "Male", "Locale": "en-US"},
    {"ShortName": "en-US-JennyNeural", "Gender": "Female", "Locale": "en-US"},
    {"ShortName": "en-US-AriaNeural", "Gender": "Female", "Locale": "en-US"},
]

_VOICES_CACHE = {"voices": None, "loading": True}


def _load_voices():
    """Подгружает список голосов Edge-TTS в фоне."""
    try:
        import edge_tts

        voices = asyncio.run(edge_tts.list_voices())
        # Русские голоса — в начало списка
        voices.sort(key=lambda v: (not v.get("Locale", "").startswith("ru"), v.get("Locale", ""), v.get("ShortName", "")))
        _VOICES_CACHE["voices"] = [
            {"ShortName": v.get("ShortName"), "Gender": v.get("Gender"), "Locale": v.get("Locale")} for v in voices
        ]
    except Exception as error:  # noqa: BLE001
        print(f"[i] Не удалось получить список голосов Edge-TTS ({error}); используется резервный список")
        _VOICES_CACHE["voices"] = FALLBACK_VOICES
    finally:
        _VOICES_CACHE["loading"] = False


# ─── Ядро RVC (импортируется после смены рабочего каталога) ────────────
print("[PolGen] Инициализация ядра RVC...")
from rvc.infer import infer as core  # noqa: E402
from rvc.lib.predictors.f0 import available_f0_methods  # noqa: E402

try:
    import torch
except ImportError:
    torch = None


# ─── Менеджер фоновых задач ────────────────────────────────────────────
class Job:
    def __init__(self, kind: str, label: str):
        self.id = uuid.uuid4().hex[:12]
        self.kind = kind
        self.label = label
        self.state = "queued"  # queued | running | done | error
        self.progress = 0.0
        self.message = "В очереди..."
        self.result = None
        self.error = None
        self.created = time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "state": self.state,
            "progress": round(self.progress, 3),
            "message": self.message,
            "result": self.result,
            "error": self.error,
        }


class JobManager:
    """Одна фоновая очередь: на телефоне конвертации должны идти по очереди."""

    def __init__(self, workers: int = 1):
        self._jobs: dict[str, Job] = {}
        self._queue: "queue.Queue[Job]" = queue.Queue()
        self._lock = threading.Lock()
        for _ in range(workers):
            threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, kind: str, label: str, fn) -> Job:
        job = Job(kind, label)
        job.fn = fn
        with self._lock:
            self._jobs[job.id] = job
        self._queue.put(job)
        return job

    def get(self, job_id: str):
        with self._lock:
            return self._jobs.get(job_id)

    def _worker(self):
        while True:
            job = self._queue.get()
            if job is None:
                return
            job.state = "running"
            job.message = "Запуск..."
            try:
                job.result = job.fn(job)
                job.state = "done"
                job.progress = 1.0
                job.message = "Готово"
            except Exception as error:  # noqa: BLE001
                job.state = "error"
                job.error = str(error)
                job.message = f"Ошибка: {error}"
                import traceback

                traceback.print_exc()
            # Чистим старые задачи (последние 30)
            with self._lock:
                if len(self._jobs) > 30:
                    for key in list(self._jobs)[:-30]:
                        self._jobs.pop(key, None)


JOBS = JobManager()


def _progress_adapter(job: Job):
    def cb(fraction: float, message: str):
        job.progress = max(0.0, min(1.0, fraction))
        if message:
            job.message = message
    return cb


# ─── Действия задач ────────────────────────────────────────────────────


def action_convert(params: dict, upload_path: str):
    def run(job: Job):
        return core.rvc_infer(
            rvc_model=params.get("rvc_model"),
            input_path=upload_path,
            f0_method=params.get("f0_method", "rmvpe"),
            f0_min=int(params.get("f0_min", 50)),
            f0_max=int(params.get("f0_max", 1100)),
            rvc_pitch=float(params.get("rvc_pitch", 0)),
            protect=float(params.get("protect", 0.5)),
            index_rate=float(params.get("index_rate", 0.25)),
            volume_envelope=float(params.get("volume_envelope", 1.0)),
            autopitch=bool(params.get("autopitch", False)),
            autopitch_threshold=float(params.get("autopitch_threshold", 155.0)),
            autotune=bool(params.get("autotune", False)),
            autotune_tonic=params.get("autotune_tonic", "C"),
            autotune_scale=params.get("autotune_scale", "chromatic"),
            autotune_strength=float(params.get("autotune_strength", 1.0)),
            stereo_sound=bool(params.get("stereo_sound", False)),
            output_format=params.get("output_format", "wav"),
            progress_callback=_progress_adapter(job),
        )

    return run


def action_tts(params: dict):
    def run(job: Job):
        job.message = "Синтез речи..."
        return core.rvc_edgetts_infer(
            rvc_model=params.get("rvc_model"),
            f0_method=params.get("f0_method", "rmvpe"),
            rvc_pitch=float(params.get("rvc_pitch", 0)),
            protect=float(params.get("protect", 0.5)),
            index_rate=float(params.get("index_rate", 0.25)),
            volume_envelope=float(params.get("volume_envelope", 1.0)),
            autopitch=bool(params.get("autopitch", False)),
            autotune=bool(params.get("autotune", False)),
            stereo_sound=bool(params.get("stereo_sound", False)),
            output_format=params.get("output_format", "wav"),
            tts_voice=params.get("tts_voice"),
            tts_text=params.get("tts_text", ""),
            tts_rate=int(params.get("tts_rate", 0)),
            tts_volume=int(params.get("tts_volume", 0)),
            tts_pitch=int(params.get("tts_pitch", 0)),
            progress_callback=_progress_adapter(job),
        )

    return run


def action_install_url(url: str, name: str):
    def run(job: Job):
        from rvc.modules.model_manager import download_from_url

        job.message = f"Загрузка модели {name}..."
        download_from_url(url, name, progress=_progress_adapter(job))
        return {"installed": name}

    return run


def action_install_file(upload_path: str, name: str):
    def run(job: Job):
        from rvc.modules.model_manager import extract_zip

        model_dir = os.path.join(MODELS_DIR, name)
        if os.path.exists(model_dir):
            raise ValueError(f"Модель с именем «{name}» уже существует")
        os.makedirs(model_dir, exist_ok=True)

        if upload_path.endswith(".zip"):
            job.message = "Распаковка архива..."
            extract_zip(model_dir, upload_path)
        elif upload_path.endswith(".pth"):
            shutil.move(upload_path, os.path.join(model_dir, os.path.basename(upload_path)))
        elif upload_path.endswith(".index"):
            shutil.move(upload_path, os.path.join(model_dir, os.path.basename(upload_path)))
        else:
            raise ValueError("Ожидался файл .zip, .pth или .index")
        return {"installed": name}

    return run


# ─── Вспомогательное ───────────────────────────────────────────────────


def list_models() -> list:
    result = []
    for name in core.list_rvc_models():
        try:
            info = core.model_info(name)
            info["index"] = info.pop("has_index")
            result.append(info)
        except Exception:  # noqa: BLE001 - сломанная модель не должна ломать список
            result.append({"name": name, "has_index": False, "index": False, "size_mb": 0, "broken": True})
    return result


def list_outputs() -> list:
    if not os.path.isdir(OUTPUT_DIR):
        return []
    files = []
    for name in os.listdir(OUTPUT_DIR):
        path = os.path.join(OUTPUT_DIR, name)
        if os.path.isfile(path) and not name.startswith("."):
            files.append({"name": name, "size_mb": round(os.path.getsize(path) / 1024**2, 1), "mtime": os.path.getmtime(path)})
    return sorted(files, key=lambda f: f["mtime"], reverse=True)


def system_info() -> dict:
    info = {
        "version": None,
        "device": core.config.device,
        "threads": getattr(core.config, "torch_threads", None),
        "ram_gb": round(getattr(core.config, "total_ram_gb", 0), 1),
        "is_android": getattr(core.config, "is_android", False),
        "torch": torch.__version__ if torch else None,
        "python": sys.version.split()[0],
        "cache": core.CACHE.stats(),
        "chunk_sec": core.config.x_center,
    }
    try:
        from assets.version import __version__

        info["version"] = __version__
    except Exception:  # noqa: BLE001
        pass
    return info


def set_wakelock(on: bool) -> dict:
    """Держит CPU активным во время конвертаций (Termux API)."""
    cmd = "termux-wake-lock" if on else "termux-wake-unlock"
    try:
        subprocess.run([cmd], check=True, timeout=10, capture_output=True)
        return {"wakelock": on, "ok": True}
    except Exception as error:  # noqa: BLE001
        return {"wakelock": None, "ok": False, "error": f"{cmd}: {error}"}


# ─── Парсер multipart/form-data (потоковый, без загрузки файла в RAM) ──


class MultipartParser:
    """Разбирает тело multipart/form-data, сохраняя файлы на диск."""

    def __init__(self, stream, content_length: int, boundary: bytes, max_file_mb: int = 2048):
        self.stream = stream
        self.remaining = content_length
        self.boundary = b"--" + boundary
        self.max_file_bytes = max_file_mb * 1024**2
        self.fields: dict[str, str] = {}
        self.files: list[dict] = []

    def _read(self, n: int) -> bytes:
        if self.remaining <= 0:
            return b""
        chunk = self.stream.read(min(n, self.remaining))
        self.remaining -= len(chunk)
        return chunk

    def _read_until_delimiter(self, buf: bytes):
        """Генератор содержимого части до разделителя. Возвращает (chunk, buf, done)."""
        while True:
            idx = buf.find(self.delimiter)
            if idx >= 0:
                yield buf[:idx], buf[idx + len(self.delimiter):], True
                return
            if self.remaining <= 0:
                # Тела больше нет — отдаём остаток целиком
                yield buf, b"", True
                return
            keep = len(self.delimiter) - 1
            yield buf[:-keep], buf[-keep:], False
            buf = buf[-keep:] + self._read(262144)

    def parse(self):
        self.delimiter = b"\r\n" + self.boundary
        # Читаем до первой границы
        buf = b""
        while self.boundary not in buf:
            data = self._read(65536)
            if not data:
                raise ValueError("Некорректный multipart: граница не найдена")
            buf += data
            buf = buf[buf.find(self.boundary):] if self.boundary in buf else buf[-(len(self.boundary) + 4):]
        buf = buf[buf.find(self.boundary) + len(self.boundary):]

        while True:
            # Конец тела?
            if buf.startswith(b"--"):
                return
            # Перевод строки после границы
            if buf.startswith(b"\r\n"):
                buf = buf[2:]
            # Заголовки части
            while b"\r\n\r\n" not in buf:
                data = self._read(65536)
                if not data:
                    return
                buf += data
            header_end = buf.find(b"\r\n\r\n") + 4
            headers = buf[:header_end].decode("utf-8", errors="replace")
            buf = buf[header_end:]

            name = None
            filename = None
            for line in headers.split("\r\n"):
                match = re.search(r'name="([^"]*)"', line)
                if match and "content-disposition" in line.lower():
                    name = match.group(1)
                    match_fn = re.search(r'filename="([^"]*)"', line)
                    if match_fn:
                        filename = match_fn.group(1)
            if name is None:
                continue

            if filename is not None:
                safe_name = re.sub(r"[^\w.\-()\[\] ]", "_", os.path.basename(filename)) or "upload.bin"
                dest = os.path.join(UPLOAD_DIR, f"{int(time.time() * 1000)}_{safe_name}")
                written = 0
                with open(dest, "wb") as out:
                    for chunk, buf, done in self._read_until_delimiter(buf):
                        if chunk:
                            out.write(chunk)
                            written += len(chunk)
                        if done:
                            break
                if written > self.max_file_bytes:
                    os.remove(dest)
                    raise ValueError("Файл слишком большой")
                self.files.append({"field": name, "path": dest, "filename": safe_name, "size": written})
            else:
                value = b""
                for chunk, buf, done in self._read_until_delimiter(buf):
                    value += chunk
                    if done:
                        break
                self.fields[name] = value.decode("utf-8", errors="replace")


# ─── HTTP-обработчик ───────────────────────────────────────────────────


class PolGenHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PolGenAndroid/1.0"

    # ── GET ──
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/index.html"):
            return self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
        if path == "/api/state":
            return self._json(
                {
                    "models": list_models(),
                    "voices": _VOICES_CACHE["voices"],
                    "voices_loading": _VOICES_CACHE["loading"],
                    "f0_methods": available_f0_methods(),
                    "system": system_info(),
                    "outputs": list_outputs(),
                    "storage_music_available": os.path.isdir(os.path.dirname(MUSIC_DIR)),
                }
            )
        if path == "/api/job":
            params = parse_qs(parsed.query)
            job = JOBS.get(params.get("id", [""])[0])
            if job is None:
                return self._json({"error": "Задача не найдена"}, 404)
            return self._json(job.to_dict())
        if path == "/api/outputs":
            return self._json({"outputs": list_outputs()})
        if path.startswith("/output/"):
            name = os.path.basename(path[len("/output/"):])
            file_path = os.path.join(OUTPUT_DIR, name)
            if not os.path.isfile(file_path):
                return self._json({"error": "Файл не найден"}, 404)
            return self._serve_file(file_path, download_name=name)

        return self._json({"error": "Не найдено"}, 404)

    # ── POST ──
    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        try:
            if path == "/api/convert":
                fields, files = self._parse_body()
                if not files:
                    return self._json({"error": "Файл аудио не получен"}, 400)
                params = json.loads(fields.get("params", "{}"))
                upload = files[0]["path"]
                # Возвращаем файлу исходное имя (для красивого имени результата)
                final_path = os.path.join(UPLOAD_DIR, files[0]["filename"])
                if final_path != upload:
                    shutil.move(upload, final_path)
                job = JOBS.submit("convert", f"Конвертация: {files[0]['filename']}", action_convert(params, final_path))
                return self._json({"job_id": job.id})

            if path == "/api/tts":
                params = self._read_json()
                job = JOBS.submit("tts", "TTS + конвертация", action_tts(params))
                return self._json({"job_id": job.id})

            if path == "/api/install_url":
                params = self._read_json()
                url = (params.get("url") or "").strip()
                name = (params.get("name") or "").strip()
                if not url or not name:
                    return self._json({"error": "Укажите ссылку и имя модели"}, 400)
                job = JOBS.submit("install", f"Установка {name}", action_install_url(url, name))
                return self._json({"job_id": job.id})

            if path == "/api/install_file":
                fields, files = self._parse_body()
                name = (fields.get("name") or "").strip()
                if not files or not name:
                    return self._json({"error": "Файл и имя модели обязательны"}, 400)
                job = JOBS.submit("install", f"Установка {name}", action_install_file(files[0]["path"], name))
                return self._json({"job_id": job.id})

            if path == "/api/cache_clear":
                core.clear_model_cache()
                return self._json({"ok": True, "cache": core.CACHE.stats()})

            if path == "/api/wakelock":
                params = self._read_json()
                return self._json(set_wakelock(bool(params.get("on"))))

            if path == "/api/delete_output":
                params = self._read_json()
                name = os.path.basename(params.get("name", ""))
                target = os.path.join(OUTPUT_DIR, name)
                if os.path.isfile(target):
                    os.remove(target)
                    return self._json({"ok": True})
                return self._json({"error": "Файл не найден"}, 404)

            if path == "/api/share":
                params = self._read_json()
                name = os.path.basename(params.get("name", ""))
                src = os.path.join(OUTPUT_DIR, name)
                if not os.path.isfile(src):
                    return self._json({"error": "Файл не найден"}, 404)
                os.makedirs(MUSIC_DIR, exist_ok=True)
                shutil.copyfile(src, os.path.join(MUSIC_DIR, name))
                return self._json({"ok": True, "path": os.path.join(MUSIC_DIR, name)})

            if path == "/api/delete_model":
                params = self._read_json()
                name = os.path.basename(params.get("name", ""))
                target = os.path.join(MODELS_DIR, name)
                if os.path.isdir(target):
                    shutil.rmtree(target)
                    core.CACHE.clear()
                    return self._json({"ok": True})
                return self._json({"error": "Модель не найдена"}, 404)

            return self._json({"error": "Не найдено"}, 404)
        except Exception as error:  # noqa: BLE001
            import traceback

            traceback.print_exc()
            return self._json({"error": str(error)}, 500)

    # ── Утилиты ──
    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _parse_body(self):
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        if "multipart/form-data" in content_type:
            match = re.search(r'boundary="?([^";]+)"?', content_type)
            if not match:
                raise ValueError("Не найдена граница multipart")
            parser = MultipartParser(self.rfile, length, match.group(1).encode())
            parser.parse()
            return parser.fields, parser.files
        # Обычная форма
        body = self.rfile.read(length).decode("utf-8")
        return {k: v[0] for k, v in parse_qs(body).items()}, []

    def _json(self, data, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_file(self, path: str, content_type: str = None, download_name: str = None):
        if not os.path.isfile(path):
            return self._json({"error": "Файл не найден"}, 404)
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(size))
        if download_name:
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{download_name}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(262144)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return

    def log_message(self, fmt, *args):
        print(f"[http] {self.address_string()} {fmt % args}")


def main():
    threading.Thread(target=_load_voices, daemon=True).start()

    server = ThreadingHTTPServer((HOST, PORT), PolGenHandler)
    server.daemon_threads = True
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║        PolGen для Android — запущен!         ║")
    print(f"║  Открой в браузере:  http://{HOST}:{PORT:<5}       ║")
    print("║  Остановка: Ctrl+C                           ║")
    print("╚══════════════════════════════════════════════╝")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[i] Остановка сервера...")


if __name__ == "__main__":
    main()
