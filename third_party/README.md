# third_party / Upstream の取り扱い

このディレクトリは Upstream の `djmannion/img_freq_web` を **手元で参照するためだけ**
の置き場です。VCS には含めません（`.gitignore` で `third_party/img_freq_web/` を除外）。

## クローン手順 (PowerShell)

```powershell
# 1) GitHub 上で djmannion/img_freq_web を fork する（ブラウザ操作）
#    https://github.com/djmannion/img_freq_web
#
# 2) fork したリポジトリを third_party/ 配下にクローン
git clone https://github.com/<your-account>/img_freq_web.git third_party/img_freq_web

# 3) upstream を追加してフェッチ
cd third_party/img_freq_web
git remote add upstream https://github.com/djmannion/img_freq_web.git
git fetch upstream
cd ../..
```

## なぜ submodule ではなく clone か

- 本リポジトリは **私的利用かつプライベートブランチ運用** を想定。
- Upstream を submodule にすると公開リポジトリへの依存リンクが残るため、
  「参照のみ・配布しない」運用と相性が悪い。
- 必要なときに `third_party/img_freq_web` をクローンし、コード読解・
  検算に使う方針。

## ライセンス

Upstream は MIT License。本リポジトリも MIT を継承（`../LICENSE` 参照）。
帰属表記は `../NOTICE.md` を参照してください。
