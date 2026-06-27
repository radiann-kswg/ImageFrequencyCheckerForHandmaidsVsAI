# コントリビュートガイド

ImageFrequencyCheckerForHandmaidsVsAI への貢献に興味を持っていただきありがとうございます。
Issue / Pull Request を歓迎します。このドキュメントは開発の進め方と設計方針をまとめたものです。

> 🤖 本ツールは GitHub Copilot と Claude によるバイブコーディングで実装されています。
> AI 支援開発の特性上、設計の粗さやエッジケースの取りこぼしが残っている可能性があります。
> 改善提案・バグ報告は大歓迎です。

## 開発環境のセットアップ

```bash
# 仮想環境（Windows / PowerShell の例）
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # macOS/Linux: source .venv/bin/activate

# 依存導入（開発用）
pip install -e ".[dev]"

# テスト
pytest -q
```

Python 3.10 以上が必要です。依存は NumPy / Pillow のみ（テストに pytest）。

## 設計方針（重要）

詳細は [AGENTS.md](AGENTS.md) と [.github/copilot-instructions.md](.github/copilot-instructions.md)
を参照してください。要点は次のとおりです。

- **層の責務を混ぜない**: `filter.py` はアルゴリズムの純粋関数のみ（`Path` や `PIL` を import しない）。
  ファイル I/O・画像合成は `compose.py`、CLI は `cli.py`、Web UI ブリッジは `server.py`。
- **軽量性を保つ**: 重い依存（PyTorch / TensorFlow / OpenCV 全体）は追加しない。
- **Upstream の帰属を維持**: アルゴリズムは [`djmannion/img_freq_web`](https://github.com/djmannion/img_freq_web)
  (MIT) の再実装です。[NOTICE.md](NOTICE.md) の帰属表記を削除しないでください。
- **SNS 画像の自動取得・スクレイピング機能は追加しない**（各 SNS の利用規約に抵触し得るため）。
- **大規模変更**（目安 200 行以上、または既存パブリック API のシグネチャ変更）は、
  先に Issue で計画を共有してから実装してください。

## Pull Request の流れ

1. リポジトリを fork し、ブランチを作成（例: `feature/xxx`, `fix/yyy`）。
2. 変更を加え、`pytest -q` が通ることを確認。
3. 必要に応じてテスト（`tests/test_*.py`）を追加・更新。
4. PR を作成。[PR テンプレート](.github/PULL_REQUEST_TEMPLATE.md) に沿って説明を記入してください。

CI（GitHub Actions）が push / PR 時に Python 3.10〜3.12 で `pytest` を実行します。

## コードスタイル

- コードコメント・docstring・ログメッセージは日本語、識別子は英語。
- 実行時バリデーションは `assert` ではなく `raise ValueError(...)` を使う。
- `from module import *` は使わない。デバッグ用 `print` はコミット前に削除する。

## ライセンス

本プロジェクトは MIT ライセンスです。コントリビュートいただいたコードは
同ライセンスの下で公開されることに同意したものとみなします。
