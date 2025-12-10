"""
Улучшенный AutoPitch для автоматического определения оптимального сдвига высоты тона.
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class VoiceType(Enum):
    """Типы голосов с их характерными диапазонами F0 (Hz)."""

    BASS = ("bass", 80, 110, 165)
    BARITONE = ("baritone", 100, 145, 200)
    TENOR = ("tenor", 130, 175, 260)
    ALTO = ("alto", 175, 230, 350)
    SOPRANO = ("soprano", 250, 340, 500)

    def __init__(self, label: str, f0_min: float, f0_center: float, f0_max: float):
        self.label = label
        self.f0_min = f0_min
        self.f0_center = f0_center
        self.f0_max = f0_max

    def contains(self, f0: float) -> bool:
        return self.f0_min <= f0 <= self.f0_max

    def distance_to(self, f0: float) -> float:
        if f0 <= 0:
            return float("inf")
        return abs(12 * np.log2(f0 / self.f0_center))


@dataclass
class VoiceAnalysis:
    """Результат анализа голоса входного аудио."""

    f0_median: float
    f0_weighted_median: float
    f0_mean: float
    f0_std: float
    f0_min: float
    f0_max: float
    f0_percentile_10: float
    f0_percentile_90: float
    detected_type: VoiceType
    confidence: float
    voiced_ratio: float
    total_frames: int
    voiced_frames: int


@dataclass
class AutoPitchResult:
    """Результат работы AutoPitch."""

    pitch_shift: float
    input_center: float
    target_center: float
    reasoning: str


class AutoPitch:
    """
    Улучшенный AutoPitch для автоматического определения сдвига высоты тона.
    
    Использует калибровку модели для точного определения целевой частоты.
    """

    MIN_VOICED_RATIO = 0.1
    MIN_STABLE_FRAMES = 3
    OUTLIER_IQR_FACTOR = 1.5
    MAX_SHIFT_SEMITONES = 24.0

    def __init__(self):
        pass

    def analyze_f0(self, f0: np.ndarray) -> VoiceAnalysis:
        """Анализирует массив F0 и возвращает характеристики голоса."""
        total_frames = len(f0)
        voiced_mask = f0 > 0
        f0_voiced = f0[voiced_mask]
        voiced_frames = len(f0_voiced)

        if voiced_frames == 0:
            return VoiceAnalysis(
                f0_median=0,
                f0_weighted_median=0,
                f0_mean=0,
                f0_std=0,
                f0_min=0,
                f0_max=0,
                f0_percentile_10=0,
                f0_percentile_90=0,
                detected_type=VoiceType.BARITONE,
                confidence=0,
                voiced_ratio=0,
                total_frames=total_frames,
                voiced_frames=0,
            )

        voiced_ratio = voiced_frames / total_frames
        f0_filtered = self._remove_outliers_iqr(f0_voiced)

        if len(f0_filtered) < 10:
            f0_filtered = f0_voiced

        f0_median = float(np.median(f0_filtered))
        f0_mean = float(np.mean(f0_filtered))
        f0_std = float(np.std(f0_filtered))
        f0_min_val = float(np.min(f0_filtered))
        f0_max_val = float(np.max(f0_filtered))
        f0_p10 = float(np.percentile(f0_filtered, 10))
        f0_p90 = float(np.percentile(f0_filtered, 90))
        f0_weighted = self._compute_weighted_median(f0, voiced_mask)
        detected_type, confidence = self._detect_voice_type(f0_filtered, f0_weighted)

        return VoiceAnalysis(
            f0_median=f0_median,
            f0_weighted_median=f0_weighted,
            f0_mean=f0_mean,
            f0_std=f0_std,
            f0_min=f0_min_val,
            f0_max=f0_max_val,
            f0_percentile_10=f0_p10,
            f0_percentile_90=f0_p90,
            detected_type=detected_type,
            confidence=confidence,
            voiced_ratio=voiced_ratio,
            total_frames=total_frames,
            voiced_frames=voiced_frames,
        )

    def _remove_outliers_iqr(self, data: np.ndarray) -> np.ndarray:
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        lower_bound = q1 - self.OUTLIER_IQR_FACTOR * iqr
        upper_bound = q3 + self.OUTLIER_IQR_FACTOR * iqr
        return data[(data >= lower_bound) & (data <= upper_bound)]

    def _compute_weighted_median(self, f0: np.ndarray, voiced_mask: np.ndarray) -> float:
        if not np.any(voiced_mask):
            return 0.0

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

        if not segments:
            return float(np.median(f0[voiced_mask]))

        values = []
        weights = []

        for start, end in segments:
            segment_f0 = f0[start:end]
            segment_length = end - start

            if segment_length >= self.MIN_STABLE_FRAMES:
                segment_median = np.median(segment_f0)
                values.append(segment_median)
                weights.append(segment_length)

        if not values:
            return float(np.median(f0[voiced_mask]))

        values = np.array(values)
        weights = np.array(weights)
        sorted_indices = np.argsort(values)
        sorted_values = values[sorted_indices]
        sorted_weights = weights[sorted_indices]
        cumsum = np.cumsum(sorted_weights)
        cutoff = cumsum[-1] / 2
        median_idx = np.searchsorted(cumsum, cutoff)

        return float(sorted_values[min(median_idx, len(sorted_values) - 1)])

    def _detect_voice_type(self, f0_filtered: np.ndarray, f0_weighted: float) -> Tuple[VoiceType, float]:
        center_f0 = f0_weighted if f0_weighted > 0 else np.median(f0_filtered)
        best_type = VoiceType.BARITONE
        min_distance = float("inf")

        for voice_type in VoiceType:
            distance = voice_type.distance_to(center_f0)
            if distance < min_distance:
                min_distance = distance
                best_type = voice_type

        in_range = best_type.contains(center_f0)
        distance_factor = max(0, 1 - min_distance / 6)
        f0_std = np.std(f0_filtered)
        f0_mean = np.mean(f0_filtered)
        stability_factor = max(0, 1 - (f0_std / f0_mean) * 2) if f0_mean > 0 else 0
        confidence = (0.5 if in_range else 0.2) * 0.4 + distance_factor * 0.4 + stability_factor * 0.2

        return best_type, min(1.0, max(0.0, confidence))

    def calculate_pitch_shift(
        self,
        f0: np.ndarray,
        model_f0_center: float,
    ) -> AutoPitchResult:
        """
        Вычисляет оптимальный сдвиг высоты тона.
        
        Args:
            f0: Массив F0 входного аудио
            model_f0_center: Центральная частота голоса модели (из калибровки)
        """
        analysis = self.analyze_f0(f0)

        if analysis.voiced_ratio < self.MIN_VOICED_RATIO:
            return AutoPitchResult(
                pitch_shift=0.0,
                input_center=0.0,
                target_center=model_f0_center,
                reasoning=f"Недостаточно озвученных фреймов ({analysis.voiced_ratio:.1%})",
            )

        input_center = analysis.f0_weighted_median
        if input_center <= 0:
            input_center = analysis.f0_median

        if input_center <= 0:
            return AutoPitchResult(
                pitch_shift=0.0,
                input_center=0.0,
                target_center=model_f0_center,
                reasoning="Не удалось определить центральную частоту входа",
            )

        # Вычисляем точный сдвиг
        pitch_shift = 12.0 * np.log2(model_f0_center / input_center)
        pitch_shift = float(np.clip(pitch_shift, -self.MAX_SHIFT_SEMITONES, self.MAX_SHIFT_SEMITONES))

        reasoning = (
            f"Вход: {input_center:.1f} Hz ({analysis.detected_type.label}) → "
            f"Модель: {model_f0_center:.1f} Hz → "
            f"Сдвиг: {pitch_shift:+.2f}"
        )

        return AutoPitchResult(
            pitch_shift=pitch_shift,
            input_center=input_center,
            target_center=model_f0_center,
            reasoning=reasoning,
        )


_autopitch_instance: Optional[AutoPitch] = None


def get_autopitch() -> AutoPitch:
    global _autopitch_instance
    if _autopitch_instance is None:
        _autopitch_instance = AutoPitch()
    return _autopitch_instance


def calculate_pitch_shift(f0: np.ndarray, model_f0_center: float) -> float:
    """
    Вычисляет сдвиг высоты тона.

    Args:
        f0: Массив значений F0 (Hz)
        model_f0_center: Центральная частота голоса модели

    Returns:
        Сдвиг в полутонах (float)
    """
    autopitch = get_autopitch()
    result = autopitch.calculate_pitch_shift(f0, model_f0_center)
    return result.pitch_shift
