<#
.SYNOPSIS
    対生成AI判別用 画像周波数分布解析ツールを、公開用 GitHub リポジトリへ
    「私的履歴を持ち込まないクリーンな初期コミット」として push します。

.DESCRIPTION
    既存のローカルリポジトリ（private/main）には一切触れません。
    現在の作業ツリーのうち「公開対象ファイル（追跡中 + 未追跡だが .gitignore で
    除外されないもの）」だけを一時フォルダへコピーし、そこで新しい git リポジトリを
    init → commit → push します。private/main・その履歴・作業ツリーは無傷のままです。

.PREREQUISITE
    1) 先に GitHub 側で「空の」public リポジトリを作成しておく
       （README / .gitignore / LICENSE の自動生成は付けない）。
       例: https://github.com/radiann-kswg/ImageFrequencyCheckerForHandmaidsVsAI
    2) git が使えること（Git for Windows）。

.NOTES
    リポジトリ名や所有者を変えた場合は $PublicUrl を書き換えてください。
    「コミットまでで良い／push はしない」場合は STEP 5 の push 行をコメントアウト。
#>

$ErrorActionPreference = "Stop"

# ── 設定（必要に応じて変更）────────────────────────────────
$RepoRoot     = "D:\VisualStudio Code Userfile\ImageFrequencyCheckerForHandmaidsVsAI"
$PublicUrl    = "https://github.com/radiann-kswg/ImageFrequencyCheckerForHandmaidsVsAI.git"
$CommitMsg    = "Public release: 対生成AI判別用 画像周波数分布解析ツール (initial public commit)"
$GitUserName  = "radiann-kswg"
# 公開コミットに実メールを残さない GitHub noreply（必要なら自分のメールに変更）
$GitUserEmail = "70576897+radiann-kswg@users.noreply.github.com"
$ExportDir    = Join-Path $env:TEMP "ifc-public-export"
# ──────────────────────────────────────────────────────────

Set-Location -LiteralPath $RepoRoot

# STEP 0: 競合する古いロックがあれば除去（既存リポジトリには他に変更を加えない）
if (Test-Path ".git\index.lock") {
    Remove-Item ".git\index.lock" -Force
    Write-Host "古い .git\index.lock を削除しました。" -ForegroundColor Yellow
}

# STEP 1: 公開対象ファイル一覧を取得
#   追跡中(--cached) + 未追跡だが無視されない(--others --exclude-standard)。
#   .venv / examples/input・output / third_party/img_freq_web / *.egg-info 等は除外されます。
$files = git ls-files --cached --others --exclude-standard | Where-Object { $_ -ne "publish-public.ps1" }
if (-not $files) { throw "公開対象ファイルが見つかりません。RepoRoot を確認してください。" }
Write-Host ("公開対象ファイル数: {0}" -f ($files | Measure-Object).Count)

# STEP 2: クリーンなエクスポート先へコピー
if (Test-Path $ExportDir) { Remove-Item $ExportDir -Recurse -Force }
New-Item -ItemType Directory -Path $ExportDir | Out-Null
foreach ($f in $files) {
    $rel = $f -replace '/', '\'
    $src = Join-Path $RepoRoot $rel
    $dst = Join-Path $ExportDir $rel
    $dstDir = Split-Path $dst -Parent
    if ($dstDir -and -not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    Copy-Item -LiteralPath $src -Destination $dst -Force
}

# STEP 3: 新規 git リポジトリとして初期化（独立した履歴・main ブランチ）
Set-Location -LiteralPath $ExportDir
git init -b main | Out-Null
git config user.name  $GitUserName
git config user.email $GitUserEmail

# STEP 4: 初期コミット
git add -A
git commit -m $CommitMsg

# STEP 5: 公開リポジトリへ push（push 不要なら次の2行をコメントアウト）
git remote add origin $PublicUrl
git push -u origin main

Set-Location -LiteralPath $RepoRoot
Write-Host ""
Write-Host ("完了: {0}" -f ($PublicUrl -replace '\.git$','')) -ForegroundColor Green
Write-Host "ローカルの private/main・履歴・作業ツリーは無傷のままです。" -ForegroundColor Green
Write-Host ("エクスポート内容の確認用フォルダ: {0}" -f $ExportDir) -ForegroundColor DarkGray
