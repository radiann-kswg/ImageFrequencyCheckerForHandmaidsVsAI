# examples

このディレクトリは入出力サンプル置き場です。

## 想定構成

```
examples/
├── input/    # 解析したい画像（権利関係を確認したものに限定）
└── output/   # CLI が生成するフィルタ結果
```

`input/` と `output/` は `.gitignore` で除外しています（誤公開防止）。

## 使い方

```powershell
python -m img_freq_extractor examples/input/your_image.png -o examples/output/
```

X 投稿で示されたレイアウトを再現する場合は、生成された
`*_compare.png` が「原本 / 50 / 60 / 70」を横並びにした 1 枚です。
