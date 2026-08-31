#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════════════════════════════════
#  PolGen для Android — запуск веб-интерфейса
#  Открывает http://127.0.0.1:4000 в браузере телефона.
# ══════════════════════════════════════════════════════════════════════
cd "$(dirname "$0")/.."

# Wake lock: CPU не заснёт во время конвертации
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock 2>/dev/null

echo "Запускаем PolGen для Android..."
echo "Интерфейс: http://127.0.0.1:4000  (откроется автоматически)"
echo "Остановка: Ctrl+C"
echo

# Запускаем сервер в фоне и ждём готовности порта
python android/server.py &
SERVER_PID=$!

PORT="${POLGEN_PORT:-4000}"
for i in $(seq 1 60); do
    if echo >/dev/tcp/127.0.0.1/$PORT 2>/dev/null; then
        break
    fi
    sleep 1
done

# Открываем браузер
if command -v termux-open-url >/dev/null 2>&1; then
    termux-open-url "http://127.0.0.1:$PORT" 2>/dev/null
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:$PORT" 2>/dev/null
fi

# Ждём завершения сервера (Ctrl+C останавливает)
trap 'kill $SERVER_PID 2>/dev/null; command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock 2>/dev/null; exit 0' INT TERM
wait $SERVER_PID
