# CLAUDE.md

このファイルは Claude / Claude Code 向けのエントリポイントです。
**ガイドラインは [AGENTS.md](AGENTS.md) に集約**しており、GitHub Copilot と Claude の
両方が同じ指示を参照できるようにしています。

- まず [AGENTS.md](AGENTS.md) を読むこと（プロジェクト概要・最重要ルール・主要ファイル）。
- 詳細な設計指針・規約・アンチパターンは
  [.github/copilot-instructions.md](.github/copilot-instructions.md)（7 項目構成）を参照。
- コントリビュート手順は [CONTRIBUTING.md](CONTRIBUTING.md)。
- 帰属・ライセンスは [NOTICE.md](NOTICE.md) / [LICENSE](LICENSE)。

## 最重要ルール（要約）

1. 回答は日本語（識別子は英語）。
2. Upstream [`djmannion/img_freq_web`](https://github.com/djmannion/img_freq_web) (MIT) の
   再実装。コードを丸ごとコピーせず、[NOTICE.md](NOTICE.md) の帰属を維持する。
3. SNS 画像の自動取得・スクレイピング機能は追加しない。
4. 重い依存（PyTorch / TensorFlow / OpenCV 全体）は追加しない。軽量性を保つ。
5. 大規模変更（>200 行 / 既存パブリック API 変更）は事前に計画提案してから実装。
6. 層の責務を混ぜない（`filter.py` はアルゴリズム純粋関数のみ）。

## よく使うコマンド

```bash
pip install -e ".[dev]"   # 依存導入（開発用）
pytest -q                  # テスト
python -m img_freq_extractor <input> -o <out_dir>   # CLI 実行
python -m img_freq_extractor --serve                # ローカル Web UI
```
