"""
Профессиональный AutoTune с полным контролем параметров.

Параметры:
- Retune Speed: скорость коррекции (0-400 мс)
- Flex-Tune: умная коррекция только фальшивых нот
- Preserve Vibrato: сохранение естественного вибрато
- Humanize: добавление микро-вариаций
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List
from scipy import signal


@dataclass
class AutoTuneConfig:
    """Конфигурация AutoTune."""

    # Музыкальные параметры
    scale_name: str = "chromatic"
    tonic_note: str = "C"
    a4_frequency: float = 440.0

    # Основные параметры коррекции
    correction_strength: float = 1.0  # 0-1
    retune_speed_ms: float = 0.0  # 0-400 мс

    # Продвинутые параметры
    flex_tune: float = 0.0  # 0-1
    preserve_vibrato: float = 0.0  # 0-1
    humanize: float = 0.0  # 0-1

    # Технические параметры
    vibrato_cutoff_hz: float = 4.0
    flex_tune_threshold_cents: float = 25.0
    humanize_rate_hz: float = 1.5
    humanize_depth_cents: float = 5.0


class AutoTune:
    """
    Профессиональный AutoTune с полным контролем параметров.

    Примеры:
        # Создание с конфигурацией
        config = AutoTuneConfig(
            scale_name="minor",
            tonic_note="A",
            correction_strength=0.8,
            retune_speed_ms=80.0,
            preserve_vibrato=0.7,
            flex_tune=0.5,
            humanize=0.3,
        )
        autotune = AutoTune(config=config)
        f0_corrected = autotune.apply(f0)

        # Простое создание
        autotune = AutoTune(scale_name="major", tonic_note="C")
        f0_corrected = autotune.apply(f0, strength=1.0)
    """

    SCALE_INTERVALS = {
        "chromatic": list(range(12)),
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "lydian": [0, 2, 4, 6, 7, 9, 11],
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
        "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
        "pentatonic_major": [0, 2, 4, 7, 9],
        "pentatonic_minor": [0, 3, 5, 7, 10],
        "blues": [0, 3, 5, 6, 7, 10],
    }

    TONIC_SEMITONES = {
        "C": 0, "C#": 1, "Db": 1,
        "D": 2, "D#": 3, "Eb": 3,
        "E": 4,
        "F": 5, "F#": 6, "Gb": 6,
        "G": 7, "G#": 8, "Ab": 8,
        "A": 9, "A#": 10, "Bb": 10,
        "B": 11,
    }

    DEFAULT_HOP_MS = 10.0

    def __init__(
        self,
        config: Optional[AutoTuneConfig] = None,
        scale_name: Optional[str] = None,
        tonic_note: Optional[str] = None,
        a4_frequency: Optional[float] = None,
    ):
        if config is not None:
            self.config = config
        else:
            self.config = AutoTuneConfig(
                scale_name=scale_name or "chromatic",
                tonic_note=tonic_note or "C",
                a4_frequency=a4_frequency or 440.0,
            )

        if self.config.scale_name not in self.SCALE_INTERVALS:
            raise ValueError(
                f"Неизвестная гамма: '{self.config.scale_name}'. "
                f"Доступные: {list(self.SCALE_INTERVALS.keys())}"
            )
        if self.config.tonic_note not in self.TONIC_SEMITONES:
            raise ValueError(
                f"Неизвестная тоника: '{self.config.tonic_note}'. "
                f"Доступные: {list(self.TONIC_SEMITONES.keys())}"
            )

        self._build_target_frequencies()

    def _build_target_frequencies(self):
        """Строит массив разрешённых частот для текущей гаммы."""
        scale_intervals = self.SCALE_INTERVALS[self.config.scale_name]
        tonic_semitone = self.TONIC_SEMITONES[self.config.tonic_note]

        frequencies = []
        for midi_note in range(24, 109):
            if (midi_note - tonic_semitone) % 12 in scale_intervals:
                freq = self.config.a4_frequency * (2 ** ((midi_note - 69) / 12))
                frequencies.append(freq)

        self.target_frequencies = np.array(frequencies)

    def apply(
        self,
        f0: np.ndarray,
        strength: Optional[float] = None,
        hop_ms: Optional[float] = None,
    ) -> np.ndarray:
        """
        Применяет автотюн к массиву F0.

        Args:
            f0: Входной массив F0 (Hz), 0 = unvoiced
            strength: Переопределяет correction_strength
            hop_ms: Время одного фрейма в мс

        Returns:
            Скорректированный массив F0
        """
        if len(self.target_frequencies) == 0:
            return f0.copy()

        hop_ms = hop_ms or self.DEFAULT_HOP_MS
        strength = strength if strength is not None else self.config.correction_strength

        if strength == 0:
            return f0.copy()

        voiced_mask = f0 > 0

        if not np.any(voiced_mask):
            return f0.copy()

        # 1. Извлекаем вибрато
        if self.config.preserve_vibrato > 0:
            f0_base, vibrato = self._extract_vibrato(f0, voiced_mask, hop_ms)
        else:
            f0_base = f0.copy()
            vibrato = np.zeros_like(f0)

        # 2. Находим целевые ноты
        target_f0 = self._find_target_frequencies(f0_base, voiced_mask)

        # 3. Вычисляем силу коррекции (flex-tune)
        frame_strength = self._compute_flex_strength(f0_base, target_f0, voiced_mask)

        # 4. Применяем коррекцию с retune speed
        f0_corrected = self._apply_retune(f0_base, target_f0, frame_strength, voiced_mask, hop_ms, strength)

        # 5. Возвращаем вибрато
        if self.config.preserve_vibrato > 0:
            f0_corrected = self._restore_vibrato(f0_corrected, vibrato, voiced_mask)

        # 6. Добавляем humanize
        if self.config.humanize > 0:
            f0_corrected = self._apply_humanize(f0_corrected, voiced_mask, hop_ms)

        return f0_corrected

    def _extract_vibrato(
        self,
        f0: np.ndarray,
        voiced_mask: np.ndarray,
        hop_ms: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Разделяет F0 на базовую частоту и вибрато."""
        f0_base = f0.copy()
        vibrato = np.zeros_like(f0)

        f0_log = np.zeros_like(f0)
        f0_log[voiced_mask] = 1200 * np.log2(f0[voiced_mask] / self.config.a4_frequency)

        sample_rate = 1000.0 / hop_ms
        cutoff = self.config.vibrato_cutoff_hz

        if np.sum(voiced_mask) < 10:
            return f0_base, vibrato

        nyq = sample_rate / 2
        if cutoff >= nyq:
            cutoff = nyq * 0.9

        try:
            b, a = signal.butter(2, cutoff / nyq, btype="low")
        except ValueError:
            return f0_base, vibrato

        segments = self._find_voiced_segments(voiced_mask)
        f0_log_filtered = f0_log.copy()

        for start, end in segments:
            if end - start < 10:
                continue

            segment = f0_log[start:end]
            pad_len = min(50, len(segment) // 2)
            padded = np.pad(segment, pad_len, mode="reflect")

            try:
                filtered = signal.filtfilt(b, a, padded)
                f0_log_filtered[start:end] = filtered[pad_len:-pad_len] if pad_len > 0 else filtered
            except ValueError:
                continue

        vibrato_cents = np.zeros_like(f0)
        vibrato_cents[voiced_mask] = f0_log[voiced_mask] - f0_log_filtered[voiced_mask]

        f0_base = np.zeros_like(f0)
        f0_base[voiced_mask] = self.config.a4_frequency * (2 ** (f0_log_filtered[voiced_mask] / 1200))

        return f0_base, vibrato_cents

    def _restore_vibrato(
        self,
        f0_corrected: np.ndarray,
        vibrato_cents: np.ndarray,
        voiced_mask: np.ndarray,
    ) -> np.ndarray:
        """Восстанавливает вибрато после коррекции."""
        result = f0_corrected.copy()
        vibrato_scaled = vibrato_cents * self.config.preserve_vibrato
        result[voiced_mask] = result[voiced_mask] * (2 ** (vibrato_scaled[voiced_mask] / 1200))
        return result

    def _find_target_frequencies(
        self,
        f0: np.ndarray,
        voiced_mask: np.ndarray,
    ) -> np.ndarray:
        """Находит ближайшую ноту в гамме для каждого фрейма."""
        target = np.zeros_like(f0)

        if not np.any(voiced_mask):
            return target

        voiced_f0 = f0[voiced_mask]

        indices = np.clip(
            np.searchsorted(self.target_frequencies, voiced_f0),
            1,
            len(self.target_frequencies) - 1,
        )

        lower = self.target_frequencies[indices - 1]
        upper = self.target_frequencies[indices]

        lower_dist = np.abs(np.log2(voiced_f0 / lower))
        upper_dist = np.abs(np.log2(voiced_f0 / upper))

        closest = np.where(lower_dist < upper_dist, lower, upper)
        target[voiced_mask] = closest

        return target

    def _compute_flex_strength(
        self,
        f0: np.ndarray,
        target_f0: np.ndarray,
        voiced_mask: np.ndarray,
    ) -> np.ndarray:
        """Вычисляет силу коррекции для каждого фрейма (flex-tune)."""
        strength = np.ones_like(f0)

        if self.config.flex_tune == 0:
            return strength

        deviation_cents = np.zeros_like(f0)
        valid = voiced_mask & (target_f0 > 0) & (f0 > 0)
        deviation_cents[valid] = 1200 * np.abs(np.log2(f0[valid] / target_f0[valid]))

        threshold = self.config.flex_tune_threshold_cents
        flex_factor = self.config.flex_tune

        below_threshold = valid & (deviation_cents < threshold)
        normalized_dev = np.zeros_like(deviation_cents)
        normalized_dev[below_threshold] = deviation_cents[below_threshold] / threshold

        strength[below_threshold] = 1.0 - flex_factor * (1.0 - normalized_dev[below_threshold]) ** 2
        strength = np.clip(strength, 0.0, 1.0)

        return strength

    def _apply_retune(
        self,
        f0: np.ndarray,
        target_f0: np.ndarray,
        frame_strength: np.ndarray,
        voiced_mask: np.ndarray,
        hop_ms: float,
        global_strength: float,
    ) -> np.ndarray:
        """Применяет коррекцию с учётом retune speed."""
        result = f0.copy()

        if self.config.retune_speed_ms <= 0:
            valid = voiced_mask & (target_f0 > 0)
            combined_strength = frame_strength * global_strength
            result[valid] = f0[valid] * (target_f0[valid] / f0[valid]) ** combined_strength[valid]
            return result

        dt_ms = hop_ms
        tau_ms = self.config.retune_speed_ms
        alpha = 1.0 - np.exp(-dt_ms / tau_ms)

        current_log = np.zeros_like(f0)
        current_log[voiced_mask] = np.log2(f0[voiced_mask])

        target_log = np.zeros_like(f0)
        valid = voiced_mask & (target_f0 > 0)
        target_log[valid] = np.log2(target_f0[valid])

        result_log = current_log.copy()

        for i in range(1, len(f0)):
            if not voiced_mask[i]:
                continue

            if not voiced_mask[i - 1]:
                continue

            combined_strength = frame_strength[i] * global_strength
            effective_target = current_log[i] + (target_log[i] - current_log[i]) * combined_strength
            result_log[i] = result_log[i - 1] + (effective_target - result_log[i - 1]) * alpha

        result[voiced_mask] = 2 ** result_log[voiced_mask]

        return result

    def _apply_humanize(
        self,
        f0: np.ndarray,
        voiced_mask: np.ndarray,
        hop_ms: float,
    ) -> np.ndarray:
        """Добавляет микро-вариации для естественности."""
        result = f0.copy()
        n_frames = len(f0)

        sample_rate = 1000.0 / hop_ms
        t = np.arange(n_frames) / sample_rate

        phase = np.random.uniform(0, 2 * np.pi)
        lfo = np.sin(2 * np.pi * self.config.humanize_rate_hz * t + phase)

        noise = np.random.randn(n_frames)
        kernel_size = max(3, int(sample_rate / 10))
        if kernel_size % 2 == 0:
            kernel_size += 1
        noise_smooth = np.convolve(noise, np.ones(kernel_size) / kernel_size, mode="same")
        noise_smooth = noise_smooth / (np.std(noise_smooth) + 1e-6)

        humanize_cents = (lfo * 0.7 + noise_smooth * 0.3) * self.config.humanize_depth_cents * self.config.humanize

        result[voiced_mask] = result[voiced_mask] * (2 ** (humanize_cents[voiced_mask] / 1200))

        return result

    def _find_voiced_segments(self, voiced_mask: np.ndarray) -> List[Tuple[int, int]]:
        """Находит непрерывные озвученные сегменты."""
        segments = []
        segment_start = None

        for i, is_voiced in enumerate(voiced_mask):
            if is_voiced and segment_start is None:
                segment_start = i
            elif not is_voiced and segment_start is not None:
                segments.append((segment_start, i))
                segment_start = None

        if segment_start is not None:
            segments.append((segment_start, len(voiced_mask)))

        return segments
