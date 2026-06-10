"""ImageFrequencyCheckerForHandmaidsVsAI

画像の空間周波数帯域を 3 段階のカットオフ（既定 50/60/70）で抽出する
Python ツール。`djmannion/img_freq_web` のアルゴリズム（FFT → 円形
カットオフフィルタ → 逆 FFT）を Python へ再実装したもの。

Public API:
    apply_cutoff(image, cutoff_percent, mode="highpass")
    process_image(input_path, output_dir, cutoffs=(50, 60, 70), ...)
    serve(host="127.0.0.1", port=4165)
"""

from .filter import apply_cutoff, build_circular_mask
from .compose import process_image, make_comparison_strip

__all__ = [
    "apply_cutoff",
    "build_circular_mask",
    "process_image",
    "make_comparison_strip",
    "serve",
]

__version__ = "0.1.0"


def __getattr__(name: str):
    # `serve` は HTTP サーバ依存を含むため遅延ロード。
    if name == "serve":
        from .server import serve as _serve
        return _serve
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
