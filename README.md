# ImageFrequencyCheckerForHandmaidsVsAI

> 🧪 **実験的ツールです** — 本ツールは画像の空間周波数帯域分布を可視化し、
> AI 生成画像と人手描き画像の傾向比較を補助することを目的とした実験的・教育的な
> ツールです。出力はあくまで判断材料であり、AI 生成か否かを断定するものでは
> ありません。利用にあたっては、Upstream である
> [`djmannion/img_freq_web`](https://github.com/djmannion/img_freq_web) (MIT) の規約、
> 入力画像の権利関係、各 SNS の利用規約を必ず遵守してください。詳細は
> [NOTICE.md](NOTICE.md) を参照。
>
> 🤖 本ツールは **GitHub Copilot と Claude によるバイブコーディング** で実装されました。
> AI 支援開発の特性上、想定外の挙動が残っている可能性があります。Issue / PR を歓迎します。

[![CI](https://github.com/radiann-kswg/ImageFrequencyCheckerForHandmaidsVsAI/actions/workflows/ci.yml/badge.svg)](https://github.com/radiann-kswg/ImageFrequencyCheckerForHandmaidsVsAI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

画像 1 枚を入力として、空間周波数帯域を **3 段階のカットオフ（既定 50% / 60% / 70%）**
で抽出した画像を一括出力する CLI ツールです。
[`djmannion/img_freq_web`](https://github.com/djmannion/img_freq_web) (MIT) のアルゴリズム
「FFT → 円形カットオフ → 逆 FFT」を Python に再実装し、複数カットオフを
バッチ処理できるようにしたものです。

## クイックスタート

### 1. 環境構築 (Windows / PowerShell)

```powershell
# 仮想環境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 依存導入（開発用）
pip install -e ".[dev]"
```

### 2. 実行

```powershell
# 既定（50/60/70 ハイパス）
python -m img_freq_extractor "examples\input\sample.png" -o "examples\output"

# カットオフをカスタマイズ
python -m img_freq_extractor input.png -o out --cutoffs 40 55 70 85

# ローパスに切り替え
python -m img_freq_extractor input.png -o out --mode lowpass

# 比較ストリップ画像を作らない
python -m img_freq_extractor input.png -o out --no-strip
```

### 3. 出力

入力 `sample.png` から、既定設定で以下が生成されます。

| ファイル                       | 内容                                                       |
| ------------------------------ | ---------------------------------------------------------- |
| `sample_highpass_cutoff50.png` | 50% を超える周波数のみ残した画像                           |
| `sample_highpass_cutoff60.png` | 60% を超える周波数のみ残した画像                           |
| `sample_highpass_cutoff70.png` | 70% を超える周波数のみ残した画像                           |
| `sample_compare.png`           | 原本 + 上記 3 枚を横並びにした比較画像（X 投稿レイアウト） |

カットオフ値は **画像短辺の半分（ナイキスト半径）に対するパーセント** です。

## Python API

```python
import numpy as np
from PIL import Image
from img_freq_extractor import apply_cutoff, process_image

# 単発フィルタ
img = np.asarray(Image.open("input.png"))
out = apply_cutoff(img, cutoff_percent=60, mode="highpass")

# 入出力含むワンショット処理
process_image("input.png", "out/", cutoffs=(50, 60, 70))
```

## テスト

```powershell
pytest -q
```

## Web UI（ローカル限定）

ブラウザから画像をアップロードして、X / Twitter 投稿風カードレイアウトで
入出力を比較できる **ローカル専用** Web UI を同梱しています。
公開はしません（バインドは `127.0.0.1`、外部ネットワークから到達不可）。

```powershell
# 既定: http://127.0.0.1:4165/
python -m img_freq_extractor --serve

# ポート変更
python -m img_freq_extractor --serve --port 8080
```

詳細な使い方・画面構成・API 仕様は [docs/webui.md](docs/webui.md) を参照してください。

## コントリビュート

Issue / Pull Request を歓迎します。開発の進め方・設計方針は
[CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## 開発者向けドキュメント

- コントリビュートガイド → [CONTRIBUTING.md](CONTRIBUTING.md)
- AI エージェント向けガイド → [AGENTS.md](AGENTS.md)
- Copilot 詳細指示書 → [.github/copilot-instructions.md](.github/copilot-instructions.md)
- Claude 向け設定 → [CLAUDE.md](CLAUDE.md)
- Upstream クローン手順 → [third_party/README.md](third_party/README.md)
- 帰属・ライセンス通知 → [NOTICE.md](NOTICE.md)

## ライセンス

MIT License（Upstream `djmannion/img_freq_web` から継承）。詳細は [LICENSE](LICENSE) と [NOTICE.md](NOTICE.md) を参照。
