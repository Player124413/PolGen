"""
Улучшенный AutoPitch для автоматического определения оптимального сдвига высоты тона.

Анализирует входное аудио и вычисляет сдвиг для соответствия целевому типу голоса модели.
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional


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
        """Проверяет, попадает ли F0 в диапазон этого типа голоса."""
        return self.f0_min <= f0 <= self.f0_max
    
    def distance_to(self, f0: float) -> float:
        """Расстояние от F0 до центра диапазона в полутонах."""
        if f0 <= 0:
            return float('inf')
        return abs(12 * np.log2(f0 / self.f0_center))


class ModelVoiceType(Enum):
    """Типы голосов для RVC моделей (упрощённый выбор для пользователя)."""
    MALE = "male"
    FEMALE = "female"
    AUTO = "auto"


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
    confidence: float  # 0-1, насколько уверены в определении типа
    voiced_ratio: float  # доля озвученных фреймов
    total_frames: int
    voiced_frames: int


@dataclass  
class AutoPitchResult:
    """Результат работы AutoPitch."""
    pitch_shift: int  # сдвиг в полутонах
    input_analysis: VoiceAnalysis
    target_f0: float
    reasoning: str  # пояснение для отладки


class AutoPitch:
    """
    Улучшенный AutoPitch для автоматического определения сдвига высоты тона.
    
    Анализирует входное аудио и вычисляет оптимальный сдвиг для соответствия
    целевому типу голоса RVC модели.
    """
    
    # Целевые центры для типов моделей
    MALE_TARGET_CENTER = 155.0  # Hz, между баритоном и тенором
    FEMALE_TARGET_CENTER = 260.0  # Hz, между альтом и сопрано
    
    # Границы для определения пола голоса
    MALE_FEMALE_BOUNDARY = 200.0  # Hz
    
    # Пороги
    MIN_VOICED_RATIO = 0.1  # минимум 10% озвученных фреймов
    MIN_STABLE_FRAMES = 3  # минимум фреймов для "стабильного" участка
    OUTLIER_IQR_FACTOR = 1.5  # множитель IQR для определения выбросов
    
    # Ограничения сдвига
    MAX_SHIFT_SEMITONES = 12  # ±1 октава максимум
    
    def __init__(self):
        self.male_types = [VoiceType.BASS, VoiceType.BARITONE, VoiceType.TENOR]
        self.female_types = [VoiceType.ALTO, VoiceType.SOPRANO]
    
    def analyze_f0(self, f0: np.ndarray) -> VoiceAnalysis:
        """
        Анализирует массив F0 и возвращает характеристики голоса.
        
        Args:
            f0: Массив значений F0 (Hz), 0 = unvoiced
            
        Returns:
            VoiceAnalysis с характеристиками голоса
        """
        total_frames = len(f0)
        
        # Отделяем озвученные фреймы
        voiced_mask = f0 > 0
        f0_voiced = f0[voiced_mask]
        voiced_frames = len(f0_voiced)
        
        if voiced_frames == 0:
            # Нет озвученных фреймов
            return VoiceAnalysis(
                f0_median=0, f0_weighted_median=0, f0_mean=0, f0_std=0,
                f0_min=0, f0_max=0, f0_percentile_10=0, f0_percentile_90=0,
                detected_type=VoiceType.BARITONE, confidence=0,
                voiced_ratio=0, total_frames=total_frames, voiced_frames=0
            )
        
        voiced_ratio = voiced_frames / total_frames
        
        # Удаляем выбросы методом IQR
        f0_filtered = self._remove_outliers_iqr(f0_voiced)
        
        if len(f0_filtered) < 10:
            # Слишком мало данных после фильтрации, используем исходные
            f0_filtered = f0_voiced
        
        # Базовые статистики
        f0_median = float(np.median(f0_filtered))
        f0_mean = float(np.mean(f0_filtered))
        f0_std = float(np.std(f0_filtered))
        f0_min = float(np.min(f0_filtered))
        f0_max = float(np.max(f0_filtered))
        f0_p10 = float(np.percentile(f0_filtered, 10))
        f0_p90 = float(np.percentile(f0_filtered, 90))
        
        # Weighted median по длительности стабильных участков
        f0_weighted = self._compute_weighted_median(f0, voiced_mask)
        
        # Определяем тип голоса
        detected_type, confidence = self._detect_voice_type(f0_filtered, f0_weighted)
        
        return VoiceAnalysis(
            f0_median=f0_median,
            f0_weighted_median=f0_weighted,
            f0_mean=f0_mean,
            f0_std=f0_std,
            f0_min=f0_min,
            f0_max=f0_max,
            f0_percentile_10=f0_p10,
            f0_percentile_90=f0_p90,
            detected_type=detected_type,
            confidence=confidence,
            voiced_ratio=voiced_ratio,
            total_frames=total_frames,
            voiced_frames=voiced_frames
        )
    
    def _remove_outliers_iqr(self, data: np.ndarray) -> np.ndarray:
        """Удаляет выбросы методом межквартильного размаха (IQR)."""
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - self.OUTLIER_IQR_FACTOR * iqr
        upper_bound = q3 + self.OUTLIER_IQR_FACTOR * iqr
        
        return data[(data >= lower_bound) & (data <= upper_bound)]
    
    def _compute_weighted_median(self, f0: np.ndarray, voiced_mask: np.ndarray) -> float:
        """
        Вычисляет взвешенную медиану F0, где вес = длительность стабильного участка.
        
        Длинные ноты имеют больший вес, чем короткие переходные звуки.
        """
        if not np.any(voiced_mask):
            return 0.0
        
        # Находим непрерывные озвученные сегменты
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
        
        # Собираем значения F0 и их веса (длительность сегмента)
        values = []
        weights = []
        
        for start, end in segments:
            segment_f0 = f0[start:end]
            segment_length = end - start
            
            # Для стабильных сегментов берём медиану
            if segment_length >= self.MIN_STABLE_FRAMES:
                segment_median = np.median(segment_f0)
                values.append(segment_median)
                weights.append(segment_length)
        
        if not values:
            # Нет стабильных сегментов, используем обычную медиану
            return float(np.median(f0[voiced_mask]))
        
        # Взвешенная медиана
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
        """
        Определяет тип голоса по распределению F0.
        
        Returns:
            (VoiceType, confidence) где confidence от 0 до 1
        """
        # Используем взвешенную медиану как основной показатель
        center_f0 = f0_weighted if f0_weighted > 0 else np.median(f0_filtered)
        
        # Находим ближайший тип голоса
        best_type = VoiceType.BARITONE
        min_distance = float('inf')
        
        for voice_type in VoiceType:
            distance = voice_type.distance_to(center_f0)
            if distance < min_distance:
                min_distance = distance
                best_type = voice_type
        
        # Уверенность на основе:
        # 1. Попадания в диапазон
        # 2. Близости к центру
        # 3. Стабильности F0 (низкий std = высокая уверенность)
        
        in_range = best_type.contains(center_f0)
        distance_factor = max(0, 1 - min_distance / 6)  # 6 полутонов = низкая уверенность
        
        f0_std = np.std(f0_filtered)
        f0_mean = np.mean(f0_filtered)
        stability_factor = max(0, 1 - (f0_std / f0_mean) * 2) if f0_mean > 0 else 0
        
        confidence = (0.5 if in_range else 0.2) * 0.4 + distance_factor * 0.4 + stability_factor * 0.2
        
        return best_type, min(1.0, max(0.0, confidence))
    
    def calculate_pitch_shift(
        self,
        f0: np.ndarray,
        model_type: ModelVoiceType = ModelVoiceType.AUTO,
        custom_target_f0: Optional[float] = None
    ) -> AutoPitchResult:
        """
        Вычисляет оптимальный сдвиг высоты тона.
        
        Args:
            f0: Массив значений F0 (Hz)
            model_type: Тип голоса модели (male/female/auto)
            custom_target_f0: Пользовательская целевая частота (переопределяет model_type)
            
        Returns:
            AutoPitchResult с рекомендуемым сдвигом и анализом
        """
        # Анализируем вход
        analysis = self.analyze_f0(f0)
        
        # Проверяем достаточность данных
        if analysis.voiced_ratio < self.MIN_VOICED_RATIO:
            return AutoPitchResult(
                pitch_shift=0,
                input_analysis=analysis,
                target_f0=0,
                reasoning=f"Недостаточно озвученных фреймов ({analysis.voiced_ratio:.1%}), сдвиг не применяется"
            )
        
        # Определяем "центр" входного голоса
        input_center = analysis.f0_weighted_median
        if input_center <= 0:
            input_center = analysis.f0_median
        
        if input_center <= 0:
            return AutoPitchResult(
                pitch_shift=0,
                input_analysis=analysis,
                target_f0=0,
                reasoning="Не удалось определить центральную частоту входа"
            )
        
        # Определяем целевую частоту
        if custom_target_f0 is not None and custom_target_f0 > 0:
            target_f0 = custom_target_f0
            reasoning_target = f"пользовательская цель {target_f0:.1f} Hz"
        elif model_type == ModelVoiceType.MALE:
            target_f0 = self.MALE_TARGET_CENTER
            reasoning_target = f"мужская модель (цель {target_f0:.1f} Hz)"
        elif model_type == ModelVoiceType.FEMALE:
            target_f0 = self.FEMALE_TARGET_CENTER
            reasoning_target = f"женская модель (цель {target_f0:.1f} Hz)"
        else:  # AUTO
            target_f0 = self._determine_auto_target(input_center, analysis)
            reasoning_target = f"авто-определение (цель {target_f0:.1f} Hz)"
        
        # Вычисляем сдвиг
        if target_f0 <= 0 or input_center <= 0:
            pitch_shift = 0
        else:
            raw_shift = 12 * np.log2(target_f0 / input_center)
            pitch_shift = int(np.round(np.clip(raw_shift, -self.MAX_SHIFT_SEMITONES, self.MAX_SHIFT_SEMITONES)))
        
        reasoning = (
            f"Вход: {analysis.detected_type.label} ({input_center:.1f} Hz), "
            f"{reasoning_target}, сдвиг: {pitch_shift:+d} полутонов"
        )
        
        return AutoPitchResult(
            pitch_shift=pitch_shift,
            input_analysis=analysis,
            target_f0=target_f0,
            reasoning=reasoning
        )
    
    def _determine_auto_target(self, input_center: float, analysis: VoiceAnalysis) -> float:
        """
        Автоматически определяет целевую частоту на основе входа.
        
        Логика:
        - Если вход явно мужской → держим в мужском диапазоне
        - Если вход явно женский → держим в женском диапазоне  
        - Если между → минимальный сдвиг к ближайшему "стабильному" диапазону
        """
        # Определяем, мужской или женский голос на входе
        is_clearly_male = input_center < self.MALE_FEMALE_BOUNDARY * 0.85  # < 170 Hz
        is_clearly_female = input_center > self.MALE_FEMALE_BOUNDARY * 1.15  # > 230 Hz
        
        if is_clearly_male:
            # Мужской голос — предполагаем мужскую модель
            return self.MALE_TARGET_CENTER
        elif is_clearly_female:
            # Женский голос — предполагаем женскую модель
            return self.FEMALE_TARGET_CENTER
        else:
            # Неопределённый диапазон (170-230 Hz)
            # Используем минимальный сдвиг — смещаем к ближайшему центру
            dist_to_male = abs(input_center - self.MALE_TARGET_CENTER)
            dist_to_female = abs(input_center - self.FEMALE_TARGET_CENTER)
            
            if dist_to_male <= dist_to_female:
                return self.MALE_TARGET_CENTER
            else:
                return self.FEMALE_TARGET_CENTER


# Глобальный экземпляр для удобства
_autopitch_instance: Optional[AutoPitch] = None


def get_autopitch() -> AutoPitch:
    """Возвращает глобальный экземпляр AutoPitch."""
    global _autopitch_instance
    if _autopitch_instance is None:
        _autopitch_instance = AutoPitch()
    return _autopitch_instance


def calculate_pitch_shift(
    f0: np.ndarray,
    model_type: str = "auto",
    custom_target_f0: Optional[float] = None
) -> int:
    """
    Удобная функция для вычисления сдвига высоты тона.
    
    Args:
        f0: Массив значений F0 (Hz)
        model_type: "male", "female" или "auto"
        custom_target_f0: Пользовательская целевая частота
        
    Returns:
        Сдвиг в полутонах (int)
    """
    autopitch = get_autopitch()
    
    # Преобразуем строку в enum
    type_map = {
        "male": ModelVoiceType.MALE,
        "female": ModelVoiceType.FEMALE,
        "auto": ModelVoiceType.AUTO,
    }
    model_type_enum = type_map.get(model_type.lower(), ModelVoiceType.AUTO)
    
    result = autopitch.calculate_pitch_shift(f0, model_type_enum, custom_target_f0)
    return result.pitch_shift


# Для обратной совместимости со старым API
def calc_pitch_shift(f0: np.ndarray, target_f0: float = 155.0, limit_f0: int = 12) -> int:
    """
    Обратно совместимая функция.
    
    DEPRECATED: Используйте calculate_pitch_shift() вместо этой функции.
    """
    # Старая логика для совместимости
    autopitch = get_autopitch()
    analysis = autopitch.analyze_f0(f0)
    
    input_center = analysis.f0_weighted_median
    if input_center <= 0:
        input_center = analysis.f0_median
    if input_center <= 0:
        return 0
    
    raw_shift = 12 * np.log2(target_f0 / input_center)
    return int(np.round(np.clip(raw_shift, -limit_f0, limit_f0)))
