import os

import torch


def _detect_android() -> bool:
    """Определяет запуск в Android/Termux (или в proot-дистрибутиве на нём)."""
    if os.environ.get("POLGEN_FORCE_ANDROID") == "1":
        return True
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix or "termux" in prefix.lower():
        return True
    return os.path.exists("/system/build.prop")


def _total_ram_gb() -> float:
    """Объём оперативной памяти (ГБ)."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024**2
    except OSError:
        pass
    return 16.0  # консервативное значение по умолчанию (десктоп)


def _default_threads(is_android: bool, cpu_count: int) -> int:
    """Оптимальное число потоков torch для CPU-инференса.

    На телефонах (big.LITTLE) использование всех ядер, включая медленные
    «little», создаёт конкуренцию потоков и замедляет конволюции HiFi-GAN.
    Практика показывает: 4-6 потоков на производительных ядрах быстрее,
    чем все 8. Переопределяется переменной окружения POLGEN_THREADS.
    """
    if is_android:
        return max(2, min(6, cpu_count))
    return max(1, cpu_count)


class Config:
    """Конфигурация устройства и параметров инференса."""

    def __init__(self):
        # Определение устройства
        self.device = self._get_device()
        self.is_android = _detect_android()
        self.cpu_count = os.cpu_count() or 1
        self.total_ram_gb = _total_ram_gb()

        # Конфигурация параметров GPU
        self.gpu_name, self.gpu_mem = self._configure_gpu() if self.device == "cuda" else (None, None)

        # Тюнинг CPU: потоки и денормалы
        self.torch_threads = self._configure_threads()
        self._configure_cpu()

        # Установка параметров на основе памяти GPU или RAM телефона
        self.x_pad, self.x_query, self.x_center, self.x_max = self._get_device_params()

        # Сколько голосовых моделей держать в кэше (зависит от RAM)
        self.cache_max_models = int(os.environ.get("POLGEN_CACHE_MODELS", 2 if self.total_ram_gb >= 8 else 1))

        print(f"Используемое устройство:  {self.device}")
        if self.device == "cpu":
            details = [f"потоки: {self.torch_threads}", f"RAM: {self.total_ram_gb:.1f} ГБ"]
            if self.is_android:
                details.append("Android/Termux")
            print(f"Режим CPU ({', '.join(details)})")

    def _get_device(self):
        """Определяет доступное устройство (cuda, mps или cpu)."""
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _configure_gpu(self):
        """Возвращает имя и объем памяти GPU."""
        gpu_name = torch.cuda.get_device_name(self.device)
        total_memory_bytes = torch.cuda.get_device_properties(self.device).total_memory
        # Преобразуем байты в ГБ и округляем
        gpu_mem = round(total_memory_bytes / 1024**3)
        return gpu_name, gpu_mem

    def _configure_threads(self) -> int:
        """Настраивает пулы потоков PyTorch."""
        threads = int(os.environ.get("POLGEN_THREADS", 0)) or _default_threads(self.is_android, self.cpu_count)
        threads = max(1, min(threads, self.cpu_count))
        torch.set_num_threads(threads)
        try:
            # inter-op потоки не нужны (последовательный конвейер) — экономим ресурсы
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass  # уже инициализировано
        return threads

    def _configure_cpu(self):
        """Микрооптимизации CPU-инференса."""
        if os.environ.get("POLGEN_NO_FLUSH_DENORMAL") != "1":
            # Денормальные float (близкие к нулю) обрабатываются микрокодом в
            # сотни раз медленнее. Обнуляем их аппаратно: скорость +10-13%,
            # влияние на качество пренебрежимо (значения меньше 1e-38).
            torch.set_flush_denormal(True)

    @property
    def torch_compile_enabled(self) -> bool:
        """Опциональная JIT-компиляция конвейера (экспериментально, ~+10% на CPU)."""
        return os.environ.get("POLGEN_TORCH_COMPILE", "0") == "1" and self.device == "cpu"

    def _get_device_params(self):
        """Возвращает параметры, специфичные для устройства, в зависимости от памяти.

        Размер чанка (x_center/x_max, секунды) определяет пиковую память:
        активации HiFi-GAN растут линейно с длиной чанка (~120 МБ/с аудио).
        На телефонах чанки уменьшаются, чтобы конвертация длинных треков
        не убивалась системой; на десктопе остаются максимальными.
        """
        if self.device == "cuda" and self.gpu_mem is not None and self.gpu_mem <= 4:
            # Параметры для GPU с низкой памятью
            return (1, 5, 30, 32)
        if self.device == "cpu":
            # Ручное переопределение размера чанка (секунды)
            chunk = int(os.environ.get("POLGEN_CHUNK_SEC", 0))
            if chunk > 0:
                return (1, max(2, chunk // 3), chunk, chunk + 2)
            # На телефонах/слабых машинах уменьшаем максимальный чанк,
            # чтобы пик памяти при обработке длинных треков был ниже
            if self.total_ram_gb <= 4:
                return (1, 3, 6, 8)
            if self.total_ram_gb <= 6:
                return (1, 4, 8, 10)
            if self.total_ram_gb <= 8:
                return (1, 5, 15, 18)
        # Параметры по умолчанию
        return (1, 6, 38, 41)
