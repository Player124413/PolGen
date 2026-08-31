import os
import shutil
import subprocess

import numpy as np


def _find_ffmpeg():
    """Ищет бинарник ffmpeg в PATH (на Android/Termux он ставится через pkg)."""
    return shutil.which("ffmpeg")


# ─── Android: декодирование через MediaCodec (без ffmpeg) ─────────────

def _on_android():
    """True, если работаем внутри APK (Chaquopy) — там есть мост в Java."""
    try:
        import java  # noqa: F401  — модуль Chaquopy

        return True
    except ImportError:
        return False


def _decode_android_pcm(file):
    """Декодирует аудио (mp3/m4a/aac/ogg/flac/wav) через системные
    кодеки Android. Возвращает (pcm_float32_mono, sample_rate).

    Работает только под Chaquopy (python внутри APK)."""
    from java import jclass, jarray, jbyte, jint

    MediaExtractor = jclass("android.media.MediaExtractor")
    MediaCodec = jclass("android.media.MediaCodec")
    MediaFormat = jclass("android.media.MediaFormat")

    extractor = MediaExtractor()
    try:
        extractor.setDataSource(file)
        mime = None
        track_format = None
        for i in range(extractor.getTrackCount()):
            fmt = extractor.getTrackFormat(i)
            m = fmt.getString(MediaFormat.KEY_MIME)
            if m is not None and m.startsWith("audio/"):
                extractor.selectTrack(i)
                mime, track_format = m, fmt
                break
        if mime is None:
            raise RuntimeError("аудиодорожка не найдена")

        codec = MediaCodec.createDecoderByType(mime)
        try:
            codec.configure(track_format, None, None, 0)
            codec.start()

            info = MediaCodec.BufferInfo()
            chunks = []
            out_rate = track_format.getInteger(MediaFormat.KEY_SAMPLE_RATE)
            channels = track_format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)

            input_done = False
            output_done = False
            while not output_done:
                if not input_done:
                    idx = codec.dequeueInputBuffer(jint(10000))
                    if idx >= 0:
                        buf = codec.getInputBuffer(idx)
                        n = extractor.readSampleData(buf, 0)
                        if n < 0:
                            codec.queueInputBuffer(
                                idx, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM
                            )
                            input_done = True
                        else:
                            codec.queueInputBuffer(idx, 0, n, extractor.getSampleTime(), 0)
                            extractor.advance()

                idx = codec.dequeueOutputBuffer(info, jint(10000))
                if idx >= 0:
                    size = info.size
                    if size > 0:
                        buf = codec.getOutputBuffer(idx)
                        buf.position(info.offset)
                        # копируем ByteBuffer → java byte[] → bytes (прямой memory-copy)
                        jarr = jarray(jbyte)(size)
                        buf.get(jarr, 0, size)
                        chunks.append(bytes(jarr))
                    codec.releaseOutputBuffer(idx, False)
                elif idx == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED:
                    new_fmt = codec.getOutputFormat()
                    out_rate = new_fmt.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                    channels = new_fmt.getInteger(MediaFormat.KEY_CHANNEL_COUNT)

            pcm = np.frombuffer(b"".join(chunks), dtype=np.int16)
            if channels > 1:
                pcm = pcm.reshape(-1, channels).mean(axis=1)
            audio = pcm.astype(np.float32) / 32768.0
            return audio, out_rate
        finally:
            try:
                codec.stop()
            except Exception:  # noqa: BLE001
                pass
            codec.release()
    finally:
        extractor.release()


def _resample_linear(audio, src_rate, dst_rate):
    """Простая линейная передискретизация (для голоса более чем достаточно)."""
    if src_rate == dst_rate or len(audio) == 0:
        return audio
    n = int(len(audio) * dst_rate / src_rate)
    x_src = np.linspace(0.0, 1.0, len(audio), endpoint=False)
    x_dst = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.interp(x_dst, x_src, audio).astype(np.float32)


def _load_audio_android(file, sample_rate):
    """Путь загрузки внутри APK: MediaCodec + numpy-ресемпл."""
    audio, rate = _decode_android_pcm(file)
    return _resample_linear(audio, rate, sample_rate)


def _load_audio_wave(file, sample_rate):
    """WAV через стандартную библиотеку (последний резерв)."""
    import wave

    with wave.open(file, "rb") as w:
        rate = w.getframerate()
        channels = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width == 2:
        pcm = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        pcm = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise RuntimeError(f"неподдерживаемая разрядность WAV: {width * 8} бит")
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    return _resample_linear(pcm, rate, sample_rate)


def _save_audio_wave(audio_data, sample_rate, output_path, stereo=False):
    """Запись 16-битного WAV стандартной библиотекой (без ffmpeg)."""
    import wave

    audio = np.clip(audio_data, -1.0, 1.0)
    pcm = (audio * 32767).astype("<i2")
    channels = 2 if stereo else 1
    if stereo:
        pcm = np.repeat(pcm.reshape(-1, 1), 2, axis=1).reshape(-1)
    with wave.open(output_path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return output_path


def _load_audio_ffmpeg(file: str, sample_rate: int) -> np.ndarray:
    """Декодирует аудио любого формата через ffmpeg-пайп (моно, f32le, нужная SR).

    Быстрее и универсальнее связки soundfile+librosa: понимает mp3/m4a/ogg/
    opus/flac/wav и даже видеофайлы, не требует C-расширений.
    """
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-i",
        file,
        "-vn",  # игнорировать видео-дорожки
        "-ac",
        "1",  # моно
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    audio = np.frombuffer(result.stdout, dtype=np.float32)
    return audio.copy()  # отвязываем от буфера результата


def _load_audio_soundfile(file: str, sample_rate: int) -> np.ndarray:
    """Резервный путь через soundfile + librosa (если ffmpeg не найден)."""
    import librosa  # noqa: PLC0415
    import soundfile as sf  # noqa: PLC0415

    audio, sr = sf.read(file)
    if len(audio.shape) > 1:
        audio = librosa.to_mono(audio.T)
    if sr != sample_rate:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=sample_rate)
    return audio.flatten()


def load_audio(file, sample_rate):
    try:
        file = file.strip(" ").strip('"').strip("\n").strip('"').strip(" ")
        if not os.path.exists(file):
            raise FileNotFoundError(f"Файл не найден: {file}")

        if _find_ffmpeg() is not None:
            try:
                return _load_audio_ffmpeg(file, sample_rate)
            except subprocess.CalledProcessError:
                # ffmpeg не смог декодировать — пробуем резервный путь
                pass

        # Внутри APK (Chaquopy): системные кодеки Android
        if _on_android():
            try:
                return _load_audio_android(file, sample_rate)
            except Exception:
                # если системный декодер не справился — ниже пробуем WAV напрямую
                pass

        # WAV умеет читать стандартная библиотека
        if file.lower().endswith((".wav", ".wave")):
            return _load_audio_wave(file, sample_rate)

        return _load_audio_soundfile(file, sample_rate)
    except Exception as error:
        raise RuntimeError(f"Произошла ошибка при загрузке аудио: {error}") from error


def save_audio(audio_data, sample_rate, output_path, output_format="wav", stereo=False):
    """Сохраняет аудио используя прямой вызов FFmpeg через pipe.

    Без ffmpeg (автономный APK) — WAV стандартной библиотекой; если
    запрошен другой формат, файл сохраняется как .wav."""
    if _find_ffmpeg() is None:
        if not output_path.lower().endswith(".wav"):
            output_path = os.path.splitext(output_path)[0] + ".wav"
        return _save_audio_wave(audio_data, sample_rate, output_path, stereo)

    # Конвертируем в int16 или float32 в зависимости от формата
    if output_format in ["wav", "flac"]:
        # Для lossless форматов используем 24-bit
        audio_data = np.clip(audio_data, -1.0, 1.0)
        # Конвертируем в 32-bit float для максимальной точности
        audio_bytes = audio_data.astype(np.float32).tobytes()
        input_format = "f32le"
    else:
        # Для lossy форматов используем 16-bit
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        input_format = "s16le"

    channels = 2 if stereo else 1

    # Базовые параметры FFmpeg
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",  # Перезаписывать выходной файл
        "-f",
        input_format,  # Формат входных данных
        "-ar",
        str(sample_rate),  # Частота дискретизации
        "-ac",
        "1",  # Входные каналы (всегда моно из RVC)
        "-i",
        "pipe:0",  # Читать из stdin
        "-ac",
        str(channels),  # Выходные каналы
    ]

    # Настройки качества для каждого формата
    format_settings = {
        "wav": [
            "-c:a",
            "pcm_f32le",  # 32-bit float PCM для максимального качества
            "-sample_fmt",
            "flt",
        ],
        "flac": [
            "-c:a",
            "flac",
            "-compression_level",
            "12",  # Максимальное сжатие (без потерь)
            "-sample_fmt",
            "s32",  # 32-bit для максимального качества
        ],
        "mp3": [
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",  # Максимальный битрейт
            "-q:a",
            "0",  # Наилучшее качество
        ],
        "ogg": [
            "-c:a",
            "libvorbis",
            "-q:a",
            "10",  # Максимальное качество (500kbps+)
        ],
        "m4a": [
            "-c:a",
            "aac",
            "-b:a",
            "320k",  # Максимальный битрейт
            "-q:a",
            "2",  # Максимальное качество
            "-aac_coder",
            "twoloop",  # Лучший кодировщик
            "-profile:a",
            "aac_low",
        ],
    }

    if output_format in format_settings:
        cmd.extend(format_settings[output_format])
    else:
        raise ValueError(f"Неподдерживаемый формат: {output_format}")

    # Добавляем выходной файл
    cmd.append(output_path)

    # Запускаем FFmpeg
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # Подавляем вывод FFmpeg для чистоты
    )

    try:
        stdout, stderr = process.communicate(input=audio_bytes, timeout=300)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("FFmpeg timeout: операция заняла слишком много времени")

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg завершился с ошибкой (код: {process.returncode})")

    return output_path
