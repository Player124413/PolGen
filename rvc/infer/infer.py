import asyncio
import gc
import os

import edge_tts
import gradio as gr
import numpy as np
import torch

from rvc.infer.config import Config
from rvc.infer.pipeline import VC
from rvc.lib.algorithm.synthesizers import Synthesizer
from rvc.lib.fairseq import load_model
from rvc.lib.my_utils import load_audio, save_audio
from rvc.modules.audio_upscaler import upscale

RVC_MODELS_DIR = os.path.join(os.getcwd(), "models", "RVC_models")
OUTPUT_DIR = os.path.join(os.getcwd(), "output", "RVC_output")
HUBERT_BASE_PATH = os.path.join(os.getcwd(), "rvc", "models", "embedders", "hubert_base.pt")

os.makedirs(RVC_MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

config = Config()


def display_progress(percent, message, is_print, progress=gr.Progress()):
    if is_print:
        print(message)
    progress(percent, desc=message)


def load_rvc_model(rvc_model):
    model_dir = os.path.join(RVC_MODELS_DIR, rvc_model)
    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"Папка модели {rvc_model} не найдена в {RVC_MODELS_DIR}")

    rvc_model_path = next((os.path.join(model_dir, f) for f in os.listdir(model_dir) if f.endswith(".pth")), None)
    rvc_index_path = next((os.path.join(model_dir, f) for f in os.listdir(model_dir) if f.endswith(".index")), None)

    if not rvc_model_path:
        raise FileNotFoundError(f"Модель {rvc_model} не содержит .pth файла!")

    return rvc_model_path, rvc_index_path


def load_hubert(model_path):
    hubert = load_model(model_path).to(config.device).eval()
    return hubert


def get_vc(model_path):
    cpt = torch.load(model_path, map_location="cpu", weights_only=True)
    if "config" not in cpt or "weight" not in cpt:
        raise ValueError(f"Некорректный формат модели {model_path}. Используйте модель RVC.")

    tgt_sr = cpt["config"][-1]
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]

    use_f0 = cpt.get("f0", 1)
    version = cpt.get("version", "v1")
    vocoder = cpt.get("vocoder", "HiFi-GAN")
    input_dim = 768 if version == "v2" else 256

    net_g = Synthesizer(*cpt["config"], use_f0=use_f0, text_enc_hidden_dim=input_dim, vocoder=vocoder)

    del net_g.enc_q
    net_g.load_state_dict(cpt["weight"], strict=False)
    net_g = net_g.to(config.device).float().eval()

    vc = VC(tgt_sr, config)
    return cpt, version, net_g, tgt_sr, vc, use_f0


async def text_to_speech(voice, text, rate, volume, pitch, output_path):
    if not -100 <= rate <= 100 or not -100 <= volume <= 100 or not -100 <= pitch <= 100:
        raise ValueError("Параметры Rate, Volume и Pitch должны быть в диапазоне от -100 до +100.")

    communicate = edge_tts.Communicate(voice=voice, text=text, rate=f"{rate:+d}%", volume=f"{volume:+d}%", pitch=f"{pitch:+d}Hz")
    await communicate.save(output_path)


def rvc_infer(
    rvc_model=None,
    input_path=None,
    f0_method="rmvpe",
    f0_min=50,
    f0_max=1100,
    rvc_pitch=0,
    protect=0.5,
    index_rate=0,
    volume_envelope=1,
    autopitch=False,
    autopitch_model_type="baritone",
    autotune=False,
    autotune_tonic="C",
    autotune_scale="chromatic",
    autotune_strength=1.0,
    autotune_retune_speed=0.0,
    autotune_flex_tune=0.0,
    autotune_preserve_vibrato=0.0,
    autotune_humanize=0.0,
    audio_upscaling=False,
    stereo_sound=False,
    output_format="wav",
    progress=gr.Progress(track_tqdm=True),
):
    if not rvc_model:
        raise ValueError("Не выбрана модель для RVC-инференса")
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Файл '{input_path}' не найден!")

    display_progress(0, "\n[⚙️] Запуск конвейера генерации...", True)

    display_progress(0.1, "Загружаем модель HuBERT...", False)
    hubert_model = load_hubert(HUBERT_BASE_PATH)

    display_progress(0.2, f"Загружаем модель '{rvc_model}'...", False)
    model_path, index_path = load_rvc_model(rvc_model)

    display_progress(0.3, "Получаем конвертер голоса...", False)
    cpt, version, net_g, tgt_sr, vc, use_f0 = get_vc(model_path)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    if len(base_name) > 50:
        gr.Warning("Имя файла превышает 50 символов и будет сокращено.")
        base_name = "Made_in_PolGen"
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}_({rvc_model}).{output_format}")

    display_progress(0.4, "Загружаем аудио...", False)
    audio = load_audio(input_path, 16000)

    display_progress(0.5, f"[🌌] Преобразуем аудио '{base_name}'...", True)
    audio_opt = vc.pipeline(
        model=hubert_model,
        net_g=net_g,
        sid=0,
        audio=audio,
        pitch=0 if autopitch else rvc_pitch,
        f0_min=f0_min,
        f0_max=f0_max,
        f0_method=f0_method,
        file_index=index_path,
        index_rate=index_rate,
        pitch_guidance=use_f0,
        volume_envelope=volume_envelope,
        version=version,
        protect=protect,
        autopitch=autopitch,
        autopitch_model_type=autopitch_model_type,
        autotune=autotune,
        autotune_tonic=autotune_tonic,
        autotune_scale=autotune_scale,
        autotune_strength=autotune_strength,
        autotune_retune_speed=autotune_retune_speed,
        autotune_flex_tune=autotune_flex_tune,
        autotune_preserve_vibrato=autotune_preserve_vibrato,
        autotune_humanize=autotune_humanize,
    )

    display_progress(0.8, "[💫] Сохраняем результат...", True)
    save_audio(audio_opt, tgt_sr, output_path, output_format, stereo_sound)

    if audio_upscaling:
        display_progress(0.9, "[🚀] Улучшаем качество аудио...", True)
        upscale(output_path, OUTPUT_DIR, 2, config.device)

    display_progress(0.95, "Освобождаем память...", False)
    del hubert_model, cpt, net_g, vc
    gc.collect()
    torch.cuda.empty_cache()

    display_progress(1.0, f"[✅] Преобразование завершено — {output_path}", True)
    return gr.Audio(output_path, label=os.path.basename(output_path))


def rvc_edgetts_infer(
    rvc_model=None,
    f0_method="rmvpe",
    f0_min=50,
    f0_max=1100,
    rvc_pitch=0,
    protect=0.5,
    index_rate=0,
    volume_envelope=1,
    autopitch=False,
    autopitch_model_type="baritone",
    autotune=False,
    autotune_tonic="C",
    autotune_scale="chromatic",
    autotune_strength=1.0,
    autotune_retune_speed=0.0,
    autotune_flex_tune=0.0,
    autotune_preserve_vibrato=0.0,
    autotune_humanize=0.0,
    stereo_sound=False,
    output_format="wav",
    tts_voice=None,
    tts_text=None,
    tts_rate=0,
    tts_volume=0,
    tts_pitch=0,
    audio_upscaling=False,
    progress=gr.Progress(track_tqdm=True),
):
    if not tts_text:
        raise ValueError("Введите текст!")
    if not tts_voice:
        raise ValueError("Выберите голос!")

    display_progress(1.0, "[🎙️] Синтезируем речь...", False)
    input_path = os.path.join(OUTPUT_DIR, "TTS_Voice.wav")
    asyncio.run(text_to_speech(tts_voice, tts_text, tts_rate, tts_volume, tts_pitch, input_path))

    output_path = rvc_infer(
        rvc_model=rvc_model,
        input_path=input_path,
        f0_method=f0_method,
        f0_min=f0_min,
        f0_max=f0_max,
        rvc_pitch=rvc_pitch,
        protect=protect,
        index_rate=index_rate,
        volume_envelope=volume_envelope,
        autopitch=autopitch,
        autopitch_model_type=autopitch_model_type,
        autotune=autotune,
        autotune_tonic=autotune_tonic,
        autotune_scale=autotune_scale,
        autotune_strength=autotune_strength,
        autotune_retune_speed=autotune_retune_speed,
        autotune_flex_tune=autotune_flex_tune,
        autotune_preserve_vibrato=autotune_preserve_vibrato,
        autotune_humanize=autotune_humanize,
        audio_upscaling=audio_upscaling,
        stereo_sound=stereo_sound,
        output_format=output_format,
    )

    return input_path, output_path
