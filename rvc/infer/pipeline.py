import ctypes
import gc
import os

import numpy as np
import torch
import torch.nn.functional as F
from scipy import signal

# malloc_trim: возврат освобождённых страниц кучи ОС (glibc). На Android/bionic
# функции нет — остаётся None, и вызов просто пропускается.
try:
    _malloc_trim = ctypes.CDLL("libc.so.6").malloc_trim
except OSError:  # pragma: no cover - зависит от платформы
    _malloc_trim = None

from rvc.lib.audio_compat import frame_rms
from rvc.lib.faiss_numpy import open_index
from rvc.lib.predictors.f0 import CREPE, FCPE, RMVPE, AutoTune, calc_pitch_shift, get_cached_f0_predictor

try:
    from librosa.feature import rms as _librosa_rms
except Exception:  # noqa: BLE001 - среда без librosa (Android/TermUX и т.п.)
    _librosa_rms = None

# Фильтр Баттерворта для высоких частот
bh, ah = signal.butter(N=5, Wn=48, btype="high", fs=16000)


# Класс для обработки аудио
class AudioProcessor:
    @staticmethod
    def _rms(y: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
        """RMS по фреймам: librosa при наличии, иначе численно эквивалентный numpy."""
        if _librosa_rms is not None:
            return _librosa_rms(y=y, frame_length=frame_length, hop_length=hop_length)
        return frame_rms(y, frame_length=frame_length, hop_length=hop_length)

    @staticmethod
    def change_rms(
        source_audio: np.ndarray,
        source_rate: int,
        target_audio: np.ndarray,
        target_rate: int,
        rate: float,
    ):
        rms1 = AudioProcessor._rms(source_audio, source_rate // 2 * 2, source_rate // 2)
        rms2 = AudioProcessor._rms(target_audio, target_rate // 2 * 2, target_rate // 2)

        rms1 = F.interpolate(torch.from_numpy(np.ascontiguousarray(rms1)).float().unsqueeze(0), size=target_audio.shape[0], mode="linear").squeeze()
        rms2 = F.interpolate(torch.from_numpy(np.ascontiguousarray(rms2)).float().unsqueeze(0), size=target_audio.shape[0], mode="linear").squeeze()
        rms2 = torch.maximum(rms2, torch.zeros_like(rms2) + 1e-6)

        adjusted_audio = target_audio * (torch.pow(rms1, 1 - rate) * torch.pow(rms2, rate - 1)).numpy()
        return adjusted_audio


# Класс для преобразования голоса
class VC:
    def __init__(self, tgt_sr, config):
        """Инициализация параметров для преобразования голоса."""
        self.x_pad = config.x_pad
        self.x_query = config.x_query
        self.x_center = config.x_center
        self.x_max = config.x_max
        self.sample_rate = 16000
        self.window = 160
        self.tgt_sr = tgt_sr
        self.t_pad = self.sample_rate * self.x_pad
        self.t_pad_tgt = self.tgt_sr * self.x_pad
        self.t_pad2 = self.t_pad * 2
        self.t_query = self.sample_rate * self.x_query
        self.t_center = self.sample_rate * self.x_center
        self.t_max = self.sample_rate * self.x_max
        self.device = config.device

    def get_f0(
        self,
        audio,
        p_len,
        pitch,
        f0_min,
        f0_max,
        f0_method,
        autopitch,
        autopitch_threshold,
        autotune,
        autotune_tonic,
        autotune_scale,
        autotune_strength,
    ):
        """Получает F0 с использованием выбранного метода."""
        f0 = None
        f0_mel_min = 1127 * np.log(1 + f0_min / 700)
        f0_mel_max = 1127 * np.log(1 + f0_max / 700)

        if f0_method in ("crepe", "crepe-tiny"):
            model = CREPE(device=self.device, sample_rate=self.sample_rate, hop_size=self.window)
            f0 = model.get_f0(audio, f0_min, f0_max, p_len, ("full" if f0_method == "crepe" else "tiny"))
            del model
        elif f0_method in ("rmvpe", "rmvpe+"):
            # Кэшированный предиктор: веса RMVPE загружаются один раз
            model = get_cached_f0_predictor(f0_method, self.device, self.sample_rate)
            f0 = model.get_f0(audio, f0_min, f0_max, f0_method)
        elif f0_method == "fcpe":
            model = get_cached_f0_predictor(f0_method, self.device, self.sample_rate, self.window)
            f0 = model.get_f0(audio, f0_min, f0_max, p_len)

        if f0 is None:
            raise ValueError("Метод F0 не распознан или не смог рассчитать F0.")

        # АвтоПитч (автоматическое определение высоты тона)
        if autopitch is True:
            pitch += calc_pitch_shift(f0, autopitch_threshold, 12)

        # АвтоТюн (коррекция высоты тона)
        if autotune is True:
            AT = AutoTune(scale_name=autotune_scale, tonic_note=autotune_tonic)
            f0 = AT.apply_autotune(f0, autotune_strength)

        f0 = np.multiply(f0, pow(2, pitch / 12))
        f0_mel = 1127 * np.log(1 + f0 / 700)
        f0_mel[f0_mel > 0] = (f0_mel[f0_mel > 0] - f0_mel_min) * 254 / (f0_mel_max - f0_mel_min) + 1
        f0_mel[f0_mel <= 1] = 1
        f0_mel[f0_mel > 255] = 255
        f0_mel = np.rint(f0_mel).astype(np.int32)

        return f0_mel, f0

    def vc(
        self,
        model,
        net_g,
        sid,
        audio0,
        pitch,
        pitchf,
        index,
        big_npy,
        index_rate,
        version,
        protect,
    ):
        """Преобразует аудио с использованием модели."""
        feats = torch.from_numpy(audio0).float()
        if feats.dim() == 2:
            feats = feats.mean(-1)
        assert feats.dim() == 1, feats.dim()
        feats = feats.view(1, -1)
        padding_mask = torch.BoolTensor(feats.shape).to(self.device).fill_(False)

        inputs = {
            "source": feats.to(self.device),
            "padding_mask": padding_mask,
            "output_layer": 9 if version == "v1" else 12,
        }

        with torch.inference_mode():
            logits = model.extract_features(**inputs)
            feats = model.final_proj(logits[0]) if version == "v1" else logits[0]

        if protect < 0.5 and pitch is not None and pitchf is not None:
            feats0 = feats.clone()

        if index is not None and big_npy is not None and index_rate != 0:
            npy = feats[0].cpu().numpy()
            score, ix = index.search(npy, k=8)
            weight = np.square(1 / np.maximum(score, 1e-12))
            weight /= weight.sum(axis=1, keepdims=True)
            npy = np.sum(big_npy[ix] * np.expand_dims(weight, axis=2), axis=1)
            feats = torch.from_numpy(npy).unsqueeze(0).to(self.device) * index_rate + (1 - index_rate) * feats

        feats = F.interpolate(feats.permute(0, 2, 1), scale_factor=2).permute(0, 2, 1)
        if protect < 0.5 and pitch is not None and pitchf is not None:
            feats0 = F.interpolate(feats0.permute(0, 2, 1), scale_factor=2).permute(0, 2, 1)

        p_len = audio0.shape[0] // self.window
        if feats.shape[1] < p_len:
            p_len = feats.shape[1]
            if pitch is not None and pitchf is not None:
                pitch = pitch[:, :p_len]
                pitchf = pitchf[:, :p_len]

        if protect < 0.5 and pitch is not None and pitchf is not None:
            pitchff = pitchf.clone()
            pitchff[pitchf > 0] = 1
            pitchff[pitchf < 1] = protect
            pitchff = pitchff.unsqueeze(-1)
            feats = feats * pitchff + feats0 * (1 - pitchff)
            feats = feats.to(feats0.dtype)

        p_len = torch.tensor([p_len], device=self.device).long()
        with torch.inference_mode():
            hasp = pitch is not None and pitchf is not None
            arg = (feats.float(), p_len, pitch, pitchf.float(), sid) if hasp else (feats.float(), p_len, sid)
            audio1 = (net_g.infer(*arg)[0][0, 0]).data.cpu().float().numpy()
            del hasp, arg

        if protect < 0.5 and pitch is not None and pitchf is not None:
            del feats0
        del feats, padding_mask
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return audio1

    def pipeline(
        self,
        model,
        net_g,
        sid,
        audio,
        pitch,
        f0_min,
        f0_max,
        f0_method,
        file_index,
        index_rate,
        pitch_guidance,
        volume_envelope,
        version,
        protect,
        autopitch,
        autopitch_threshold,
        autotune,
        autotune_tonic,
        autotune_scale,
        autotune_strength,
        progress_callback=None,
    ):
        """Основной конвейер для преобразования аудио."""
        index = big_npy = None
        if file_index and os.path.exists(file_index) and index_rate != 0:
            try:
                # Индекс кэшируется: повторные конвертации не перечитывают
                # .index с диска (faiss — если установлен, иначе numpy-ридер)
                index = open_index(file_index)
                if index is not None:
                    big_npy = index.reconstruct_n(0, index.ntotal)
            except Exception as error:
                print(f"Произошла ошибка при чтении индекса FAISS: {error}")
                index = big_npy = None

        opt_ts = []
        audio = signal.filtfilt(bh, ah, audio)
        audio_pad = np.pad(audio, (self.window // 2, self.window // 2), mode="reflect")

        if audio_pad.shape[0] > self.t_max:
            # Векторизованная оконная сумма (раньше — цикл из 160 итераций)
            n_sum = audio_pad.shape[0] - self.window
            strided = np.lib.stride_tricks.as_strided(
                audio_pad,
                shape=(self.window, n_sum),
                strides=(audio_pad.strides[0], audio_pad.strides[0]),
            )
            audio_sum = strided.sum(axis=0)

            for t in range(self.t_center, audio.shape[0], self.t_center):
                segment = audio_sum[t - self.t_query : t + self.t_query]
                min_index = np.where(np.abs(segment) == np.abs(segment).min())[0][0]
                opt_ts.append(t - self.t_query + min_index)

            # Энергетические минимумы могут дать сегменты длиннее чанка
            # (активации HiFi-GAN ~120 МБ на секунду аудио → пик RAM растёт
            # с длиной трека). Ограничиваем: короткие (<x_center/2) склеиваем,
            # длинные (>x_max) режем принудительно — пик памяти ограничен.
            capped = []
            s = 0
            for t in opt_ts:
                if t - s < self.t_center // 2:
                    continue  # слишком близко к предыдущей точке разреза
                while t - s > self.t_max:
                    forced = (s + self.t_max) // self.window * self.window
                    capped.append(forced)
                    s = forced
                capped.append(t)
                s = t
            while audio.shape[0] + 2 * self.t_pad - s > self.t_max + self.t_center // 2:
                s += self.t_max
                capped.append(s)
            opt_ts = capped

        s = 0
        t = None
        audio_opt = []
        audio_pad = np.pad(audio, (self.t_pad, self.t_pad), mode="reflect")
        p_len = audio_pad.shape[0] // self.window
        sid = torch.tensor(sid, device=self.device).unsqueeze(0).long()

        pitch_tensor = pitchf_tensor = None
        if pitch_guidance:
            pitch, pitchf = self.get_f0(
                audio_pad,
                p_len,
                pitch,
                f0_min,
                f0_max,
                f0_method,
                autopitch,
                autopitch_threshold,
                autotune,
                autotune_tonic,
                autotune_scale,
                autotune_strength,
            )
            pitch = pitch[:p_len]
            pitchf = pitchf[:p_len]

            if self.device == "mps":
                pitchf = pitchf.astype(np.float32)

            pitch_tensor = torch.tensor(pitch, device=self.device).unsqueeze(0).long()
            pitchf_tensor = torch.tensor(pitchf, device=self.device).unsqueeze(0).float()

        total_steps = len(opt_ts) + 1
        for step, t in enumerate(opt_ts):
            t = t // self.window * self.window

            audio_segment = audio_pad[s : t + self.t_pad2 + self.window]
            pitch_segment = pitch_tensor[:, s // self.window : (t + self.t_pad2) // self.window] if pitch_guidance else None
            pitchf_segment = pitchf_tensor[:, s // self.window : (t + self.t_pad2) // self.window] if pitch_guidance else None

            audio_opt.append(
                self.vc(
                    model,
                    net_g,
                    sid,
                    audio_segment,
                    pitch_segment,
                    pitchf_segment,
                    index,
                    big_npy,
                    index_rate,
                    version,
                    protect,
                )[self.t_pad_tgt : -self.t_pad_tgt],
            )
            s = t
            # Циклические ссылки копятся между чанками и раздуливают RSS на
            # длинных треках; после gc возвращаем страницы кучи ОС
            gc.collect()
            if _malloc_trim is not None:
                _malloc_trim(0)
            if progress_callback is not None:
                progress_callback((step + 1) / (total_steps + 1), "Конвертация")

        pitch_segment = pitch_tensor[:, t // self.window :] if pitch_guidance and t is not None else pitch_tensor
        pitchf_segment = pitchf_tensor[:, t // self.window :] if pitch_guidance and t is not None else pitchf_tensor

        audio_opt.append(
            self.vc(
                model,
                net_g,
                sid,
                audio_pad[t:],
                pitch_segment,
                pitchf_segment,
                index,
                big_npy,
                index_rate,
                version,
                protect,
            )[self.t_pad_tgt : -self.t_pad_tgt],
        )
        if progress_callback is not None:
            progress_callback(1.0, "Конвертация")

        audio_opt = np.concatenate(audio_opt)
        if volume_envelope != 1:
            audio_opt = AudioProcessor.change_rms(audio, self.sample_rate, audio_opt, self.tgt_sr, volume_envelope)

        audio_max = np.abs(audio_opt).max() / 0.99
        if audio_max > 1:
            audio_opt /= audio_max

        if pitch_guidance:
            del pitch_tensor, pitchf_tensor
        del sid
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return audio_opt
