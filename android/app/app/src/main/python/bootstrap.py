# -*- coding: utf-8 -*-
"""Автономный запуск PolGen внутри APK (Chaquopy).

Вызывается из MainActivity:

    bootstrap.main(data_dir, activity)

где data_dir — каталог приложения (filesDir), activity — Java-объект,
у которого питон вызывает onStatus(str) для отображения прогресса.

Соседний каталог polgen/ содержит код из репозитория (rvc, server.py,
static, model_installer) — он распакован из APK и доступен только для
чтения. Все данные (модели, загрузки, результат) живут в data_dir.
"""

import os
import sys
import traceback


def _log(listener, message):
    try:
        if listener is not None:
            listener.onStatus(message)
    except Exception:  # noqa: BLE001 — не роняем запуск из-за UI
        pass
    print("[PolGen] " + message, flush=True)


def main(data_dir, listener=None):
    here = os.path.dirname(os.path.abspath(__file__))
    pkg = os.path.join(here, "polgen")
    sys.path.insert(0, pkg)

    os.environ["POLGEN_DATA_DIR"] = data_dir
    os.environ.setdefault("POLGEN_HOST", "127.0.0.1")
    os.environ.setdefault("POLGEN_PORT", "4000")
    os.environ["HOME"] = data_dir

    os.makedirs(os.path.join(data_dir, "output", "uploads"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "output", "RVC_output"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "models", "RVC_models"), exist_ok=True)
    os.chdir(data_dir)

    # 1. модели (первый запуск — загрузка ~560 МБ с HuggingFace)
    try:
        _log(listener, "Проверяю модели (первый запуск — загрузка ~560 МБ)…")
        import model_installer

        model_installer.check_and_install_models()
    except Exception as error:  # noqa: BLE001
        _log(listener, "Модели не загрузились: %s — сервер всё равно поднимется" % error)
        traceback.print_exc()

    # 2. ядро RVC + веб-сервер (блокируется до конца работы приложения)
    _log(listener, "Инициализация ядра RVC (PyTorch)…")
    import server

    _log(listener, "PolGen готов — открываю интерфейс")
    server.main()
