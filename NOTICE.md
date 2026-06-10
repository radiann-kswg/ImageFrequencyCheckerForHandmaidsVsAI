# NOTICE

本リポジトリ ImageFrequencyCheckerForHandmaidsVsAI は、以下の Upstream プロジェクトの
アイデア・アルゴリズム・UI 設計を参考に、Python へ再実装したものです。

## Upstream

- 名称  : img_freq_web
- 著者  : Damien Mannion (@djmannion)
- URL   : https://github.com/djmannion/img_freq_web
- Web   : https://www.djmannion.net/img_freq_web/
- ライセンス : MIT License

Upstream のコードを直接コピーしている箇所はありませんが、設計思想
（FFT → 円形カットオフフィルタ → 逆 FFT による空間周波数分解）と
ライセンス（MIT）を継承しています。

## SNS 上の入出力例（着想元）

- https://x.com/dried_gosari/status/2064347491152306560
- https://x.com/dried_gosari/status/2064348024906936621

上記投稿で示された「原本 / 50 / 60 / 70 カットオフ」のレイアウトを参考に、
本ツールでは 3 段階のカットオフを一括出力する CLI を提供します。

## 利用上の注意（重要）

- 本ツールは **私的利用** を前提とした **プライベートブランチ運用** を想定しています。
- 入力に用いる画像は、必ず権利者の許諾を得たもの、あるいは自身が権利を保有する
  ものを使用してください。第三者の著作物を無断で解析・再配布する用途には使えません。
- 本ツールが出力する画像は、入力画像の派生物に該当する可能性があります。配布や
  公開を行う前に、必ず元画像の権利関係・利用規約を確認してください。
- 各種 SNS（X / Twitter 等）の利用規約・スクレイピングポリシーを遵守してください。
  本ツールには SNS 画像の自動取得機能は **含めません**。

## サードパーティライセンス

主要依存（インストール時に取得）:

- NumPy (BSD-3-Clause)
- Pillow (HPND / MIT-CMU)
- 任意: SciPy (BSD-3-Clause)

各ライブラリのライセンス全文は、各配布元を確認してください。
