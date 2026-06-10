"""空間周波数フィルタの実装。

元ツール `djmannion/img_freq_web` と同じ考え方:
  1. 入力画像を中心化 (mean subtract) しチャネルごとに 2D FFT。
  2. fftshift で DC 成分を中央に。
  3. 中心からの半径ベースで円形マスク（low-pass / high-pass / band-pass）。
  4. ifftshift → 2D iFFT → 実部を取り出し、mean を戻す。
  5. [0, 255] にクリップして uint8 に。

カットオフは「Nyquist 半径に対する％ (0–100)」で指定する。
たとえば 50 はナイキスト半径の 50% より内側を切り捨てる（high-pass の場合）。
"""

from __future__ import annotations

from typing import Literal

import numpy as np

FilterMode = Literal["highpass", "lowpass", "bandpass"]


def build_circular_mask(
    shape: tuple[int, int],
    cutoff_percent: float,
    mode: FilterMode = "highpass",
    high_cutoff_percent: float | None = None,
    soft_edge_px: float = 0.0,
) -> np.ndarray:
    """周波数領域 (fftshift 済) で使う円形マスクを作る。

    Args:
        shape: (H, W)
        cutoff_percent: low-pass なら通過する内側半径 (%) / high-pass なら遮断する内側半径 (%)。
        mode: "highpass" | "lowpass" | "bandpass"
        high_cutoff_percent: bandpass の外側半径 (%)。
        soft_edge_px: 0 より大きいとガウス的に縁をぼかす（ピクセル単位）。

    Returns:
        shape と同じ大きさの float32 マスク (値域 0..1)。
    """
    if not 0 < cutoff_percent <= 100:
        raise ValueError(f"cutoff_percent must be in (0, 100], got {cutoff_percent}")

    h, w = shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    y = np.arange(h, dtype=np.float32)[:, None]
    x = np.arange(w, dtype=np.float32)[None, :]
    radius = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)

    # Nyquist 半径は短辺の半分。これに対する % をピクセル半径に変換。
    nyquist_radius = min(h, w) / 2.0
    r_in = nyquist_radius * (cutoff_percent / 100.0)

    if mode == "lowpass":
        mask = (radius <= r_in).astype(np.float32)
        if soft_edge_px > 0:
            soft = np.clip((r_in + soft_edge_px - radius) / soft_edge_px, 0.0, 1.0)
            mask = np.minimum(mask + (1 - mask) * soft, 1.0).astype(np.float32)
    elif mode == "highpass":
        mask = (radius >= r_in).astype(np.float32)
        if soft_edge_px > 0:
            soft = np.clip((radius - (r_in - soft_edge_px)) / soft_edge_px, 0.0, 1.0)
            mask = np.maximum(mask, soft).astype(np.float32)
    elif mode == "bandpass":
        if high_cutoff_percent is None:
            raise ValueError("bandpass mode requires high_cutoff_percent")
        r_out = nyquist_radius * (high_cutoff_percent / 100.0)
        if r_out <= r_in:
            raise ValueError("high_cutoff_percent must be > cutoff_percent for bandpass")
        mask = ((radius >= r_in) & (radius <= r_out)).astype(np.float32)
    else:
        raise ValueError(f"unknown mode: {mode}")

    return mask


def _apply_to_channel(channel: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """単一チャネル (float32, HxW) に対して FFT → マスク → iFFT を適用。"""
    mean = float(channel.mean())
    centered = channel - mean
    spec = np.fft.fftshift(np.fft.fft2(centered))
    spec_filtered = spec * mask
    recon = np.fft.ifft2(np.fft.ifftshift(spec_filtered)).real
    return recon + mean


def apply_cutoff(
    image: np.ndarray,
    cutoff_percent: float,
    mode: FilterMode = "highpass",
    high_cutoff_percent: float | None = None,
    soft_edge_px: float = 0.0,
) -> np.ndarray:
    """画像に空間周波数フィルタを適用する。

    Args:
        image: HxW (グレースケール) または HxWx{3,4} (RGB/RGBA) の uint8/float 配列。
        cutoff_percent: ナイキスト半径に対する％ (0..100)。
        mode: "highpass" | "lowpass" | "bandpass"
        high_cutoff_percent: bandpass のみ使用。
        soft_edge_px: マスクの縁をぼかす量（リンギング軽減）。

    Returns:
        入力と同じ shape / dtype=uint8 のフィルタ後画像。
    """
    if image.ndim not in (2, 3):
        raise ValueError(f"image must be 2D or 3D, got shape {image.shape}")

    arr = image.astype(np.float32, copy=False)
    if arr.ndim == 2:
        mask = build_circular_mask(
            arr.shape, cutoff_percent, mode, high_cutoff_percent, soft_edge_px
        )
        out = _apply_to_channel(arr, mask)
    else:
        h, w, c = arr.shape
        mask = build_circular_mask(
            (h, w), cutoff_percent, mode, high_cutoff_percent, soft_edge_px
        )
        out = np.empty_like(arr)
        # アルファチャネルはフィルタしない（あれば最後にそのままコピー）。
        rgb_channels = min(c, 3)
        for ch in range(rgb_channels):
            out[..., ch] = _apply_to_channel(arr[..., ch], mask)
        if c == 4:
            out[..., 3] = arr[..., 3]

    return np.clip(out, 0, 255).astype(np.uint8)
