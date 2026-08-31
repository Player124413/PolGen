#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════════════════════════════════
#  PolGen для Android — установщик (Termux)
#  Полный RVC-конвейер (замена голоса + TTS) прямо на телефоне.
#  Требуется 64-битное устройство (arm64-v8a / x86_64) и Android 8+.
# ══════════════════════════════════════════════════════════════════════
set -e

GREEN='\033[1;32m'; YELLOW='\033[1;33m'; RED='\033[1;31m'; CYAN='\033[1;36m'; NC='\033[0m'
step() { echo -e "${CYAN}════════════════════════════════════════${NC}"; echo -e "${CYAN} $1${NC}"; echo -e "${CYAN}════════════════════════════════════════${NC}"; }

# ─── Проверки окружения ───────────────────────────────────────────────
ARCH=$(uname -m)
case "$ARCH" in
    aarch64|arm64|x86_64) ;;
    *)
        echo -e "${RED}✖ Нужен 64-битный телефон (arm64-v8a), у вас: $ARCH${NC}"
        echo "К сожалению, PyTorch для Android существует только для 64-битных ARM."
        exit 1
        ;;
esac

if [ ! -d "/system" ]; then
    echo -e "${YELLOW}⚠ Похоже, это не Android/Termux (запуск вне Termux — продолжаем на свой страх и риск)${NC}"
fi

step "1/6 Обновление пакетов Termux"
pkg update -y && pkg upgrade -y

step "2/6 Установка базовых пакетов (python, ffmpeg, torch)"
pkg install -y python python-pip ffmpeg git clang make

# PyTorch для Android — из репозитория Termux (сборка aarch64)
if ! python -c "import torch" >/dev/null 2>&1; then
    echo -e "${GREEN}Устанавливаем PyTorch (python-torch, ~600 МБ)...${NC}"
    pkg install -y python-torch || pkg install -y python-torch-static || {
        echo -e "${YELLOW}⚠ Не удалось установить python-torch из репозитория.${NC}"
        echo "Попробуйте: pkg install python-torch-static"
        exit 1
    }
fi

# numpy и scipy — системные сборки Termux (pip-версии не собираются)
python -c "import numpy" >/dev/null 2>&1 || pkg install -y python-numpy
python -c "import scipy" >/dev/null 2>&1 || pkg install -y python-scipy

step "3/6 Установка Python-зависимостей (чистый Python с PyPI)"
pip install --upgrade edge-tts requests tqdm omegaconf gdown

# Опциональные методы F0 (чистый Python; при ошибке — RMVPE работает и без них)
pip install torchcrepe --no-deps 2>/dev/null && pip install matplotlib 2>/dev/null \
    || echo -e "${YELLOW}⚠ torchcrepe пропущен — метод CREPE будет недоступен (RMVPE работает)${NC}"
pip install torchfcpe --no-deps 2>/dev/null \
    || echo -e "${YELLOW}⚠ torchfcpe пропущен — метод FCPE будет недоступен (RMVPE работает)${NC}"

step "4/6 Termux:API (wake lock — экран не гаснет при конвертации)"
pkg install -y termux-api 2>/dev/null || echo -e "${YELLOW}⚠ termux-api пропущен (не критично)${NC}"

step "5/6 Загрузка базовых моделей (HuBERT + RMVPE, ~560 МБ)"
cd "$(dirname "$0")/.."
python assets/model_installer.py

step "6/6 Ярлык на рабочем столе (Termux:Widget)"
mkdir -p ~/.shortcuts
cp android/run.sh ~/.shortcuts/PolGen 2>/dev/null && chmod +x ~/.shortcuts/PolGen \
    && echo -e "${GREEN}Ярлык «PolGen» создан (виджет Termux:Widget → добавь на рабочий стол)${NC}" \
    || echo -e "${YELLOW}⚠ Ярлык не создан — запускай через ./android/run.sh${NC}"

echo
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        PolGen для Android установлен! 🌿     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo
echo "Запуск:      ./android/run.sh"
echo "Ярлык:       Termux:Widget → PolGen"
echo
echo -e "${YELLOW}Совет: выполни 'termux-setup-storage', чтобы сохранять результаты в общую папку Музыка.${NC}"
