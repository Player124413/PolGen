from pathlib import Path

import requests
from tqdm import tqdm

# Константы - конфигурация моделей
MODELS_CONFIG = {
    "predictors": {
        "url": "https://huggingface.co/Politrees/RVC_resources/resolve/main/predictors/",
        "dir": Path("rvc/models/predictors"),
        "files": ["rmvpe.pt"]
    },
    "embedders": {
        "url": "https://huggingface.co/Politrees/RVC_resources/resolve/main/embedders/pytorch/",
        "dir": Path("rvc/models/embedders"),
        "files": ["hubert_base.pt"]
    },
    "flash_sr": {
        "url": "https://huggingface.co/datasets/jakeoneijk/FlashSR_weights/resolve/main/",
        "dir": Path("rvc/models/FlashSR"),
        "files": ["sr_vocoder.pth", "student_ldm.pth", "vae.pth"]
    }
}


def download_model(url, file_name, save_dir):
    file_path = save_dir / file_name
    if file_path.exists():
        return  # Пропускаем загрузку, если файл уже существует

    try:
        with requests.get(f"{url}{file_name}", stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            with open(file_path, "wb") as f, tqdm(desc=file_name, total=total_size, unit="iB", unit_scale=True, unit_divisor=1024) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))

    except requests.exceptions.RequestException as e:
        print(f"Ошибка загрузки {file_name}: {e}")
        file_path.unlink(missing_ok=True)  # Удаляем частично загруженный файл
        raise


def check_and_install_models():
    for _, config in MODELS_CONFIG.items():
        config["dir"].mkdir(parents=True, exist_ok=True)  # Создаём директорию
        for file_name in config["files"]:
            try:
                download_model(config["url"], file_name, config["dir"])
            except Exception as e:
                print(f"Не удалось загрузить {file_name}: {e}")


if __name__ == "__main__":
    check_and_install_models()
