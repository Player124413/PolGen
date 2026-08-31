#!/usr/bin/env bash
# Сборка APK-лаунчера PolGen.
#
# Зависимости:
#   - JRE 8+ (java)          — для apktool
#   - python3 + cryptography — для подписи (pip install cryptography)
#   - npm (опционально)      — чтобы получить apktool.jar (npm pack apktool-jar)
#     либо скачайте apktool.jar с https://apktool.org
#
# Использование:  bash build.sh
set -euo pipefail
cd "$(dirname "$0")"

APKTOOL_JAR="${APKTOOL_JAR:-apktool.jar}"
if [ ! -f "$APKTOOL_JAR" ]; then
    echo "apktool.jar не найден. Пробую получить через npm..."
    npm pack apktool-jar@2.4.1
    tar xzf apktool-jar-2.4.1.tgz
    mv package/bin/apktool_2.4.1.jar "$APKTOOL_JAR"
    rm -rf package apktool-jar-2.4.1.tgz
fi

echo "[1/2] Сборка через apktool..."
java -jar "$APKTOOL_JAR" b . -o ../PolGen-launcher-unsigned.apk

echo "[2/2] Подпись (v1, SHA-256)..."
python3 sign.py ../PolGen-launcher-unsigned.apk ../PolGen-launcher.apk polgen-launcher-key.pem

rm -f ../PolGen-launcher-unsigned.apk
echo
echo "Готово: ../PolGen-launcher.apk"
echo "Установка: adb install PolGen-launcher.apk  (или просто открыть файл на телефоне)"
