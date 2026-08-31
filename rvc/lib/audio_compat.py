"""Чистые numpy/torch-реализации функций аудиообработки.

Заменяют тяжёлые зависимости (librosa → numba/llvmlite, soundfile → CFFI),
которые невозможно установить на Android/Termux. Реализации численно
эквивалентны librosa (проверяется тестами в tests/test_audio_compat.py).
"""

import numpy as np


def hz_to_mel(frequencies, htk: bool = False) -> np.ndarray:
    """Герцы → мели (формула HTK или Slaney, как в librosa)."""
    frequencies = np.asanyarray(frequencies, dtype=np.float64)
    if htk:
        return 2595.0 * np.log10(1.0 + frequencies / 700.0)
    # Формула Slaney (Auditory Toolbox)
    f_min, f_sp = 0.0, 200.0 / 3
    mels = (frequencies - f_min) / f_sp
    min_log_hz = 1000.0
    min_log_mel = (min_log_hz - f_min) / f_sp
    logstep = np.log(6.4) / 27.0
    log_t = frequencies >= min_log_hz
    mels[log_t] = min_log_mel + np.log(frequencies[log_t] / min_log_hz) / logstep
    return mels


def mel_to_hz(mels, htk: bool = False) -> np.ndarray:
    """Мели → герцы (формула HTK или Slaney, как в librosa)."""
    mels = np.asanyarray(mels, dtype=np.float64)
    if htk:
        return 700.0 * (10.0 ** (mels / 2595.0) - 1.0)
    f_min, f_sp = 0.0, 200.0 / 3
    freqs = f_min + f_sp * mels
    min_log_hz = 1000.0
    min_log_mel = (min_log_hz - f_min) / f_sp
    logstep = np.log(6.4) / 27.0
    log_t = mels >= min_log_mel
    freqs[log_t] = min_log_hz * np.exp(logstep * (mels[log_t] - min_log_mel))
    return freqs


def mel_frequencies(n_mels: int, fmin: float, fmax: float, htk: bool = False) -> np.ndarray:
    """Частоты центров мел-фильтров (n_mels + 2 точек, как в librosa)."""
    return mel_to_hz(hz_to_mel(np.linspace(0, 1, n_mels + 2) * (fmax - fmin) + fmin, htk=htk), htk=htk)


def mel_filterbank(
    sr: int,
    n_fft: int,
    n_mels: int,
    fmin: float = 0.0,
    fmax: float = None,
    htk: bool = False,
    norm: str = "slaney",
) -> np.ndarray:
    """Мел-фильтрбанк, численно эквивалентный librosa.filters.mel.

    Поддерживаются режимы, используемые PolGen: htk=True/False, norm='slaney'/'none'.
    """
    if fmax is None:
        fmax = float(sr) / 2

    fft_freqs = np.linspace(0, float(sr) / 2, 1 + n_fft // 2)
    mel_f = mel_frequencies(int(n_mels) + 2, fmin=fmin, fmax=fmax, htk=htk)

    fdiff = np.diff(mel_f)
    ramps = np.subtract.outer(mel_f, fft_freqs)

    weights = np.zeros((int(n_mels), len(fft_freqs)), dtype=np.float64)
    for i in range(int(n_mels)):
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i + 2] / fdiff[i + 1]
        weights[i] = np.maximum(0.0, np.minimum(lower, upper))

    if norm == "slaney":
        enorm = 2.0 / (mel_f[2 : int(n_mels) + 2] - mel_f[: int(n_mels)])
        weights *= enorm[:, np.newaxis]
    elif norm not in (None, "none"):
        raise ValueError(f"Неподдерживаемая нормировка мел-фильтра: {norm!r}")

    return weights


def frame_rms(
    y: np.ndarray,
    frame_length: int,
    hop_length: int,
    center: bool = True,
    pad_mode: str = "reflect",
) -> np.ndarray:
    """RMS по фреймам, численно эквивалентно librosa.feature.rms."""
    y = np.asarray(y, dtype=np.float64)

    if center:
        padding = [(int(frame_length // 2), int(frame_length // 2))]
        if pad_mode == "reflect":
            # np.pad с reflect не работает при нулевой длине — обрабатываем отдельно
            if y.size == 0:
                y = np.zeros(0)
            elif y.size == 1:
                y = np.repeat(y, 3)
            else:
                pad_len = int(frame_length // 2)
                if pad_len > y.size - 1:
                    # циклическое расширение для очень коротких сигналов
                    reps = int(np.ceil(pad_len / (y.size - 1))) + 1
                    y = np.concatenate([y] * reps)
        y = np.pad(y, padding, mode=pad_mode)

    if y.size < frame_length:
        y = np.pad(y, (0, int(frame_length - y.size)))

    n_frames = 1 + (y.size - frame_length) // hop_length
    if n_frames <= 0:
        return np.zeros(0)

    # Оконное среднее квадратов без копий (strided view)
    strides = (y.strides[0] * hop_length, y.strides[0])
    frames = np.lib.stride_tricks.as_strided(y, shape=(n_frames, int(frame_length)), strides=strides)
    return np.sqrt(np.mean(frames**2, axis=1, keepdims=True))


def to_mono(y: np.ndarray) -> np.ndarray:
    """Сведение к моно (среднее каналов), эквивалентно librosa.to_mono."""
    y = np.asarray(y)
    # Ожидается форма (..., каналы, время)
    if y.ndim > 1:
        y = np.mean(y, axis=-2)
    return np.ascontiguousarray(y)
