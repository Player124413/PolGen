"""
Автоматическая калибровка RVC моделей.

Определяет характеристики голоса модели (F0) для точного AutoPitch.
"""

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from typing import Optional, Tuple
import numpy as np


@dataclass
class ModelVoiceInfo:
    """Характеристики голоса модели."""
    
    f0_center: float  # Центральная частота голоса модели (Hz)
    f0_min: float  # Минимальная частота
    f0_max: float  # Максимальная частота
    voice_type: str  # Тип голоса (bass, baritone, tenor, alto, soprano)
    calibrated: bool = True  # Была ли проведена калибровка
    
    def save(self, path: str):
        """Сохраняет в JSON файл."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: str) -> "ModelVoiceInfo":
        """Загружает из JSON файла."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def default(cls) -> "ModelVoiceInfo":
        """Возвращает значения по умолчанию (баритон)."""
        return cls(
            f0_center=145.0,
            f0_min=100.0,
            f0_max=200.0,
            voice_type="baritone",
            calibrated=False,
        )


def get_voice_info_path(model_dir: str) -> str:
    """Возвращает путь к файлу voice_info.json."""
    return os.path.join(model_dir, "voice_info.json")


def load_voice_info(model_dir: str) -> Optional[ModelVoiceInfo]:
    """Загружает информацию о голосе модели, если есть."""
    path = get_voice_info_path(model_dir)
    if os.path.exists(path):
        try:
            return ModelVoiceInfo.load(path)
        except Exception:
            return None
    return None


def determine_voice_type(f0_center: float) -> str:
    """Определяет тип голоса по центральной частоте."""
    if f0_center < 130:
        return "bass"
    elif f0_center < 165:
        return "baritone"
    elif f0_center < 200:
        return "tenor"
    elif f0_center < 280:
        return "alto"
    else:
        return "soprano"


def generate_test_audio(sample_rate: int = 16000, duration: float = 3.0) -> np.ndarray:
    """
    Генерирует тестовый аудиосигнал для калибровки.
    
    Используем chirp-сигнал (sweep) с гармониками, имитирующий голос.
    Покрывает диапазон 80-400 Hz.
    """
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Базовая частота: sweep от 120 до 250 Hz
    f0_start = 120.0
    f0_end = 250.0
    
    # Логарифмический sweep
    f0 = f0_start * (f0_end / f0_start) ** (t / duration)
    
    # Фаза (интеграл частоты)
    phase = 2 * np.pi * np.cumsum(f0) / sample_rate
    
    # Основной тон + гармоники (имитация голоса)
    signal = np.sin(phase)  # Основной тон
    signal += 0.5 * np.sin(2 * phase)  # 2-я гармоника
    signal += 0.25 * np.sin(3 * phase)  # 3-я гармоника
    signal += 0.125 * np.sin(4 * phase)  # 4-я гармоника
    
    # Нормализация
    signal = signal / np.max(np.abs(signal)) * 0.8
    
    return signal.astype(np.float32)


def analyze_model_output(
    audio: np.ndarray,
    sample_rate: int = 16000,
    device: str = "cuda",
) -> Tuple[float, float, float]:
    """
    Анализирует выходной сигнал модели и возвращает характеристики F0.
    
    Returns:
        (f0_center, f0_min, f0_max)
    """
    from rvc.lib.predictors.f0 import RMVPE
    
    # Извлекаем F0
    rmvpe = RMVPE(device=device, sample_rate=sample_rate)
    f0 = rmvpe.get_f0(audio, "rmvpe")
    
    # Фильтруем озвученные фреймы
    f0_voiced = f0[f0 > 0]
    
    if len(f0_voiced) < 10:
        # Недостаточно данных — возвращаем значения по умолчанию
        return 145.0, 100.0, 200.0
    
    # Удаляем выбросы
    q1 = np.percentile(f0_voiced, 25)
    q3 = np.percentile(f0_voiced, 75)
    iqr = q3 - q1
    f0_filtered = f0_voiced[(f0_voiced >= q1 - 1.5*iqr) & (f0_voiced <= q3 + 1.5*iqr)]
    
    if len(f0_filtered) < 10:
        f0_filtered = f0_voiced
    
    f0_center = float(np.median(f0_filtered))
    f0_min = float(np.percentile(f0_filtered, 10))
    f0_max = float(np.percentile(f0_filtered, 90))
    
    return f0_center, f0_min, f0_max


def calibrate_model(
    model_dir: str,
    rvc_model_path: str,
    index_path: Optional[str],
    device: str = "cuda",
    force: bool = False,
) -> ModelVoiceInfo:
    """
    Калибрует RVC модель — определяет характеристики её голоса.
    
    Args:
        model_dir: Папка с моделью
        rvc_model_path: Путь к .pth файлу
        index_path: Путь к .index файлу (опционально)
        device: Устройство для вычислений
        force: Принудительная перекалибровка
        
    Returns:
        ModelVoiceInfo с характеристиками голоса модели
    """
    import torch
    from rvc.infer.pipeline import VC
    from rvc.infer.config import Config
    from rvc.lib.algorithm.synthesizers import Synthesizer
    from rvc.lib.fairseq import load_model
    from rvc.lib.my_utils import load_audio
    
    voice_info_path = get_voice_info_path(model_dir)
    
    # Проверяем, есть ли уже калибровка
    if not force and os.path.exists(voice_info_path):
        try:
            info = ModelVoiceInfo.load(voice_info_path)
            if info.calibrated:
                return info
        except Exception:
            pass
    
    print(f"[⚙️] Калибровка модели...")
    
    # Загружаем модель
    config = Config()
    
    hubert_path = os.path.join(os.getcwd(), "rvc", "models", "embedders", "hubert_base.pt")
    hubert_model = load_model(hubert_path).to(device).eval()
    
    cpt = torch.load(rvc_model_path, map_location="cpu", weights_only=True)
    tgt_sr = cpt["config"][-1]
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
    
    use_f0 = cpt.get("f0", 1)
    version = cpt.get("version", "v1")
    vocoder = cpt.get("vocoder", "HiFi-GAN")
    input_dim = 768 if version == "v2" else 256
    
    net_g = Synthesizer(*cpt["config"], use_f0=use_f0, text_enc_hidden_dim=input_dim, vocoder=vocoder)
    del net_g.enc_q
    net_g.load_state_dict(cpt["weight"], strict=False)
    net_g = net_g.to(device).float().eval()
    
    vc = VC(tgt_sr, config)
    
    # Генерируем тестовый сигнал
    test_audio = generate_test_audio(sample_rate=16000, duration=3.0)
    
    # Прогоняем через модель
    try:
        output_audio = vc.pipeline(
            model=hubert_model,
            net_g=net_g,
            sid=0,
            audio=test_audio,
            pitch=0,  # Без сдвига!
            f0_min=50,
            f0_max=1100,
            f0_method="rmvpe",
            file_index=index_path,
            index_rate=0,
            pitch_guidance=use_f0,
            volume_envelope=1,
            version=version,
            protect=0.5,
            autopitch=False,
            autopitch_model_type="baritone",
            autotune=False,
            autotune_tonic="C",
            autotune_scale="chromatic",
            autotune_strength=0,
            autotune_retune_speed=0,
            autotune_flex_tune=0,
            autotune_preserve_vibrato=0,
            autotune_humanize=0,
        )
    except Exception as e:
        print(f"[!] Ошибка при калибровке: {e}")
        print("[!] Используем значения по умолчанию")
        info = ModelVoiceInfo.default()
        info.save(voice_info_path)
        return info
    
    # Ресемплируем к 16kHz для анализа (если нужно)
    if tgt_sr != 16000:
        import librosa
        output_audio = librosa.resample(output_audio, orig_sr=tgt_sr, target_sr=16000)
    
    # Анализируем выход
    f0_center, f0_min, f0_max = analyze_model_output(output_audio, sample_rate=16000, device=device)
    
    # Определяем тип голоса
    voice_type = determine_voice_type(f0_center)
    
    # Создаём и сохраняем информацию
    info = ModelVoiceInfo(
        f0_center=round(f0_center, 2),
        f0_min=round(f0_min, 2),
        f0_max=round(f0_max, 2),
        voice_type=voice_type,
        calibrated=True,
    )
    
    info.save(voice_info_path)
    
    print(f"[✓] Голос модели: {f0_center:.1f} Hz ({voice_type})")
    print(f"[✓] Сохранено в voice_info.json")
    
    # Освобождаем память
    del hubert_model, net_g, vc, cpt
    torch.cuda.empty_cache()
    
    return info
