<#
.SYNOPSIS
    Publish this project to a public GitHub repository as a clean initial commit
    (no private history is carried over).

.DESCRIPTION
    Your existing local repository (private/main) is NOT touched at all.
    The script copies only the publishable files (tracked + untracked-but-not-ignored)
    into a temp folder, then runs a fresh git init -> commit -> push there.
    private/main, its history, and your working tree stay intact.

.PREREQUISITE
    1) Create an EMPTY public repo on GitHub first
       (do NOT auto-generate README / .gitignore / LICENSE).
       e.g. https://github.com/radiann-kswg/ImageFrequencyCheckerForHandmaidsVsAI
    2) Git for Windows must be installed.

.NOTES
    If you change the repo name/owner, edit $PublicUrl below.
    To "commit only, do not push", comment out the two push lines in STEP 5.
    This file is intentionally ASCII-only to avoid Windows PowerShell codepage issues.
#>

$ErrorActionPreference = "Stop"

# ---- Settings (edit if needed) -------------------------------------------
$RepoRoot     = "D:\VisualStudio Code Userfile\ImageFrequencyCheckerForHandmaidsVsAI"
$PublicUrl    = "https://github.com/radiann-kswg/ImageFrequencyCheckerForHandmaidsVsAI.git"
$CommitMsg    = "Public release: image frequency distribution analysis tool (initial public commit)"
$GitUserName  = "radiann-kswg"
# GitHub noreply email so your real address is not exposed in public commits
$GitUserEmail = "70576897+radiann-kswg@users.noreply.github.com"
$ExportDir    = Join-Path $env:TEMP "ifc-public-export"
# --------------------------------------------------------------------------

Set-Location -LiteralPath $RepoRoot

# STEP 0: Remove a stale index lock if present (no other change to the existing repo)
if (Test-Path ".git\index.lock") {
    Remove-Item ".git\index.lock" -Force
    Write-Host "Removed stale .git\index.lock" -ForegroundColor Yellow
}

# STEP 1: Get the publishable file list
#   tracked (--cached) + untracked-but-not-ignored (--others --exclude-standard).
#   .venv / examples/input|output / third_party/img_freq_web / *.egg-info are excluded.
$files = git ls-files --cached --others --exclude-standard | Where-Object { $_ -ne "publish-public.ps1" }
if (-not $files) { throw "No publishable files found. Check RepoRoot." }
Write-Host ("Publishable files: {0}" -f ($files | Measure-Object).Count)

# STEP 2: Copy them into a clean export folder
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

# STEP 3: Init a brand new git repo (independent history, branch main)
Set-Location -LiteralPath $ExportDir
git init -b main | Out-Null
git config user.name  $GitUserName
git config user.email $GitUserEmail

# STEP 4: Initial commit
git add -A
git commit -m $CommitMsg

# STEP 5: Push to the public repo (comment out the next two lines to skip pushing)
git remote add origin $PublicUrl
git push -u origin main

Set-Location -LiteralPath $RepoRoot
Write-Host ""
Write-Host ("Done: {0}" -f ($PublicUrl -replace '\.git$','')) -ForegroundColor Green
Write-Host "Local private/main, history, and working tree are untouched." -ForegroundColor Green
Write-Host ("Export folder for review: {0}" -f $ExportDir) -ForegroundColor DarkGray
