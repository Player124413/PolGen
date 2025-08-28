import os

import numpy as np
import torch
import torchcrepe
from torchfcpe import spawn_bundled_infer_model

from rvc.lib.predictors.RMVPE import RMVPEF0Predictor


def median_interp_pitch(f0):
    f0 = np.where(f0 == 0, np.nan, f0)
    return float(np.median(np.interp(np.arange(len(f0)), np.where(~np.isnan(f0))[0], f0[~np.isnan(f0)])))


def calc_pitch_shift(f0, target_f0=155.0, limit_f0=12):
    return max(-limit_f0, min(limit_f0, int(np.round(12 * np.log2(target_f0 / median_interp_pitch(f0))))))


class RMVPE:
    def __init__(self, device, sample_rate=16000):
        self.device = device
        self.sample_rate = sample_rate
        self.model = RMVPEF0Predictor(os.path.join("rvc", "models", "predictors", "rmvpe.pt"), device=self.device)

    def get_f0(self, audio, type_rmvpe="rmvpe"):
        if type_rmvpe == "rmvpe":
            return self.model.infer_from_audio(audio, thred=0.03)

        if type_rmvpe == "rmvpe+":
            return self.model.infer_from_audio_modified(audio, thred=0.02)

        raise ValueError(f"Недопустимое значение: {type_rmvpe!r}")


class CREPE:
    def __init__(self, device, sample_rate=16000, hop_size=160):
        self.device = device
        self.sample_rate = sample_rate
        self.hop_size = hop_size

    def get_f0(self, audio, f0_min=50, f0_max=1100, p_len=None, model="full"):
        if p_len is None:
            p_len = audio.shape[0] // self.hop_size

        if not torch.is_tensor(audio):
            audio = torch.from_numpy(audio)

        f0, pd = torchcrepe.predict(
            audio.float().to(self.device).unsqueeze(dim=0),
            self.sample_rate,
            self.hop_size,
            f0_min,
            f0_max,
            model=model,
            batch_size=512,
            device=self.device,
            return_periodicity=True,
        )
        pd = torchcrepe.filter.median(pd, 3)
        f0 = torchcrepe.filter.mean(f0, 3)
        f0[pd < 0.1] = 0
        f0 = f0[0].cpu().numpy()

        return f0


class FCPE:
    def __init__(self, device, sample_rate=16000, hop_size=160):
        self.device = device
        self.sample_rate = sample_rate
        self.hop_size = hop_size
        self.model = spawn_bundled_infer_model(self.device)

    def get_f0(self, audio, p_len=None):
        if p_len is None:
            p_len = audio.shape[0] // self.hop_size

        if not torch.is_tensor(audio):
            audio = torch.from_numpy(audio)

        f0 = (
            self.model.infer(
                audio.float().to(self.device).unsqueeze(0),
                sr=self.sample_rate,
                decoder_mode="local_argmax",
                threshold=0.006,
            )
            .squeeze()
            .cpu()
            .numpy()
        )

        return f0
