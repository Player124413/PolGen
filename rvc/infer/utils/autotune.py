import numpy as np
from typing import List, Dict


class AutoTune:
    """Класс для выполнения автотюна на аудиосигнале."""

    SCALE_INTERVALS: Dict[str, List[int]] = {
        # Базовые
        "chromatic": list(range(12)),  # Все 12 нот (полутонов)
        "major": [0, 2, 4, 5, 7, 9, 11],  # Мажорная гамма (Ionian)
        "minor": [0, 2, 3, 5, 7, 8, 10],  # Минорная гамма (Aeolian)
        # Модальные
        "dorian": [0, 2, 3, 5, 7, 9, 10],  # Дорийский лад
        "phrygian": [0, 1, 3, 5, 7, 8, 10],  # Фригийский лад
        "lydian": [0, 2, 4, 6, 7, 9, 11],  # Лидийский лад
        "mixolydian": [0, 2, 4, 5, 7, 9, 10],  # Миксолидийский лад
        # Миноры
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],  # Гармонический минор
        "melodic_minor": [0, 2, 3, 5, 7, 9, 11],  # Мелодический минор
        # Пентатоники и блюз
        "pentatonic_major": [0, 2, 4, 7, 9],  # Мажорная пентатоника
        "pentatonic_minor": [0, 3, 5, 7, 10],  # Минорная пентатоника
        "blues": [0, 3, 5, 6, 7, 10],  # Блюзовая гамма
    }

    TONIC_SEMITONES: Dict[str, int] = {
        "C": 0,
        "C#": 1,
        "Db": 1,
        "D": 2,
        "D#": 3,
        "Eb": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "Gb": 6,
        "G": 7,
        "G#": 8,
        "Ab": 8,
        "A": 9,
        "A#": 10,
        "Bb": 10,
        "B": 11,
    }

    @staticmethod
    def _freq_to_midi(f: np.ndarray, a4: float) -> np.ndarray:
        """Конвертирует частоту (Гц) в MIDI-ноту."""
        return 69 + 12 * np.log2(f / a4)

    @staticmethod
    def _midi_to_freq(m: np.ndarray, a4: float) -> np.ndarray:
        """Конвертирует MIDI-ноту в частоту (Гц)."""
        return a4 * 2**((m - 69) / 12)

    def __init__(self, a4_frequency: float = 440.0, scale: str = "chromatic", tonic: str = "C"):
        """Инициализирует класс."""
        self.a4_frequency = a4_frequency
        self.target_midi_notes = np.array([])
        self.set_scale(scale, tonic)

    def set_scale(self, scale: str, tonic: str):
        """
        Устанавливает рабочую тональность (гамму и тонику).

        Args:
            scale (str): Название гаммы.
            tonic (str): Название тоники.
        """
        if scale not in self.SCALE_INTERVALS:
            raise ValueError(f"Неизвестная гамма: '{scale}'. Доступные гаммы: {list(self.SCALE_INTERVALS.keys())}")
        if tonic not in self.TONIC_SEMITONES:
            raise ValueError(f"Неизвестная тоника: '{tonic}'. Доступные тоники: {list(self.TONIC_SEMITONES.keys())}")

        intervals = self.SCALE_INTERVALS[scale]
        tonic_semitone = self.TONIC_SEMITONES[tonic]

        allowed_notes = []
        for midi_note in range(128):  # Полный MIDI-диапазон
            if (midi_note - tonic_semitone) % 12 in intervals:
                allowed_notes.append(float(midi_note))

        self.target_midi_notes = np.array(allowed_notes)

    def apply(self, f0: np.ndarray, strength: float = 1.0, retune_speed: float = 0.5, tolerance_cents: int = 20) -> np.ndarray:
        """
        Применяет автотюн к массиву основной частоты (F0).

        Args:
            f0 (np.ndarray): Входной массив F0.
            strength (float): Сила коррекции (0.0 - нет, 1.0 - полная).
            retune_speed (float): Скорость коррекции (0.0 - медленно, 1.0 - мгновенно).
            tolerance_cents (int): Зона в центах, внутри которой коррекция не применяется.

        Returns:
            np.ndarray: Массив F0 после применения автотюна.
        """
        if strength == 0 or not self.target_midi_notes.any():
            return f0

        output_f0 = f0.copy()
        is_voiced = f0 > 0
        if not np.any(is_voiced):
            return f0

        # Работаем только с "вокализованными" участками в MIDI-шкале
        voiced_f0 = f0[is_voiced]
        voiced_midi = self._freq_to_midi(voiced_f0, self.a4_frequency)

        # Находим ближайшую целевую ноту для каждого сэмпла
        diffs = np.abs(voiced_midi[:, np.newaxis] - self.target_midi_notes)
        closest_indices = np.argmin(diffs, axis=1)
        target_midi = self.target_midi_notes[closest_indices]

        # Применяем "очеловечивание" (tolerance)
        cents_diff = (voiced_midi - target_midi) * 100
        # Не трогаем ноты, которые уже достаточно точны
        target_midi[np.abs(cents_diff) < tolerance_cents] = voiced_midi[np.abs(cents_diff) < tolerance_cents]

        # Рассчитываем конечную цель с учетом силы (strength)
        final_target_midi = voiced_midi + (target_midi - voiced_midi) * strength

        # Применяем плавную коррекцию (retune speed)
        smoothed_midi = voiced_midi.copy()
        # Коэффициент сглаживания должен быть в пределах (0, 1] для стабильности
        safe_retune_speed = np.clip(retune_speed, 1e-9, 1.0)

        # Итерируем для применения экспоненциального сглаживания
        for i in range(1, len(voiced_midi)):
            smoothed_midi[i] = (1 - safe_retune_speed) * smoothed_midi[i-1] + safe_retune_speed * final_target_midi[i]

        # Конвертируем обратно в герцы и обновляем выходной массив
        output_f0[is_voiced] = self._midi_to_freq(smoothed_midi, self.a4_frequency)
        return output_f0
