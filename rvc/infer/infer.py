import asyncio
import gc
import os

import edge_tts
import gradio as gr
import numpy as np
import torch
from pydub import AudioSegment

from rvc.infer.config import Config
from rvc.infer.pipeline import VC
from rvc.lib.algorithm.synthesizers import Synthesizer
from rvc.lib.fairseq import load_model
from rvc.lib.my_utils import load_audio
from rvc.modules.audio_upscaler import upscale

# Определяем пути к папкам и файлам
RVC_MODELS_DIR = os.path.join(os.getcwd(), "models", "RVC_models")
OUTPUT_DIR = os.path.join(os.getcwd(), "output", "RVC_output")
HUBERT_BASE_PATH = os.path.join(os.getcwd(), "rvc", "models", "embedders", "hubert_base.pt")

# Создаем папки, если их нет
os.makedirs(RVC_MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Инициализация конфигурации
config = Config()


class RVCInferer:
    def __init__(self):
        self.hubert_model = None
        self.model_cache = {}
        self._load_hubert()

    def _load_hubert(self):
        """Загрузка модели Hubert."""
        self.hubert_model = load_model(HUBERT_BASE_PATH).to(config.device).eval()

    def _load_rvc_model(self, rvc_model):
        """Загрузка модели и индекса RVC."""
        if rvc_model in self.model_cache:
            return self.model_cache[rvc_model]

        # Путь к каталогу модели
        model_dir = os.path.join(RVC_MODELS_DIR, rvc_model)
        model_files = os.listdir(model_dir)

        # Поиск .pth файла
        rvc_model_path = next((os.path.join(model_dir, f) for f in model_files if f.endswith(".pth")), None)
        # Поиск .index файла
        rvc_index_path = next((os.path.join(model_dir, f) for f in model_files if f.endswith(".index")), None)

        if not rvc_model_path:
            raise ValueError(f"\033[91mERROR!\033[0m Модель {rvc_model} не найдена.")

        # Загрузка состояния модели
        cpt = torch.load(rvc_model_path, map_location="cpu", weights_only=True)

        # Проверка формата модели
        if "config" not in cpt or "weight" not in cpt:
            raise ValueError(f"Неверный формат для {rvc_model_path}. Используйте голосовую модель, обученную на RVC v2.")

        # Извлечение параметров модели
        tgt_sr = cpt["config"][-1]
        cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
        use_f0 = cpt.get("f0", 1)
        version = cpt.get("version", "v1")
        vocoder = cpt.get("vocoder", "HiFi-GAN")
        input_dim = 768 if version == "v2" else 256

        # Инициализация synthesizer
        net_g = Synthesizer(*cpt["config"], use_f0=use_f0, text_enc_hidden_dim=input_dim, vocoder=vocoder)
        del net_g.enc_q
        net_g.load_state_dict(cpt["weight"], strict=False)
        net_g = net_g.to(config.device).float()
        net_g.eval()

        # Инициализация объекта VC
        vc = VC(tgt_sr, config)

        # Кэшировать загруженную модель
        self.model_cache[rvc_model] = (cpt, version, net_g, tgt_sr, vc, use_f0, rvc_model_path, rvc_index_path)
        return self.model_cache[rvc_model]

    def display_progress(self, percent, message, is_print, progress=gr.Progress()):
        if is_print:
            print(message)
        progress(percent, desc=message)

    async def text_to_speech(self, voice, text, rate, volume, pitch, output_path):
        if not -100 <= rate <= 100:
            raise ValueError("Rate должен быть в диапазоне от -100% до +100%")
        if not -100 <= volume <= 100:
            raise ValueError("Volume должен быть в диапазоне от -100% до +100%")
        if not -100 <= pitch <= 100:
            raise ValueError("Pitch должен быть в диапазоне от -100Hz до +100Hz")

        rate = f"+{rate}%" if rate >= 0 else f"{rate}%"
        volume = f"+{volume}%" if volume >= 0 else f"{volume}%"
        pitch = f"+{pitch}Hz" if pitch >= 0 else f"{pitch}Hz"

        communicate = edge_tts.Communicate(voice=voice, text=text, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(output_path)

    @torch.no_grad()
    def rvc_infer(
        self,
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
        autopitch_threshold=155.0,
        autotune=False,
        autotune_strength=1.0,
        audio_upscaling=False,  # FlashSR
        stereo_sound=False,
        output_format="wav",
        progress=gr.Progress(track_tqdm=True),
    ):
        if not rvc_model:
            raise ValueError("Выберите голосовую модель для преобразования.")
        if not os.path.exists(input_path):
            raise ValueError(f"Файл '{input_path}' не найден. Убедитесь, что он загружен, или проверьте путь.")

        self.display_progress(0, "\n[⚙️] Запуск конвейера генерации...", True)

        # Загрузка модели RVC (из кэша, если доступно)
        self.display_progress(0.2, "Загрузка модели и индекса RVC...", False)
        cpt, version, net_g, tgt_sr, vc, use_f0, model_path, index_path = self._load_rvc_model(rvc_model)

        # Создание имени выходного файла
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        if len(base_name) > 50:
            gr.Warning("Имя файла превышает 50 символов и будет сокращено для удобства.")
            base_name = "Made_in_PolGen"  # Изменить имя файла, если оригинал превышает 50 символов
        output_path = os.path.join(OUTPUT_DIR, f"{base_name}_({rvc_model}).{output_format}")

        # Загрузка аудиофайла
        self.display_progress(0.4, "Загрузка аудиофайла...", False)
        audio = load_audio(input_path, 16000)

        self.display_progress(0.5, f"[🌌] Преобразование аудио — {base_name}...", True)
        audio_opt = vc.pipeline(
            self.hubert_model,
            net_g,
            0,
            audio,
            0 if autopitch else rvc_pitch,
            f0_min,
            f0_max,
            f0_method,
            index_path,
            index_rate,
            use_f0,
            volume_envelope,
            version,
            protect,
            autopitch,
            autopitch_threshold,
            autotune,
            autotune_strength,
        )
        # Сохранение файла и преобразование в выбранный формат
        self.display_progress(0.8, "[💫] Сохранение результата...", True)
        audio_segment = AudioSegment(data=(audio_opt * 32767).astype(np.int16).tobytes(), sample_width=2, frame_rate=tgt_sr, channels=1)
        if stereo_sound:
            audio_segment = audio_segment.set_channels(2)
        audio_segment.export(output_path, format=output_format)

        if audio_upscaling:
            self.display_progress(0.9, "[🚀] Улучшение качества звука...", True)
            upscale(output_path, OUTPUT_DIR, 2, config.device)

        # Очистка памяти с сохранением кэша
        self.display_progress(0.95, "Очистка временной памяти...", False)
        gc.collect()
        torch.cuda.empty_cache()

        self.display_progress(1.0, f"[✅] Преобразование завершено — {output_path}", True)
        return gr.Audio(output_path, label=os.path.basename(output_path))

    async def rvc_edgetts_infer(
        self,
        # RVC
        rvc_model=None,
        f0_method="rmvpe",
        f0_min=50,
        f0_max=1100,
        rvc_pitch=0,
        protect=0.5,
        index_rate=0,
        volume_envelope=1,
        autopitch=False,
        autopitch_threshold=155.0,
        autotune=False,
        autotune_strength=1.0,
        stereo_sound=False,
        output_format="wav",
        # EdgeTTS
        tts_voice=None,
        tts_text=None,
        tts_rate=0,
        tts_volume=0,
        tts_pitch=0,
        # FlashSR
        audio_upscaling=False,
        progress=gr.Progress(track_tqdm=True),
    ):
        if not tts_text:
            raise ValueError("Введите необходимый текст в поле ввода.")
        if not tts_voice:
            raise ValueError("Выберите язык и голос для синтеза речи.")

        self.display_progress(1.0, "[🎙️] Синтез речи...", False)
        input_path = os.path.join(OUTPUT_DIR, "TTS_Voice.wav")
        await self.text_to_speech(tts_voice, tts_text, tts_rate, tts_volume, tts_pitch, input_path)

        output_path = self.rvc_infer(
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
            autopitch_threshold=autopitch_threshold,
            autotune=autotune,
            autotune_strength=autotune_strength,
            audio_upscaling=audio_upscaling,
            stereo_sound=stereo_sound,
            output_format=output_format,
        )

        return input_path, output_path
