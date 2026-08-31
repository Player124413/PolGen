"""Бенчмарк конвейера RVC: холодный и тёплый запуск, пиковая память."""
import os
import resource
import sys
import time

sys.path.insert(0, os.getcwd())


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def run_once(tag):
    import gc

    from rvc.infer.infer import rvc_infer

    gc.collect()
    t0 = time.perf_counter()
    rvc_infer(
        rvc_model="test_voice",
        input_path="test_audio.wav",
        f0_method="rmvpe",
        index_rate=0.25,
        protect=0.4,
        output_format="wav",
    )
    dt = time.perf_counter() - t0
    print(f"[{tag}] {dt:.2f} s | peak RSS {rss_mb():.0f} MB", flush=True)
    return dt


if __name__ == "__main__":
    print(f"Python {sys.version.split()[0]} | torch threads env: OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS')}")
    cold = run_once("cold")
    warm = run_once("warm")
    print(f"\nTOTAL: cold={cold:.2f}s warm={warm:.2f}s peak={rss_mb():.0f}MB")
