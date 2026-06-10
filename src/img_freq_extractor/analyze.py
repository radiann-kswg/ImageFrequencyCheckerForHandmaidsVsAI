"""イラストの「情報量」可視化（NumPy 完結版）。

参考:
    https://zenn.dev/mattyamonaca/articles/d3d7acbd796733
    "AIを使ってイラストの情報量を可視化できないか試してみた" (抹茶もなか)

依存方針:
    本リポジトリは PyTorch / Segment Anything / OpenCV を入れない方針
    （[copilot-instructions.md](../../.github/copilot-instructions.md) 参照）
    のため、SAM ベースの「セグメント密集度」は実装しない。
    代わりに NumPy のみで実装できる以下の 2 手法を提供する:

    - **luminance**: 輝度マップ（明度の情報）
    - **local_contrast**: 局所コントラストマップ
        （sliding-window 内の輝度標準偏差。
        SAM の代替として「情報の密集している領域」を近似表示する目的）

各マップは jet カラーマップで可視化し、原画にアルファ合成したオーバーレイ画像も
返す。SAM 版より粗いが、線が密な領域・テクスチャ豊富な領域を視覚的に強調できる。
"""

from __future__ import annotations

from typing import Literal

import numpy as np

InfoMetric = Literal["luminance", "local_contrast"]
BinarizeMethod = Literal["otsu", "fixed"]


def to_luminance(image: np.ndarray) -> np.ndarray:
    """ITU-R BT.601 で RGB → 輝度（float32, HxW）。

    グレースケール入力はそのまま float32 化して返す。
    RGBA はアルファを無視して RGB から計算。
    """
    if image.ndim == 2:
        return image.astype(np.float32)
    if image.shape[2] >= 3:
        return (
            0.299 * image[..., 0].astype(np.float32)
            + 0.587 * image[..., 1].astype(np.float32)
            + 0.114 * image[..., 2].astype(np.float32)
        )
    raise ValueError(f"unsupported image shape for luminance: {image.shape}")


def _box_filter(arr: np.ndarray, window: int) -> np.ndarray:
    """積分画像を使った O(N) ボックスフィルタ（境界は valid 領域で割る）。

    NumPy のみで実装。`scipy.ndimage.uniform_filter` 相当だが追加依存なし。
    """
    if arr.ndim != 2:
        raise ValueError(f"_box_filter requires 2D array, got {arr.shape}")
    h, w = arr.shape
    win = max(1, min(window, h, w))
    half = win // 2

    # 積分画像 (左上ゼロ行/列を追加)
    ii = arr.astype(np.float64).cumsum(axis=0).cumsum(axis=1)
    ii = np.pad(ii, ((1, 0), (1, 0)), constant_values=0.0)

    rows = np.arange(h)
    cols = np.arange(w)
    i0 = np.clip(rows - half, 0, h)
    i1 = np.clip(rows - half + win, 0, h)
    j0 = np.clip(cols - half, 0, w)
    j1 = np.clip(cols - half + win, 0, w)

    I0 = i0[:, None]
    I1 = i1[:, None]
    J0 = j0[None, :]
    J1 = j1[None, :]

    total = ii[I1, J1] - ii[I0, J1] - ii[I1, J0] + ii[I0, J0]
    area = (I1 - I0) * (J1 - J0)
    area = np.where(area > 0, area, 1)
    return (total / area).astype(np.float32)


def local_contrast_map(image: np.ndarray, window: int = 32) -> np.ndarray:
    """sliding-window 内の輝度標準偏差マップ。

    Zenn 記事の `cluster_analysis` (SAM セグメント数の密集度) は AI 推論が必要で
    依存が重くなるため、近似として「窓内の輝度ばらつき」を採用。
    テクスチャの濃い領域・コントラストが激しい領域が高値になる。

    Args:
        image: HxW または HxWx{3,4}
        window: 窓サイズ (px)。小さいほど局所、大きいほど大域。
            記事の `window_size=64` 程度を目安に、画像短辺の 1/8 〜 1/16 を推奨。

    Returns:
        HxW の float32 配列（同 shape の輝度標準偏差）。
    """
    lum = to_luminance(image)
    mean = _box_filter(lum, window)
    sq_mean = _box_filter(lum * lum, window)
    var = np.clip(sq_mean - mean * mean, 0.0, None)
    return np.sqrt(var)


def jet_colormap(values: np.ndarray) -> np.ndarray:
    """[0, 1] の float 配列を jet 風 RGB (uint8) に変換。

    matplotlib に頼らず NumPy だけで実装した近似 jet。
    青 → シアン → 緑 → 黄 → 赤 の 4 段グラデーション。
    """
    v = np.clip(values.astype(np.float32), 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * v - 3.0), 0.0, 1.0)
    g = np.clip(1.5 - np.abs(4.0 * v - 2.0), 0.0, 1.0)
    b = np.clip(1.5 - np.abs(4.0 * v - 1.0), 0.0, 1.0)
    rgb = np.stack([r, g, b], axis=-1) * 255.0
    return rgb.astype(np.uint8)


def _normalize_minmax(arr: np.ndarray) -> np.ndarray:
    """[0, 1] に min-max 正規化。フラット入力は 0 を返す。"""
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def compute_information_map(
    image: np.ndarray,
    metric: InfoMetric = "local_contrast",
    window: int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    """画像から「情報量マップ」と jet 可視化を返す。

    Returns:
        (heatmap_rgb, normalized_values)
        - heatmap_rgb: HxWx3 uint8 (jet カラー)
        - normalized_values: HxW float32 ([0, 1] 正規化された生値)
    """
    if metric == "luminance":
        raw = to_luminance(image)
    elif metric == "local_contrast":
        raw = local_contrast_map(image, window=window)
    else:
        raise ValueError(f"unknown metric: {metric!r}")

    normalized = _normalize_minmax(raw)
    heatmap = jet_colormap(normalized)
    return heatmap, normalized


def overlay_information_map(
    image: np.ndarray,
    metric: InfoMetric = "local_contrast",
    window: int = 32,
    alpha: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """情報量マップを元画像にアルファ合成したオーバーレイを返す。

    Args:
        image: 入力画像 (HxW / HxWx3 / HxWx4)。RGBA はアルファを無視して合成。
        metric: 使う指標。
        window: local_contrast の窓サイズ。
        alpha: ヒートマップの不透明度 (0..1)。

    Returns:
        (overlay_rgb, heatmap_rgb)
        どちらも HxWx3 uint8。
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    heatmap, _ = compute_information_map(image, metric=metric, window=window)

    # 入力を RGB に正規化（A はドロップ、L は 3ch 複製）
    if image.ndim == 2:
        base = np.stack([image] * 3, axis=-1).astype(np.float32)
    elif image.shape[2] >= 3:
        base = image[..., :3].astype(np.float32)
    else:
        raise ValueError(f"unsupported image shape: {image.shape}")

    overlay = base * (1.0 - alpha) + heatmap.astype(np.float32) * alpha
    return np.clip(overlay, 0, 255).astype(np.uint8), heatmap


# ── 二値化（X 投稿の 2〜4 枚目を再現するための白黒化） ─────────────────────


def _otsu_threshold(lum: np.ndarray) -> float:
    """大津の二値化で最適閾値を求める。

    NumPy のみで 256-bin ヒストグラム + クラス間分散最大化を実装。
    `cv2.threshold(..., cv2.THRESH_OTSU)` 相当の結果を返す。
    """
    flat = np.clip(lum, 0.0, 255.0)
    hist, _ = np.histogram(flat, bins=256, range=(0.0, 256.0))
    total = int(hist.sum())
    if total == 0:
        return 127.0

    intensities = np.arange(256, dtype=np.float64)
    sum_total = float((intensities * hist).sum())

    w_b = 0.0
    sum_b = 0.0
    max_var = -1.0
    threshold = 127.0
    for t in range(256):
        count = float(hist[t])
        w_b += count
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * count
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var_between = w_b * w_f * (m_b - m_f) ** 2
        if var_between > max_var:
            max_var = var_between
            threshold = float(t)
    # Otsu の規約は「t 以下が背景、t 超が前景」。本ファイルの二値化判定は
    # `lum >= thr` を使うため、境界を +1 して両規約を一致させる。
    return threshold + 1.0


def binarize_image(
    image: np.ndarray,
    method: BinarizeMethod = "otsu",
    threshold: float | None = None,
    invert: bool = False,
) -> np.ndarray:
    """画像をグレースケール化し、閾値で 0/255 の二値画像にする。

    X 投稿の 2〜4 枚目 ([dried_gosari の例](https://x.com/dried_gosari/status/2064347491152306560))
    のように、空間周波数フィルタ後の白黒エッジ画像を再現するために使う。

    Args:
        image: HxW または HxWx{3,4}（uint8 推奨）。
        method: "otsu"（大津の自動閾値）または "fixed"（固定閾値）。
        threshold: `method="fixed"` 時の閾値（0..255）。None なら 127。
            `method="otsu"` 時はこの値を無視する。
        invert: True で 0/255 を反転（黒地に白線 → 白地に黒線）。

    Returns:
        HxW uint8（0 か 255 のみ）。
    """
    lum = to_luminance(image)

    if method == "otsu":
        thr = _otsu_threshold(lum)
    elif method == "fixed":
        if threshold is None:
            thr = 127.0
        else:
            if not 0.0 <= float(threshold) <= 255.0:
                raise ValueError(
                    f"threshold は 0..255 の範囲で指定してください: {threshold}"
                )
            thr = float(threshold)
    else:
        raise ValueError(f"unknown binarize method: {method!r}")

    binary = (lum >= thr).astype(np.uint8) * 255
    if invert:
        binary = (255 - binary).astype(np.uint8)
    return binary
