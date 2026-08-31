# PolGen для Android — автономный APK (без Termux)

Приложение содержит **всё ядро внутри APK**: python (Chaquopy), PyTorch 1.8.1
(arm64), scipy, edge-tts и веб-интерфейс. Termux больше не нужен — после
установки достаточно запустить PolGen.

При **первом запуске** приложение само скачает модели (HuBERT + RMVPE,
~560 МБ с HuggingFace) в свой каталог и поднимет интерфейс на
`http://127.0.0.1:4000` прямо на экране.

## Сборка

CI собирает APK и выкладывает его как **артефакт** (без релизов и тегов):

1. скопируй [`ci/standalone-apk.yml`](../ci/standalone-apk.yml) в
   `.github/workflows/` (см. комментарий в файле);
2. Actions → «PolGen standalone APK» → **Run workflow** → выбери ветку;
3. после сборки: страница запуска → **Artifacts** → `PolGen-standalone-apk`.

Локальная сборка (нужны JDK 17, Android SDK 34, Gradle 8.9, любой python3):

```bash
bash android/app/stage_python.sh          # вложить код PolGen в APK
cd android/app && gradle :app:assembleRelease
python android/sign.py app/build/outputs/apk/release/app-release-unsigned.apk \
       PolGen-standalone.apk android/polgen-launcher-key.pem
```

## Как это устроено

```
android/
├── app/                      Gradle-проект (Chaquopy: python внутри APK)
│   ├── app/build.gradle      версии, pip-зависимости (torch==1.8.1, scipy…)
│   ├── app/src/main/java/    MainActivity: WebView + ожидание сервера
│   ├── app/src/main/python/bootstrap.py   запуск ядра и сервера
│   └── stage_python.sh       копирует rvc/ + server.py в APK перед сборкой
├── server.py                 веб-интерфейс (чистая стандартная библиотека)
├── static/                   статика интерфейса
├── sign.py                   подпись APK v1+v2 (python + cryptography)
└── polgen-launcher-key.pem   ключ подписи (тот же, что у старых версий)
```

Внутри APK (после `stage_python.sh`):

- `polgen/rvc/…` — ядро конвертации голоса;
- `polgen/server.py` — сервер интерфейса (`127.0.0.1:4000`);
- `polgen/static/` — вёрстка интерфейса;
- `polgen/model_installer.py` — загрузка моделей при первом запуске.

Поток данных: `MainActivity` стартует python-поток → `bootstrap.main()` →
докачка моделей → `server.main()` → порт 4000 открыт → WebView показывает
интерфейс. Прогресс начальной загрузки виден на экране запуска.

## Совместимость (важно)

- **Python 3.8** — единственная версия, для которой существует сборка PyTorch
  для Android (`chaquo.com/pypi-13.1`, torch 1.8.1). Код ядра адаптирован:
  `rvc/lib/torch_compat.py` выбирает старый/новый `weight_norm`;
- **torch 1.8.1**: `parametrizations.weight_norm` заменён через шим;
- **без ffmpeg**: аудио декодируется системными кодеками Android
  (`MediaCodec` из python через мост Chaquopy), результат пишется WAV
  стандартной библиотекой (`rvc/lib/my_utils.py`);
- scipy 1.4.1: `medfilt` при недоступности scipy заменяется numpy-версией.

## Ограничения

- только **arm64-v8a** (64-битные устройства; PyTorch для Android другого
  нет);
- выходной формат — WAV (mp3/flac недоступны без ffmpeg);
- фоновая конвертация при свёрнутом приложении может быть приостановлена
  системой;
- размер APK ~120 МБ + ~560 МБ моделей при первом запуске.
