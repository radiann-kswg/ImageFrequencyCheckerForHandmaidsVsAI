# AGENTS.md

> ⚠️ **重要 — 私的利用かつプライベートブランチ運用前提**
>
> 本リポジトリは **個人の私的利用（教育・自己学習・私的検証）に限定** して
> 運用する想定です。**パブリックリポジトリへの push、第三者への配布、商用利用は
> 行わない** 方針です。Upstream である `djmannion/img_freq_web` (MIT) の規約と、
> 入力画像の権利関係・各 SNS の利用規約を必ず遵守してください。

このファイルは AI コーディングエージェント（GitHub Copilot / Claude Code 等）
向けの最小ガイドです。詳細な指示書は次の場所にあります。

- 詳細仕様 / 7 項目構成のルール → [.github/copilot-instructions.md](.github/copilot-instructions.md)
- 帰属とライセンス → [NOTICE.md](NOTICE.md), [LICENSE](LICENSE)
- ユーザ向け使い方 → [README.md](README.md)
- Upstream の取り扱い → [third_party/README.md](third_party/README.md)
- 入出力サンプルの置き場 → [examples/README.md](examples/README.md)

## 一目で分かる本プロジェクト

- **目的**: 1 枚の画像 → 3 段階のカットオフ (既定 50/60/70) で空間周波数フィルタ
  をかけた 3 枚 + 比較用 1 枚を出力する CLI。
- **言語**: Python 3.10+ / NumPy / Pillow のみ（重い依存なし）。
- **由来**: `djmannion/img_freq_web` (MIT) のアルゴリズム
  「FFT → 円形カットオフ → 逆 FFT」を Python に再実装。
- **エントリ**: `python -m img_freq_extractor <input> -o <out_dir>`

## エージェントへの最重要ルール（短く）

1. **回答は日本語**。
2. **私的利用前提の文面・運用** を壊さない（README/AGENTS 冒頭の警告を勝手に
   削除しない、公開を前提とした文言を追加しない）。
3. **Upstream のコードを丸ごとコピーしない**。アルゴリズムの再実装はOKだが、
   MIT 帰属表記 (`NOTICE.md`) を維持すること。
4. **SNS 画像の自動取得機能は追加しない**（X 等の規約に抵触し得るため）。
5. **大規模変更 (>200 行 / 既存パブリック API 変更) は事前に計画提案**してから
   実装する。
6. ファイルパスにスペースを含むワークスペース
   (`D:\VisualStudio Code Userfile\ImageFrequencyCheckerForHandmaidsVsAI`)
   で動作する想定。コマンド例ではクォートを忘れない。

## 主要なファイル/責務（リンク）

- アルゴリズム本体 → [src/img_freq_extractor/filter.py](src/img_freq_extractor/filter.py)
- ファイル I/O / 比較画像生成 → [src/img_freq_extractor/compose.py](src/img_freq_extractor/compose.py)
- CLI → [src/img_freq_extractor/cli.py](src/img_freq_extractor/cli.py)
- テスト → [tests/test_filter.py](tests/test_filter.py)

## 開発時によく使うコマンド

```powershell
# 仮想環境作成 & 依存導入
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# テスト
pytest -q

# 動作確認
python -m img_freq_extractor examples\input\sample.png -o examples\output\
```

詳細・規約・設計指針は [.github/copilot-instructions.md](.github/copilot-instructions.md) を参照してください。
