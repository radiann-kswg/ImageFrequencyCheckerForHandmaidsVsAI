# Web UI ドキュメント

> ⚠️ 本 Web UI は **ローカル実行・私的利用専用** です。
> サーバは既定でループバック (`127.0.0.1`) にしかバインドしません。
> 外部公開（ポートフォワード、リバースプロキシ、Cloudflare Tunnel 等）は
> 行わないでください。SNS 画像の自動取得機能も搭載していません。

---

## 1. できること

1 枚の画像をブラウザからアップロードすると、
[`apply_cutoff()`](../src/img_freq_extractor/filter.py) で複数のカットオフを
適用したフィルタ結果と、横並びの比較画像を
**X / Twitter の投稿カード風レイアウト** で表示します。

- 入力画像 → 「入力カード」（Original のサムネ + メタ情報）
- 各カットオフのフィルタ結果 → 「出力カード」（最大 4 枚は X 風グリッド）
- 比較ストリップ画像（原本 + 各カットオフを横並びにした 1 枚）
- すべての画像セルから PNG をダウンロード可能

CLI でも同じ結果が得られますが、Web UI は
**パラメータをインタラクティブに調整して即座に視覚比較したい用途** に向いています。

---

## 2. 起動方法

### 2.1 前提

- 仮想環境を作成し、開発依存を含めて editable install 済みであること。

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -e ".[dev]"
  ```

### 2.2 サーバ起動

```powershell
# 既定: http://127.0.0.1:4165/
python -m img_freq_extractor --serve

# ポートを変更したい場合
python -m img_freq_extractor --serve --port 8080

# 同一 LAN 内の別端末から見たい場合 (自己責任・推奨しない)
python -m img_freq_extractor --serve --host 0.0.0.0
```

起動すると以下が標準出力に出ます。

```
2026-06-11 07:36:04 INFO img_freq_extractor.server: 対生成AI判別用 画像周波数分布解析ツール Web UI を起動: http://127.0.0.1:4165/
2026-06-11 07:36:04 INFO img_freq_extractor.server: 停止: Ctrl+C
```

ブラウザで上記 URL を開くと UI が表示されます。

### 2.3 停止

ターミナルで `Ctrl + C`。

### 2.4 コンソールスクリプト

`pip install -e ".[dev]"` 後は次のショートカットも使えます。

```powershell
img-freq-webui          # --serve と同等 (既定 127.0.0.1:4165)
```

---

## 3. 画面構成

```
┌──────────────────────────────────────────────────┐
│  対生成AI判別用 画像周波数分布解析ツール — Web UI    │
│  ⚠️ 私的利用かつローカル実行専用                  │
├──────────────────────────────────────────────────┤
│  1. 画像と設定                                    │  ← 入力フォーム
│    [画像ファイル]                                 │
│    [モード]  [カットオフ％]                       │
│    [ソフトエッジ] [bandpass 外側 ％ (条件表示)]   │
│    (フィルタ適用) (リセット)  ステータス           │
├──────────────────────────────────────────────────┤
│  2. 結果（X / Twitter 風カード表示）              │
│                                                  │
│  ┌─ 入力カード ────────────────────────────────┐ │
│  │ [入] 入力画像  Input    YYYY/MM/DD HH:MM    │ │
│  │ @local · sample.png · 1024×1024 px          │ │
│  │ ┌────────────────────────────────────────┐ │ │
│  │ │            (Original 画像)             │ │ │
│  │ └────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌─ 出力カード ────────────────────────────────┐ │
│  │ [出] フィルタ結果 Output  YYYY/MM/DD HH:MM  │ │
│  │ mode = highpass / cutoffs = [50, 60, 70]    │ │
│  │ ┌─────┬─────┐                              │ │
│  │ │ 50% │ 60% │   ← 1〜4 枚は X 風グリッド   │ │
│  │ ├─────┼─────┤                              │ │
│  │ │ 70% │ ... │                              │ │
│  │ └─────┴─────┘                              │ │
│  │ 比較ストリップ:                              │ │
│  │ ┌──────────────────────────────────────────┐│ │
│  │ │  原本 | 50% | 60% | 70%  (横並び 1 枚)   ││ │
│  │ └──────────────────────────────────────────┘│ │
│  │ (⬇ 比較画像を保存)                          │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

各画像セル右下の **「⬇ 保存」** リンクから PNG として個別ダウンロードできます。

---

## 4. フォーム入力項目

| 項目                 |      必須       | 形式 / 既定                                              | 説明                                                                      |
| -------------------- | :-------------: | -------------------------------------------------------- | ------------------------------------------------------------------------- |
| 画像ファイル         |       ✅        | PNG / JPEG / WebP / BMP / TIFF（最大 20 MiB）            | 入力 1 枚。                                                               |
| モード               |       ✅        | `highpass`（既定） / `lowpass` / `bandpass`              | フィルタ種別。                                                            |
| カットオフ％         |       ✅        | カンマ／空白区切り。既定 `50, 60, 70`。各値は `(0, 100]` | ナイキスト半径（短辺の半分）に対する割合。複数指定可。                    |
| ソフトエッジ (px)    |        —        | float ≥ 0。既定 `0`                                      | 円形マスク縁のぼかし。リンギング軽減用。                                  |
| bandpass 外側 ％     | bandpass 時のみ | `(0, 100]`                                               | `bandpass` 選択時のみ表示。内側カットオフ ＜ 外側 ％。                    |
| 正規化               |        —        | チェックボックス。既定 ON                                | highpass/bandpass 出力を視認しやすく引き伸ばす（色相保持）。詳細は §4.1。 |
| 二値化               |        —        | チェックボックス。既定 OFF                               | 出力画像を白黒 (0/255) にする。X 投稿の 2〜4 枚目を再現。詳細は §4.3。    |
| 二値化 閾値方法      |        —        | `otsu`（既定） / `fixed`                                 | `otsu` は大津の自動閾値、`fixed` は固定値。                               |
| 二値化 閾値          |  fixed 時のみ   | `[0, 255]`。既定 `127`                                   | `fixed` 選択時のみ使用。                                                  |
| 二値化 白黒反転      |        —        | チェックボックス。既定 OFF                               | 0/255 を反転（黒地 → 白地）。                                             |
| 情報量マップ 指標    |        —        | `both`（既定） / `local_contrast` / `luminance` / `none` | Zenn 記事由来の追加可視化。詳細は §4.2。                                  |
| 情報量マップ 窓 (px) |        —        | int ≥ 2。既定 `32`                                       | `local_contrast` のスライディング窓サイズ。                               |
| ヒートマップ不透明度 |        —        | `[0, 1]`。既定 `0.5`                                     | オーバーレイ時のアルファ。0 で原画のみ、1 でヒートマップのみ。            |

### モードの意味（再掲）

- **highpass**: 中〜高周波だけ残す（X 投稿の用例。AI / 手描き比較用）。
- **lowpass**: 低周波だけ残す。輪郭をぼかした画像。
- **bandpass**: 内側 ％ 〜 外側 ％ の帯域だけ残す。中間周波数解析向け。

### 4.1 「正規化」について（白く潰れる問題の対策）

`apply_cutoff` の素の出力は、FFT 後に **mean を戻して `[0, 255]` にクリップ** する
仕様です。highpass / bandpass では振幅が小さく、結果が
**入力画像の平均輝度の近傍にギュッと潰れる** ため、明るい画像では
**ほぼ白一色**、暗い画像では **ほぼ黒一色** に見えます。

**正規化 ON**（既定）では、フィルタ結果の偏差を 99.5 パーセンタイル基準で
`[0, 255]` へ引き伸ばします。重要な性質:

- **色相を保持する**: RGB 全チャネルで **共通スケール** を使うため、
  特定チャネルだけ強調されることがなく hue が崩れない。
- **lowpass では無視**: 低周波（DC 含む）はそもそも視認可能なので、
  既定動作は素の出力のまま。
- CLI でも `--normalize` フラグで有効化可能（既定は OFF、互換性のため）。

色味そのものを忠実に検証したい用途では OFF にしてください。

### 4.2 情報量マップ（Zenn 記事の軽量版）

参考: [抹茶もなか「AI を使ってイラストの情報量を可視化できないか試してみた」](https://zenn.dev/mattyamonaca/articles/d3d7acbd796733)

元記事は Meta の Segment Anything (SAM) を使って **セグメント領域の密集度** を
ヒートマップ化していますが、本リポジトリの方針 (PyTorch / OpenCV を入れない) の
ため、**NumPy だけで完結する軽量代替** を 2 つ実装しています。

| 指標             | アルゴリズム                                       | 意味                                                     |
| ---------------- | -------------------------------------------------- | -------------------------------------------------------- |
| `luminance`      | BT.601 で RGB → 輝度                               | 明度マップ（明るい領域ほど赤）。                         |
| `local_contrast` | sliding-window 内の輝度標準偏差（積分画像で O(N)） | 線が密／テクスチャが豊富な領域ほど赤。情報密度の近似値。 |

可視化:

- 正規化値を **jet カラーマップ**（青=低 → 赤=高）で着色
- 原画にアルファ合成した **Overlay** と、ヒートマップ単体の **Heatmap** を
  両方表示

UI では「指標」プルダウンで `none` を選ぶと情報量カードは非表示になります。

### 4.3 二値化（白黒化）

参考: [@dried_gosari のポスト](https://x.com/dried_gosari/status/2064347491152306560) の
2〜4 枚目（ハイパス結果を白黒化した画像）を再現するためのオプションです。

- 「二値化を有効にする」を ON にすると、各カットオフ画像をグレースケール化した
  あとに **閾値で 0/255 に二分** します。
- **閾値方法**:
  - `otsu`（既定）: 大津の自動閾値。前景／背景のクラス間分散を最大化する閾値を
    画像ごとに自動で決定。フィルタ後のエッジ画像でも自然に効きます。
  - `fixed`: 指定した固定値（0〜255）で二分。閾値方法が `fixed` のときだけ
    閾値フィールドが出現します。
- 「白黒を反転」を ON にすると、白黒が反転します（黒地 → 白地）。
- 出力ファイル名にはサフィックス `_bin` が付きます
  （例: `sample_highpass_cutoff60_bin.png`）。
- CLI でも `--binarize` フラグで同じ動作が得られます
  （`--binarize-method otsu|fixed` / `--binarize-threshold N` / `--binarize-invert`）。

---

## 5. API 仕様

UI が裏で叩いている HTTP API です。`curl` 等から直接呼べます。

### 5.1 `GET /api/health`

サーバ稼働確認用。認証なし。

```json
{ "status": "ok", "version": "0.1.0" }
```

### 5.2 `POST /api/process`

`multipart/form-data` で画像と設定を受け取り、フィルタ結果と情報量マップを
Base64 PNG（data URL）で返します。

| フィールド           | 型     |      必須       | 説明                                                      |
| -------------------- | ------ | :-------------: | --------------------------------------------------------- |
| `image`              | file   |       ✅        | 画像本体。最大 20 MiB。                                   |
| `cutoffs`            | string |        —        | `"50,60,70"` 形式。既定 `"50,60,70"`。                    |
| `mode`               | string |        —        | `highpass` / `lowpass` / `bandpass`。既定 `highpass`。    |
| `soft_edge`          | number |        —        | px。既定 `0`。                                            |
| `high_cutoff`        | number | bandpass 時のみ | `(0, 100]`。                                              |
| `normalize`          | bool   |        —        | `"1"`/`"0"` 等。既定 `"1"`。表示用コントラスト正規化。    |
| `binarize`           | bool   |        —        | `"1"`/`"0"` 等。既定 `"0"`。出力画像を白黒化。            |
| `binarize_method`    | string |        —        | `otsu`（既定）/ `fixed`。                                 |
| `binarize_threshold` | number |        —        | `[0, 255]`。`fixed` の閾値。                              |
| `binarize_invert`    | bool   |        —        | `"1"`/`"0"` 等。既定 `"0"`。白黒反転。                    |
| `info_map`           | string |        —        | `none`/`luminance`/`local_contrast`/`both`。既定 `both`。 |
| `info_window`        | int    |        —        | 既定 `32`。`local_contrast` の窓サイズ (px)。             |
| `info_alpha`         | number |        —        | 既定 `0.5`。情報量オーバーレイの不透明度 `[0, 1]`。       |

**成功レスポンス (200)**:

```jsonc
{
  "mode": "highpass",
  "cutoffs": [50.0, 60.0, 70.0],
  "soft_edge_px": 0.0,
  "high_cutoff_percent": null,
  "normalize": true,
  "binarize": false,
  "binarize_method": "otsu",
  "binarize_threshold": null,
  "binarize_invert": false,
  "info_map": "both",
  "info_window": 32,
  "info_alpha": 0.5,
  "input": {
    "filename": "sample.png",
    "width": 1024,
    "height": 1024,
    "data_url": "data:image/png;base64,iVBORw0KGgo...",
  },
  "filtered": [
    {
      "cutoff": 50.0,
      "label": "highpass cutoff 50%",
      "data_url": "data:image/png;base64,...",
    },
    {
      "cutoff": 60.0,
      "label": "highpass cutoff 60%",
      "data_url": "data:image/png;base64,...",
    },
    {
      "cutoff": 70.0,
      "label": "highpass cutoff 70%",
      "data_url": "data:image/png;base64,...",
    },
  ],
  "comparison": {
    "label": "comparison strip",
    "data_url": "data:image/png;base64,...",
  },
  "info_maps": [
    {
      "metric": "luminance",
      "label": "Luminance（明度マップ）",
      "overlay_data_url": "data:image/png;base64,...",
      "heatmap_data_url": "data:image/png;base64,...",
    },
    {
      "metric": "local_contrast",
      "label": "Local Contrast（窓 32px の輝度標準偏差）",
      "overlay_data_url": "data:image/png;base64,...",
      "heatmap_data_url": "data:image/png;base64,...",
    },
  ],
}
```

**エラーレスポンス**:

| ステータス | 例                                                          | 意味                       |
| ---------- | ----------------------------------------------------------- | -------------------------- |
| 400        | `{"error": "'image' フィールド（画像ファイル）が必要です"}` | 不正な入力                 |
| 413        | `{"error": "リクエストが大きすぎます (>20971520 bytes)"}`   | 上限超過                   |
| 415        | `{"error": "multipart/form-data が必要です"}`               | Content-Type 不正          |
| 500        | `{"error": "内部エラー: ..."}`                              | 想定外（詳細はサーバログ） |

### 5.3 curl 例

```powershell
curl.exe -X POST "http://127.0.0.1:4165/api/process" `
  -F "image=@examples\input\sample.png" `
  -F "cutoffs=50,60,70" `
  -F "mode=highpass" -o result.json
```

---

## 6. アーキテクチャ概要

```
┌────────────────────────┐
│ Browser (バニラ JS)    │
│   index.html / app.js  │
└──────────┬─────────────┘
           │ POST /api/process (multipart)
           ▼
┌────────────────────────┐
│ server.py              │  ← 標準 http.server のみ
│   _parse_multipart()   │  ← 自前 multipart パーサ (cgi 不使用)
│   _process_request()   │
└──────────┬─────────────┘
           ▼
┌────────────────────────┐
│ filter.apply_cutoff()  │  ← 純粋関数 (numpy のみ)
│ compose.make_strip()   │
│ analyze.overlay_*()    │  ← 情報量マップ (NumPy 完結)
└────────────────────────┘
```

- **追加依存ゼロ**: Web UI は Python 標準ライブラリ + 既存依存（numpy / Pillow）
  のみで動作します。Flask / FastAPI / Node.js は使用しません。
- **層分離は厳守**: `server.py` は薄いブリッジで、`filter.py` / `compose.py`
  の純粋関数を呼ぶだけ。アルゴリズム側に Web 由来のコードは入りません。
- **フロントエンドはバニラ HTML/CSS/JS (ES Modules)**。フレームワークは使いません。
- **`cgi` を使わない**: Python 3.13+ で `cgi` が削除されたため、最小限の
  multipart パーサ（[server.py](../src/img_freq_extractor/server.py) の
  `_parse_multipart`）を自前実装しています。

---

## 7. セキュリティ・運用上の注意

- **既定で `127.0.0.1` バインド**。`--host 0.0.0.0` を付けない限り外部から
  到達できません。
- **アップロード上限 20 MiB**（`server.py` の `MAX_UPLOAD_BYTES` で定義）。
- **`Cache-Control: no-store`** を JSON 応答に付与。
- **パストラバーサル防止**: 静的ファイル配信は `web/static/` 配下に解決される
  パスのみ許可。
- **認証なし**。ローカル前提のため。外部公開する場合（**推奨しません**）は
  必ずリバースプロキシ側で認証を入れてください。
- **ログ**: 各リクエストは Python の `logging` (INFO) に出力されます。
  アップロード画像そのものはログに残しません。

---

## 8. トラブルシューティング

| 症状                                         | 対処                                                                                                             |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **出力画像が真っ白／真っ黒に見える**         | 「表示用にコントラスト正規化」を ON にする。素の highpass/bandpass 出力は平均輝度近傍に潰れる仕様。詳細は §4.1。 |
| `pytest: コマンドが見つかりません`           | `python -m pytest -q` を使うか、venv をアクティブ化。                                                            |
| `OSError: [Errno 98] Address already in use` | 別ポートを指定 (`--port 8080`)。                                                                                 |
| ブラウザに「サーバに接続できません」表示     | サーバが落ちている。ターミナルでログを確認。                                                                     |
| 「リクエストが大きすぎます」                 | 20 MiB 以下にリサイズするか、CLI 版を使う。                                                                      |
| bandpass で 400 エラー                       | `high_cutoff > cutoff` を満たしているか確認。                                                                    |
| 文字化け / 表示崩れ                          | ブラウザのキャッシュをクリア (Ctrl + F5)。                                                                       |
| 情報量マップが粗い / 細かすぎる              | 「窓サイズ」を調整。短辺の 1/16〜1/8 が目安。                                                                    |

---

## 9. 関連ファイル

- サーバ本体: [src/img_freq_extractor/server.py](../src/img_freq_extractor/server.py)
- フロントエンド: [src/img_freq_extractor/web/static/](../src/img_freq_extractor/web/static/)
  - [index.html](../src/img_freq_extractor/web/static/index.html)
  - [style.css](../src/img_freq_extractor/web/static/style.css)
  - [app.js](../src/img_freq_extractor/web/static/app.js)
- アルゴリズム本体: [src/img_freq_extractor/filter.py](../src/img_freq_extractor/filter.py)
- 情報量マップ実装: [src/img_freq_extractor/analyze.py](../src/img_freq_extractor/analyze.py)
- CLI: [src/img_freq_extractor/cli.py](../src/img_freq_extractor/cli.py)
- テスト: [tests/test_server.py](../tests/test_server.py) / [tests/test_filter.py](../tests/test_filter.py) / [tests/test_analyze.py](../tests/test_analyze.py)
