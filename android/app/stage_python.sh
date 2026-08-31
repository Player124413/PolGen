#!/usr/bin/env bash
# Готовит python-исходники для сборки APK: копирует код PolGen из репозитория
# в src/main/python (chaquopy кладёт их внутрь APK).
# Запускается CI (или локально) перед `gradle assembleRelease`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"        # корень репозитория
APP="$ROOT/android/app/app/src/main/python"

rm -rf "$APP/polgen"
mkdir -p "$APP/polgen"

# код ядра и веб-интерфейса
cp -r "$ROOT/rvc"                          "$APP/polgen/rvc"
cp "$ROOT/android/server.py"               "$APP/polgen/server.py"
cp -r "$ROOT/android/static"               "$APP/polgen/static"
cp "$ROOT/assets/model_installer.py"       "$APP/polgen/model_installer.py"

# инструментарий python в рвк не нужен в APK
rm -rf "$APP/polgen/rvc/__pycache__"
find "$APP/polgen" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# большие модели внутрь APK не кладём — они загружаются при первом запуске
echo "polgen подготовлен:"
du -sh "$APP/polgen"
