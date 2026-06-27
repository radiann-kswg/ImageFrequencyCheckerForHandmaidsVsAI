"""コマンドラインエントリーポイント。

例:
    python -m img_freq_extractor input.png -o out/
    python -m img_freq_extractor input.png -o out/ --cutoffs 50 60 70 --mode highpass
    python -m img_freq_extractor input.png -o out/ --mode lowpass --no-strip
    python -m img_freq_extractor --serve              # Web UI を 4165 番で起動
    python -m img_freq_extractor --serve --port 8080  # 別ポートで起動
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
    p.add_argument(
        "input", type=Path, nargs="?",
        help="入力画像ファイル (png/jpg/...)。--serve 時は不要。",
    )
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
    p.add_argument(
        "--normalize", action="store_true",
        help=(
            "highpass/bandpass の出力を視認しやすくコントラスト引き伸ばしする "
            "(色相は保持、全チャネル共通スケール)。CLI 既定は OFF。"
        ),
    )
    p.add_argument(
        "--binarize", action="store_true",
        help=(
            "各カットオフ画像を二値化 (白黒化) して保存する。X 投稿 2〜4 枚目の"
            "ような白黒エッジ画像を再現する用途。CLI 既定は OFF。"
        ),
    )
    p.add_argument(
        "--binarize-method", choices=["otsu", "fixed"], default="otsu",
        help="二値化の閾値決定方法。otsu (自動) または fixed (固定値)。既定: otsu",
    )
    p.add_argument(
        "--binarize-threshold", type=float, default=None,
        help="--binarize-method fixed の閾値 (0..255)。既定: 127",
    )
    p.add_argument(
        "--binarize-invert", action="store_true",
        help="二値化の白黒を反転する (黒地→白地)。",
    )

    # Web UI 関連
    p.add_argument(
        "--serve", action="store_true",
        help="ローカル Web UI を起動する (既定ポート: 4165)。input は無視される。",
    )
    p.add_argument(
        "--host", default="127.0.0.1",
        help="--serve 時のバインドアドレス。既定: 127.0.0.1 (ループバックのみ)",
    )
    p.add_argument(
        "--port", type=int, default=4165,
        help="--serve 時のポート番号。既定: 4165",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Web UI モード: --serve が立っていればそちらに分岐
    if args.serve:
        # サーバ依存を遅延 import (CLI バッチ用途では読み込みを避けたい)
        from .server import serve
        return serve(host=args.host, port=args.port)

    if args.input is None:
        print(
            "[error] input が指定されていません。--serve なしの場合は入力画像が必須です。",
            file=sys.stderr,
        )
        return 2
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
            normalize=args.normalize,
            binarize=args.binarize,
            binarize_method=args.binarize_method,
            binarize_threshold=args.binarize_threshold,
            binarize_invert=args.binarize_invert,
        )
    except (ValueError, OSError) as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1

    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
