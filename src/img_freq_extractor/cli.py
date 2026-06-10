"""コマンドラインエントリーポイント。

例:
    python -m img_freq_extractor input.png -o out/
    python -m img_freq_extractor input.png -o out/ --cutoffs 50 60 70 --mode highpass
    python -m img_freq_extractor input.png -o out/ --mode lowpass --no-strip
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compose import process_image


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="img_freq_extractor",
        description=(
            "画像の空間周波数帯域を複数のカットオフで抽出する "
            "(djmannion/img_freq_web 由来のアルゴリズムを Python に移植)"
        ),
    )
    p.add_argument("input", type=Path, help="入力画像ファイル (png/jpg/...)")
    p.add_argument(
        "-o", "--output-dir", type=Path, default=Path("./output"),
        help="出力先ディレクトリ (既定: ./output)",
    )
    p.add_argument(
        "--cutoffs", type=float, nargs="+", default=[50, 60, 70],
        help="カットオフ％ (ナイキスト半径基準)。複数指定可。既定: 50 60 70",
    )
    p.add_argument(
        "--mode", choices=["highpass", "lowpass", "bandpass"], default="highpass",
        help="フィルタモード。既定: highpass (中〜高周波だけ残す)",
    )
    p.add_argument(
        "--soft-edge", type=float, default=0.0,
        help="マスク縁ぼかし量 (px)。リンギング軽減用。0 で無効。",
    )
    p.add_argument(
        "--no-strip", action="store_true",
        help="原本+各カットオフを並べた比較画像を作らない",
    )
    p.add_argument(
        "--format", default="png",
        help="出力フォーマット拡張子 (png/jpg 等)。既定: png",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if not args.input.exists():
        print(f"[error] input not found: {args.input}", file=sys.stderr)
        return 2

    try:
        outputs = process_image(
            input_path=args.input,
            output_dir=args.output_dir,
            cutoffs=args.cutoffs,
            mode=args.mode,
            soft_edge_px=args.soft_edge,
            make_strip=not args.no_strip,
            output_format=args.format,
        )
    except (ValueError, OSError) as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1

    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
