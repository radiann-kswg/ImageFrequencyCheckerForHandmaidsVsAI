"""フィルタ結果を出力ファイル／比較レイアウトとして書き出す。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image

from .filter import FilterMode, apply_cutoff


def _load_image(path: Path) -> tuple[np.ndarray, str]:
    """画像を読み込み、(ndarray, mode) を返す。mode は PIL の元 mode。"""
    with Image.open(path) as im:
        original_mode = im.mode
        # フィルタ処理は RGB or L で行う
        if im.mode in ("RGB", "L"):
            return np.asarray(im), im.mode
        if im.mode == "RGBA":
            return np.asarray(im), "RGBA"
        return np.asarray(im.convert("RGB")), "RGB"


def _save_image(arr: np.ndarray, path: Path, mode_hint: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr.ndim == 2:
        Image.fromarray(arr, mode="L").save(path)
    elif arr.shape[2] == 4:
        Image.fromarray(arr, mode="RGBA").save(path)
    else:
        Image.fromarray(arr, mode="RGB").save(path)


def process_image(
    input_path: str | Path,
    output_dir: str | Path,
    cutoffs: Sequence[float] = (50, 60, 70),
    mode: FilterMode = "highpass",
    soft_edge_px: float = 0.0,
    make_strip: bool = True,
    output_format: str = "png",
) -> list[Path]:
    """1 枚の入力画像に対し、複数カットオフでフィルタを適用して保存する。

    Args:
        input_path: 入力画像ファイル。
        output_dir: 出力ディレクトリ（無ければ作成）。
        cutoffs: 適用するカットオフのリスト（％）。
        mode: フィルタモード。
        soft_edge_px: マスクの縁ぼかし。
        make_strip: True なら原本 + 各カットオフを横並びにした比較画像も出力。
        output_format: 拡張子（"png" / "jpg" 等）。

    Returns:
        生成したファイルの Path のリスト。
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    img, _ = _load_image(input_path)

    stem = input_path.stem
    generated: list[Path] = []

    filtered_images: list[np.ndarray] = []
    for cutoff in cutoffs:
        out_arr = apply_cutoff(img, cutoff_percent=cutoff, mode=mode, soft_edge_px=soft_edge_px)
        out_path = output_dir / f"{stem}_{mode}_cutoff{int(cutoff)}.{output_format}"
        _save_image(out_arr, out_path, mode_hint="RGB")
        generated.append(out_path)
        filtered_images.append(out_arr)

    if make_strip:
        strip = make_comparison_strip(img, filtered_images, labels=[f"{int(c)}" for c in cutoffs])
        strip_path = output_dir / f"{stem}_compare.{output_format}"
        _save_image(strip, strip_path, mode_hint="RGB")
        generated.append(strip_path)

    return generated


def make_comparison_strip(
    original: np.ndarray,
    filtered: Sequence[np.ndarray],
    labels: Iterable[str] | None = None,
    gap_px: int = 8,
    bg_value: int = 0,
) -> np.ndarray:
    """原本 + フィルタ結果を横並びにした 1 枚の比較画像を作る（X 投稿のレイアウト）。"""
    panels = [original, *filtered]
    # 全パネルを同じ高さに揃える（既に同サイズの想定だが念のため）。
    h = max(p.shape[0] for p in panels)
    widths = [p.shape[1] for p in panels]
    total_w = sum(widths) + gap_px * (len(panels) - 1)

    # チャネル数を揃える（混在ケースを RGB に正規化）。
    def _to_rgb(p: np.ndarray) -> np.ndarray:
        if p.ndim == 2:
            return np.stack([p] * 3, axis=-1)
        if p.shape[2] == 4:
            return p[..., :3]
        return p

    panels = [_to_rgb(p) for p in panels]
    canvas = np.full((h, total_w, 3), bg_value, dtype=np.uint8)

    x = 0
    for p in panels:
        ph, pw = p.shape[:2]
        canvas[:ph, x : x + pw] = p
        x += pw + gap_px

    return canvas
