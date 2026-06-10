# GitHub Copilot 指示書 (copilot-instructions.md)

> 本ファイルは [Qiita「GitHub Copilotを使っている人は全員 copilot-instructions.md を作成してください」](https://qiita.com/TooMe/items/873540da84567733d16b) の推奨構成（7 項目）に従って記述しています。
> 各項目はプロジェクトの「取扱説明書」として、GitHub Copilot がユーザの指示を処理する前に最初に読み込む前提です。

---

## 1. 前提条件

- 回答は **必ず日本語** で行うこと。コードコメント・ドキッグストリング・ログメッセージも日本語で統一する（識別子は英語）。
- **大規模変更（目安: 200 行以上、または既存のパブリック API のシグネチャ変更）を行う前に、必ず変更計画を箇条書きで提示し、ユーザーの承認を得てから実装する**。
- 本リポジトリは **私的利用かつプライベートブランチ運用** を前提としている。
  - **パブリックリポジトリへの push、第三者配布、商用利用を想定する変更を提案しない**（CI/CD で公開デプロイするワークフロー追加、PyPI 公開設定、Docker Hub 公開、GitHub Pages デプロイ等を勝手に提案しない）。
  - `pyproject.toml` の `classifiers` にある `Private :: Do Not Upload` を **削除しない**。
  - [AGENTS.md](../AGENTS.md) / [README.md](../README.md) 冒頭の警告ブロックを **削除・改変しない**。
- 本リポジトリは Upstream `djmannion/img_freq_web` (MIT) の **アルゴリズムを再実装** したもの。
  - Upstream の JavaScript コードを **そのまま翻訳して貼り付けない**（独自再実装の形を保つ）。
  - [NOTICE.md](../NOTICE.md) の帰属表記を勝手に削除しない。
- **SNS（X / Twitter 等）から画像を自動取得する機能、スクレイピング機能は追加しない**。各 SNS の利用規約に抵触し得るため。
- ワークスペースのパスにスペース (`VisualStudio Code Userfile`) が含まれる。PowerShell コマンド例では必ずパスをダブルクォートで囲むこと。

## 2. アプリの概要

- **プロジェクト名**: ImageFrequencyCheckerForHandmaidsVsAI
- **目的**: 1 枚の画像から、ナイキスト半径に対する **3 段階のカットオフ（既定 50% / 60% / 70%）** で空間周波数フィルタを掛けた画像を一括生成する。
- **背景**: AI 生成画像と人手描き画像の **中間周波数帯域の情報分布** を可視化・比較する用途（着想元: [@dried_gosari の X 投稿群](../NOTICE.md)）。
- **入出力**:
  - 入力: 画像ファイル 1 枚（PNG/JPEG 等、Pillow が読めるもの）
  - 出力: 各カットオフごとのフィルタ画像 N 枚 + 横並び比較画像 1 枚
- **主要機能**:
  - `highpass` / `lowpass` / `bandpass` の選択
  - カットオフリストの可変指定（`--cutoffs 50 60 70`）
  - リンギング軽減用ソフトエッジ
  - 比較ストリップ画像の生成（X 投稿のレイアウトを再現）

## 3. 技術スタック（エコシステム）

| 種別 | 名称 | バージョン | 用途 |
|---|---|---|---|
| 言語 | Python | 3.10 以上 | 全実装 |
| 数値計算 | NumPy | >=1.24 | FFT・配列演算 |
| 画像 I/O | Pillow | >=10.0 | 画像読み書き |
| テスト | pytest | >=7.0（dev） | ユニットテスト |
| パッケージング | setuptools (PEP 621 `pyproject.toml`) | 68+ | ローカル `pip install -e .` |

**追加してよいライブラリの方針**:
- 単体追加で済む小さい I/O・補助ツール (例: `imageio`) は OK だが、提案時に理由を述べる。
- **重い依存（PyTorch / TensorFlow / OpenCV 全体）は追加しない**。本ツールの軽量性を保つ。
- SciPy の `fft` 高速版を使う場合は optional 依存として追加（必須にしない）。

## 4. ディレクトリ構成

```
ImageFrequencyCheckerForHandmaidsVsAI/
├── .github/
│   └── copilot-instructions.md   # 本ファイル
├── src/
│   └── img_freq_extractor/
│       ├── __init__.py           # 公開 API
│       ├── __main__.py           # `python -m img_freq_extractor`
│       ├── filter.py             # FFT / マスク / 逆 FFT（純粋関数）
│       ├── compose.py            # ファイル I/O・比較画像生成
│       └── cli.py                # argparse によるコマンドラインI/F
├── tests/
│   └── test_filter.py            # アルゴリズムのスモーク + 性質ベーステスト
├── examples/
│   ├── README.md                 # サンプル使用法
│   ├── input/                    # ★.gitignore（誤公開防止）
│   └── output/                   # ★.gitignore
├── third_party/
│   ├── README.md                 # Upstream のクローン手順
│   └── img_freq_web/             # ★.gitignore（参照のみ・配布しない）
├── AGENTS.md                     # AI エージェント向け最小ガイド
├── README.md                     # 人間向け README（冒頭に私的利用警告）
├── NOTICE.md                     # Upstream 帰属とライセンス通知
├── LICENSE                       # MIT（Upstream から継承）
├── pyproject.toml                # ビルド・依存・CLI スクリプト定義
├── requirements.txt              # 最小依存
└── .gitignore
```

**新規ファイルを追加する際のルール**:
- アルゴリズムの純粋関数は `filter.py` に追加（I/O を含めない）。
- ファイル入出力・複数画像合成は `compose.py` に追加。
- CLI 引数の追加は `cli.py` の `_build_parser()` を更新し、対応する `compose.process_image()` の引数を増やす。
- テストは `tests/test_<module>.py` に。

## 5. アーキテクチャ・設計指針

### 5.1 全体アーキテクチャ

```
[CLI: cli.py]
   ↓ argparse でパース
[I/O 層: compose.py]
   ↓ Pillow で読み込み → np.ndarray
[アルゴリズム層: filter.py]
   ↓ build_circular_mask() → apply_cutoff()
   ↓ FFT2 → fftshift → mask 適用 → ifftshift → IFFT2
[I/O 層: compose.py]
   ↓ 結果保存 + make_comparison_strip() で比較画像
[CLI: cli.py]
   ↓ 出力パスを stdout に列挙
```

### 5.2 設計原則

1. **層の責務を混ぜない**: `filter.py` には `Path` も `PIL` も登場しない（純粋に numpy 配列の入出力のみ）。テスト容易性のため。
2. **副作用の局所化**: ディスク書き込みは `compose._save_image()` 1 箇所に集約。
3. **設定はトップレベル関数の引数で受ける**: グローバル変数や環境変数は導入しない。
4. **既定値は X 投稿の入出力例を再現できるもの**: 既定 `cutoffs=(50, 60, 70)`、`mode="highpass"`。
5. **エラーハンドリングは境界で**: CLI で `ValueError` / `OSError` を catch して `exit(1)`。アルゴリズム層は素直に raise する。

### 5.3 アルゴリズムの要点（変更時の注意）

- カットオフは **ナイキスト半径 (=短辺/2 px) に対するパーセント**。これは X 投稿の「50/60/70」と直感的に揃える設計上の選択。Upstream の cycles/image 表現とは異なるので、CLI に `--unit` を後付けする場合はデフォルト動作を変えないこと。
- FFT 前に平均値を引いてから掛け、後で戻す。これにより DC 成分の扱いが安定する。
- カラー画像は **チャネルごとに独立に** FFT/IFFT。アルファチャネルはフィルタしない。
- マスクは `fftshift` 後の座標系で構築（中心が DC）。ifftshift して周波数領域へ戻す。

## 6. テスト方針

- **フレームワーク**: pytest。テストは `tests/` 配下、`test_*.py` 命名。
- **配置**: テスト対象モジュールごとに 1 ファイル（`test_filter.py`, 将来 `test_compose.py`, `test_cli.py`）。
- **方針**:
  - **性質ベーステスト**を優先（例: 「ローパス 100% は元画像を保つ」「ハイパスは平均輝度の DC 成分を消す」）。
  - 数値の一致テストは丸め誤差を考慮し、`np.abs(...).mean() < ε` のように許容差で書く。
  - 画像ファイルは可能なら **生成して使う**（リポジトリにバイナリを増やさない）。サンプル画像を追加する場合は権利関係を必ず確認。
- **実行**:
  ```powershell
  pytest -q
  ```
- **カバレッジ目標**: 当面は `filter.py` の主要関数を全てカバー。CLI は smoke 実行で十分。
- **CI**: 現時点では設定しない（私的利用前提）。追加するなら、GitHub Actions を **`workflow_dispatch` のみ**にし、自動公開を行わない構成にする。

## 7. アンチパターン（やってはいけないこと）

### コード規約

- ❌ **`from module import *`** は禁止。明示的にインポート。
- ❌ **`print` でデバッグログを残す**。一時的に使うのは可だが、コミット前に削除する。常設ログが必要なら `logging` を使う。
- ❌ **`assert` で実行時バリデーション**しない（最適化フラグで消える）。`raise ValueError(...)` を使う。
- ❌ **マジックナンバーをハードコード**。カットオフ既定値などは `cli.py` の `default=` に集約。
- ❌ **`# type: ignore`** の濫用。原則として型エラーは直す。
- ❌ **広範な `except Exception`**。境界（CLI）以外では具体的な例外を捕捉する。

### 設計

- ❌ **`filter.py` に `Path` や `PIL` を import** しない（層の混入禁止）。
- ❌ **新規ディレクトリを増やす変更**を計画提示なしで行わない。
- ❌ **依存ライブラリを軽率に追加**しない（特に OpenCV / PyTorch 等の大型依存）。
- ❌ **既定の出力ファイル名規則 (`{stem}_{mode}_cutoff{int}.{ext}`) を勝手に変える**。X 投稿のレイアウト再現性のため。

### 運用・規約

- ❌ **`AGENTS.md` / `README.md` 冒頭の私的利用警告ブロックを削除・改変しない**。
- ❌ **`NOTICE.md` の Upstream 帰属を削除しない**。
- ❌ **SNS 画像取得・スクレイピングコードを追加しない**。
- ❌ **PyPI / Docker Hub / GitHub Pages 等への自動公開ワークフローを追加しない**。
- ❌ **`pyproject.toml` の `Private :: Do Not Upload` classifier を削除しない**。
- ❌ **`third_party/img_freq_web/` の中身を改変してコミットしない**（あくまで参照用）。
- ❌ **入力画像 (`examples/input/`) や出力 (`examples/output/`) を `.gitignore` から外さない**（個人画像の誤公開防止）。

---

最終更新: 2026-06-11
