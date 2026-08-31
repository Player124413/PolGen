"""Чистый numpy-ридер FAISS-индексов RVC.

На Android/TermUX пакет faiss-cpu недоступен (нет совместимых сборок), но
голосовые модели RVC поставляются с .index-файлами FAISS. Этот модуль читает
наиболее распространённые форматы индексов и выполняет поиск силами numpy:

  * IndexFlatL2 / IndexFlatIP  (fourcc: "IxFl", "IxF2", "IxFI")
  * IndexIVFFlat               (fourcc: "IwFl" + ArrayInvertedLists "ilar")

Формат сериализации FAISS стабилен с версии 1.7 — именно ею (и новее)
записываются индексы при обучении RVC-моделей.

Если установлен настоящий faiss — используется он (API совместим).
"""

import os
import struct
import threading

import numpy as np

try:
    import faiss  # type: ignore

    FAISS_AVAILABLE = True
except Exception:  # pragma: no cover - среда без faiss (Android и т.п.)
    faiss = None
    FAISS_AVAILABLE = False

# Кэш открытых индексов: путь -> (метаданные, объект)
_INDEX_CACHE: dict = {}
_INDEX_CACHE_LOCK = threading.Lock()
_INDEX_CACHE_MAX = 4

_METRIC_IP = 0
_METRIC_L2 = 1


class FaissNumpyError(Exception):
    """Неподдерживаемый или повреждённый файл индекса."""


class _Reader:
    """Последовательное чтение little-endian полей из файла."""

    def __init__(self, path: str):
        self._f = open(path, "rb")

    def u32(self) -> int:
        return struct.unpack("<I", self._f.read(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self._f.read(4))[0]

    def i64(self) -> int:
        return struct.unpack("<q", self._f.read(8))[0]

    def u8(self) -> int:
        return self._f.read(1)[0]

    def f32_vector(self) -> np.ndarray:
        n = self.i64()
        if n < 0 or n > (1 << 40):
            raise FaissNumpyError(f"Некорректная длина вектора: {n}")
        return np.frombuffer(self._f.read(n * 4), dtype="<f4")

    def i64_vector(self) -> np.ndarray:
        n = self.i64()
        if n < 0 or n > (1 << 40):
            raise FaissNumpyError(f"Некорректная длина вектора: {n}")
        return np.frombuffer(self._f.read(n * 8), dtype="<i8")

    def raw(self, n: int) -> bytes:
        return self._f.read(n)

    def close(self):
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _fourcc(value: int) -> str:
    return "".join(chr((value >> (8 * i)) & 0xFF) for i in range(4))


class NumpyFlatIndex:
    """IndexFlat (L2 или IP), векторы хранятся одним непрерывным массивом."""

    def __init__(self, vectors: np.ndarray, metric_type: int):
        self._vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        self.metric_type = metric_type
        self.ntotal = int(self._vectors.shape[0])
        self.d = int(self._vectors.shape[1]) if self._vectors.ndim == 2 else 0

    def search(self, x: np.ndarray, k: int):
        x = np.ascontiguousarray(x, dtype=np.float32)
        n = x.shape[0]
        if self.metric_type == _METRIC_L2:
            # Квадратичное евклидово расстояние (как в faiss)
            xx = (x * x).sum(axis=1, keepdims=True)
            cc = (self._vectors * self._vectors).sum(axis=1)[np.newaxis, :]
            dist = xx + cc - 2.0 * x @ self._vectors.T
            dist = np.maximum(dist, 0.0)
            best = np.argsort(dist, axis=1, kind="stable")[:, :k]
        else:
            sim = x @ self._vectors.T
            best = np.argsort(-sim, axis=1, kind="stable")[:, :k]

        rows = np.arange(n)[:, np.newaxis]
        scores = dist[rows, best] if self.metric_type == _METRIC_L2 else sim[rows, best]
        ids = best.astype(np.int64)

        # Дополнение, если векторов меньше k
        if self.ntotal < k:
            pad = k - self.ntotal
            scores = np.hstack([scores, np.full((n, pad), np.inf, dtype=np.float32)])
            ids = np.hstack([ids, np.full((n, pad), -1, dtype=np.int64)])
        return scores.astype(np.float32), ids

    def reconstruct_n(self, i0: int, ni: int) -> np.ndarray:
        return self._vectors[i0 : i0 + ni].copy()


class NumpyIVFFlatIndex:
    """IndexIVFFlat: центроиды (квантизатор IndexFlat) + инвертированные списки."""

    def __init__(self, d, metric_type, nprobe, centroids, codes, ids, list_sizes):
        self.d = int(d)
        self.metric_type = metric_type
        self.nprobe = max(1, int(nprobe))
        self.ntotal = int(ids.size)
        self._centroids = np.ascontiguousarray(centroids, dtype=np.float32).reshape(-1, self.d)
        if codes.size:
            self._codes = np.ascontiguousarray(codes, dtype=np.float32).reshape(-1, self.d)
        else:
            self._codes = np.zeros((0, self.d), dtype=np.float32)
        self._ids = np.ascontiguousarray(ids, dtype=np.int64)
        self._list_sizes = np.asarray(list_sizes, dtype=np.int64)
        self._list_offsets = np.concatenate([[0], np.cumsum(self._list_sizes)]).astype(np.int64)

        # Восстановление векторов по id (для reconstruct_n)
        order = np.argsort(self._ids, kind="stable")
        self._id_sorted = self._ids[order]
        self._by_id = self._codes[order]

    def _quantizer_assign(self, x: np.ndarray) -> np.ndarray:
        """Индексы nprobe ближайших центроидов для каждого запроса."""
        if self.metric_type == _METRIC_L2:
            xx = (x * x).sum(axis=1, keepdims=True)
            cc = (self._centroids * self._centroids).sum(axis=1)[np.newaxis, :]
            dist = xx + cc - 2.0 * x @ self._centroids.T
            dist = np.maximum(dist, 0.0)
            lists = np.argsort(dist, axis=1, kind="stable")[:, : self.nprobe]
        else:
            sim = x @ self._centroids.T
            lists = np.argsort(-sim, axis=1, kind="stable")[:, : self.nprobe]
        return lists

    def search(self, x: np.ndarray, k: int):
        x = np.ascontiguousarray(x, dtype=np.float32)
        n = x.shape[0]
        lists = self._quantizer_assign(x)

        scores = np.full((n, k), np.inf, dtype=np.float32)
        ids = np.full((n, k), -1, dtype=np.int64)

        for qi in range(n):
            cand_ids, cand_vecs = [], []
            for list_no in lists[qi]:
                s, e = self._list_offsets[list_no], self._list_offsets[list_no + 1]
                if e > s:
                    cand_ids.append(self._ids[s:e])
                    cand_vecs.append(self._codes[s:e])
            if not cand_ids:
                continue
            cid = np.concatenate(cand_ids)
            cvec = np.concatenate(cand_vecs)
            q = x[qi]
            if self.metric_type == _METRIC_L2:
                dvec = np.maximum((cvec * cvec).sum(axis=1) - 2.0 * (cvec @ q) + float((q * q).sum()), 0.0)
                order = np.argsort(dvec, kind="stable")[:k]
                m = min(k, order.size)
                scores[qi, :m] = dvec[order[:m]]
            else:
                svec = cvec @ q
                order = np.argsort(-svec, kind="stable")[:k]
                m = min(k, order.size)
                scores[qi, :m] = svec[order[:m]]
            ids[qi, :m] = cid[order[:m]]
        return scores, ids

    def reconstruct_n(self, i0: int, ni: int) -> np.ndarray:
        if i0 == 0 and ni == self.ntotal and np.array_equal(self._id_sorted, np.arange(self.ntotal)):
            return self._by_id.copy()  # быстрый путь: последовательные id
        pos = np.searchsorted(self._id_sorted, np.arange(i0, i0 + ni))
        if np.any(self._id_sorted[pos] != np.arange(i0, i0 + ni)):
            raise FaissNumpyError("reconstruct_n: id отсутствует в индексе")
        return self._by_id[pos].copy()


def _read_index_header(reader: _Reader):
    d = reader.i32()
    ntotal = reader.i64()
    reader.i64()  # dummy (1 << 20)
    reader.i64()  # dummy (1 << 20)
    reader.u8()  # is_trained
    metric_type = reader.i32()
    if metric_type > 1:
        reader.raw(4)  # metric_arg (float)
    return d, ntotal, metric_type


def _read_flat(reader: _Reader, code: str) -> NumpyFlatIndex:
    d, ntotal, _ = _read_index_header(reader)
    metric = _METRIC_IP if code == "IxFI" else _METRIC_L2
    vectors = reader.f32_vector()
    if vectors.size != ntotal * d:
        raise FaissNumpyError("Размер массива векторов не совпадает с заголовком")
    return NumpyFlatIndex(vectors.reshape(ntotal, d), metric)


def _read_quantizer(reader: _Reader) -> NumpyFlatIndex:
    """Читает вложенный индекс-квантизатор (ожидается IndexFlat*)."""
    code = _fourcc(reader.u32())
    if code not in ("IxFl", "IxF2", "IxFI"):
        raise FaissNumpyError(f"Неподдерживаемый тип квантизатора: {code!r}")
    return _read_flat(reader, code)


def _read_inverted_lists(reader: _Reader, d: int):
    code = _fourcc(reader.u32())
    if code != "ilar":
        raise FaissNumpyError(f"Неподдерживаемый формат инвертированных списков: {code!r}")
    nlist = reader.i64()
    code_size = reader.i64()
    if code_size != d * 4:
        raise FaissNumpyError(f"Ожидался Flat-код (code_size={d * 4}), получен {code_size}")
    list_type = _fourcc(reader.u32())

    if list_type == "full":
        sizes = reader.i64_vector()
        if sizes.size != nlist:
            raise FaissNumpyError("Размер массива sizes не совпадает с nlist")
    elif list_type == "sprs":
        pairs = reader.i64_vector().reshape(-1, 2)
        sizes = np.zeros(nlist, dtype=np.int64)
        sizes[pairs[:, 0]] = pairs[:, 1]
    else:
        raise FaissNumpyError(f"Неизвестный тип списков: {list_type!r}")

    total = int(sizes.sum())
    codes = np.empty((total, d), dtype=np.float32)
    ids = np.empty(total, dtype=np.int64)
    pos = 0
    for list_no in range(nlist):
        n = int(sizes[list_no])
        if n > 0:
            codes[pos : pos + n] = np.frombuffer(reader.raw(n * d * 4), dtype="<f4").reshape(n, d)
            ids[pos : pos + n] = np.frombuffer(reader.raw(n * 8), dtype="<i8")
            pos += n
    return codes, ids, sizes.tolist()


def _read_ivf_flat(reader: _Reader) -> NumpyIVFFlatIndex:
    d, ntotal, metric_type = _read_index_header(reader)
    reader.i64()  # nlist
    nprobe = reader.i64()

    quantizer = _read_quantizer(reader)

    # direct map: тип (int8) + массив int64 (+ пары для Hashtable)
    reader.u8()  # тип direct map (индексы RVC используют NoMap = 0)
    reader.i64_vector()  # массив direct map (пустой при NoMap)

    codes, ids, sizes = _read_inverted_lists(reader, d)
    if ids.size != ntotal:
        raise FaissNumpyError(f"ntotal ({ntotal}) не совпадает с числом id в списках ({ids.size})")

    return NumpyIVFFlatIndex(d, metric_type, nprobe, quantizer._vectors, codes, ids, sizes)


def read_index(path: str):
    """Читает .index файл. Возвращает объект с API faiss (search/ntotal/reconstruct_n)."""
    with _Reader(path) as reader:
        code = _fourcc(reader.u32())
        if code in ("IxFl", "IxF2", "IxFI"):
            return _read_flat(reader, code)
        if code == "IwFl":
            return _read_ivf_flat(reader)
        raise FaissNumpyError(f"Неподдерживаемый тип индекса: {code!r} (поддерживаются IndexFlat и IndexIVFFlat)")


def open_index(path: str):
    """Открывает индекс с кэшированием: настоящий faiss при наличии, иначе numpy.

    Возвращает объект с методами search(x, k) и reconstruct_n(i0, ni),
    либо None, если файл не существует.
    """
    if not path or not os.path.exists(path):
        return None

    stat = os.stat(path)
    key = os.path.abspath(path)
    entry = (stat.st_mtime_ns, stat.st_size)
    with _INDEX_CACHE_LOCK:
        cached = _INDEX_CACHE.get(key)
        if cached and cached[0] == entry:
            return cached[1]

    if FAISS_AVAILABLE:
        index = faiss.read_index(path)
    else:
        index = read_index(path)

    with _INDEX_CACHE_LOCK:
        _INDEX_CACHE[key] = (entry, index)
        while len(_INDEX_CACHE) > _INDEX_CACHE_MAX:
            _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
    return index


def clear_cache():
    with _INDEX_CACHE_LOCK:
        _INDEX_CACHE.clear()
