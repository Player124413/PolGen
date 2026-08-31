"""Генератор синтетических моделей для локального тестирования и бенчмарков PolGen.

Создаёт модели с РЕАЛЬНЫМИ архитектурами (те же размеры слоёв и вычислительная
стоимость), но со случайными весами. Это позволяет:
  * тестировать полный конвейер RVC без скачивания 600+ МБ весей;
  * запускать воспроизводимые бенчмарки производительности;
  * проверять бит-в-бит совместимость между версиями кода.

Использование:
    python tests/generate_test_models.py [--out .] [--seed 42]

ВНИМАНИЕ: выходное аудио будет шумом — веса случайные. Инструмент предназначен
только для тестирования производительности и корректности кода.
"""

import argparse
import inspect
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch  # noqa: E402

from rvc.lib.algorithm.synthesizers import Synthesizer  # noqa: E402
from rvc.lib.fairseq import HubertConfig, HubertModel  # noqa: E402
from rvc.lib.predictors.RMVPE import E2E  # noqa: E402


def build_hubert_checkpoint(seed: int) -> dict:
    """Контрольная точка HuBERT base (12 слоёв, 768 dim) в формате fairseq."""
    torch.manual_seed(seed)

    params = inspect.signature(HubertConfig.__init__).parameters
    cfg = {name: p.default for name, p in params.items() if name != "self"}
    # Значения по умолчанию HubertConfig уже соответствуют hubert_base:
    # 12 слоёв, 768 dim, 3072 FFN, 12 голов, extractor_mode="default".
    cfg = {k: v for k, v in cfg.items() if v is not inspect.Parameter.empty}

    model = HubertModel(HubertConfig(**cfg), num_classes=504)
    return {"cfg": {"model": cfg}, "model": model.state_dict()}


def build_rmvpe_checkpoint(seed: int) -> dict:
    """Контрольная точка RMVPE (E2E 4,1,(2,2)) — только state_dict."""
    torch.manual_seed(seed)
    model = E2E(4, 1, (2, 2))
    return model.state_dict()


def build_rvc_v2_checkpoint(seed: int) -> dict:
    """Контрольная точка RVC v2 (40k) в формате PolGen/RVC."""
    torch.manual_seed(seed)

    config = [
        1025,  # spec_channels
        120,  # segment_size
        192,  # inter_channels
        192,  # hidden_channels
        768,  # filter_channels
        2,  # n_heads
        6,  # n_layers
        3,  # kernel_size
        0,  # p_dropout
        "1",  # resblock
        [3, 7, 11],  # resblock_kernel_sizes
        [[1, 3, 5], [1, 3, 5], [1, 3, 5]],  # resblock_dilation_sizes
        [10, 10, 2, 2],  # upsample_rates (произведение 400 = 40000 Гц / 100 fps)
        512,  # upsample_initial_channel
        [16, 16, 4, 4],  # upsample_kernel_sizes
        109,  # spk_embed_dim (перезаписывается на n_spk при загрузке)
        256,  # gin_channels
        40000,  # sampling rate
    ]

    net_g = Synthesizer(*config, use_f0=1, text_enc_hidden_dim=768, vocoder="HiFi-GAN")

    return {
        "config": config,
        "weight": net_g.state_dict(),
        "f0": 1,
        "version": "v2",
        "sr": "40k",
        "info": "synthetic test model",
    }


def build_faiss_index(path: str, n: int, d: int, seed: int, ivf: bool = True):
    """Индекс FAISS, аналогичный создаваемому при обучении RVC."""
    import faiss

    rng = np.random.default_rng(seed)
    data = rng.standard_normal((n, d)).astype(np.float32)

    if ivf:
        index = faiss.index_factory(d, "IVF512,Flat")
        index.train(data)
        index.add(data)
    else:
        index = faiss.index_factory(d, "Flat", faiss.METRIC_INNER_PRODUCT)
        index.add(data)

    faiss.write_index(index, path)
    return index


def generate_speech_like_audio(path: str, seconds: float = 10.0, sr: int = 16000, seed: int = 7):
    """Похожая на речь запись: гармонические «гласные» с вибрато + паузы + шум."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(sr * seconds)) / sr
    audio = np.zeros_like(t)

    # «Слоги»: участки с фундаментальной частотой 100-200 Гц и вибрато
    pos = 0.0
    while pos < seconds:
        dur = rng.uniform(0.2, 0.45)
        f0 = rng.uniform(100, 200)
        start, end = int(pos * sr), min(int((pos + dur) * sr), len(t))
        seg = t[start:end] - t[start]
        vibrato = 1 + 0.02 * np.sin(2 * np.pi * 5.5 * seg)
        phase = 2 * np.pi * f0 * seg * vibrato
        tone = 0.5 * np.sin(phase) + 0.25 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase)
        env = np.minimum(1, np.minimum(seg / 0.03, (seg[-1] - seg) / 0.03 + 1)) if len(seg) > 10 else np.ones_like(seg)
        audio[start:end] += tone * env
        pos += dur + rng.uniform(0.05, 0.2)  # пауза между «слогами»

    audio += 0.005 * rng.standard_normal(len(audio))  # лёгкий шум
    audio = (audio / np.abs(audio).max() * 0.8).astype(np.float32)

    import soundfile as sf

    sf.write(path, audio, sr)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=".", help="Корневая директория PolGen")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--index-vectors", type=int, default=5000, help="Число векторов в индексе FAISS")
    parser.add_argument("--audio-seconds", type=float, default=10.0)
    args = parser.parse_args()

    root = os.path.abspath(args.out)
    embedders = os.path.join(root, "rvc", "models", "embedders")
    predictors = os.path.join(root, "rvc", "models", "predictors")
    rvc_models = os.path.join(root, "models", "RVC_models", "test_voice")
    os.makedirs(embedders, exist_ok=True)
    os.makedirs(predictors, exist_ok=True)
    os.makedirs(rvc_models, exist_ok=True)

    print("[1/5] Генерируем HuBERT base (12 слоёв, 768 dim)...")
    hubert = build_hubert_checkpoint(args.seed)
    torch.save(hubert, os.path.join(embedders, "hubert_base.pt"))

    print("[2/5] Генерируем RMVPE...")
    torch.save(build_rmvpe_checkpoint(args.seed + 1), os.path.join(predictors, "rmvpe.pt"))

    print("[3/5] Генерируем RVC v2 модель (40k)...")
    torch.save(build_rvc_v2_checkpoint(args.seed + 2), os.path.join(rvc_models, "test_voice.pth"))

    print("[4/5] Генерируем FAISS индексы (IVF512 и FlatIP)...")
    build_faiss_index(os.path.join(rvc_models, "test_voice.index"), args.index_vectors, 768, args.seed + 3, ivf=True)
    build_faiss_index(os.path.join(rvc_models, "test_voice_flat_ip.index"), args.index_vectors, 768, args.seed + 3, ivf=False)

    print("[5/5] Генерируем тестовое аудио...")
    generate_speech_like_audio(os.path.join(root, "test_audio.wav"), args.audio_seconds)

    total = 0
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith((".pt", ".pth", ".index", ".wav")) and ("test" in f or "hubert" in f or "rmvpe" in f):
                total += os.path.getsize(os.path.join(dirpath, f))
    print(f"\nГотово! Синтетические модели ({total / 1024**2:.0f} МБ) созданы в {root}")


if __name__ == "__main__":
    main()
