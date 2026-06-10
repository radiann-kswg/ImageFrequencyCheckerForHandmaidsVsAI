"""ImageFrequencyCheckerForHandmaidsVsAI

画像の空間周波数帯域を 3 段階のカットオフ（既定 50/60/70）で抽出する
Python ツール。`djmannion/img_freq_web` のアルゴリズム（FFT → 円形
カットオフフィルタ → 逆 FFT）を Python へ再実装したもの。

Public API:
    apply_cutoff(image, cutoff_percent, mode="highpass")
    process_image(input_path, output_dir, cutoffs=(50, 60, 70), ...)
"""

from .filter import apply_cutoff, build_circular_mask
from .compose import process_image, make_comparison_strip

__all__ = [
    "apply_cutoff",
    "build_circular_mask",
    "process_image",
    "make_comparison_strip",
]

__version__ = "0.1.0"
