#!/usr/bin/env pwsh
# BLOQUE 67: recover the local-only documents into the reset-to-origin/master
# state. Re-applies ONLY the files that don't conflict with remote BLOQUE 73.
# SKIPS oval revert (GOLIATH code refactored beyond our patch) and test fix
# (test fails for unrelated tiles-path reason).

Set-Location F:\AI\MM\void-hunter

# Verify the right baseline
$head = git log --oneline -1
Write-Host "Baseline HEAD: $head"
if (-not ($head -match "31815ee")) {
    Write-Error "Expected HEAD at BLOQUE 73 (31815ee). Aborting."
    exit 1
}

# 1. Restore Category A new files (just copy from commit content)
$docsToAdd = @(
    @{Hash='f3039b9'; Path='docs/superpowers/specs/2026-10-20-v1-4-ship-as-is-design.md'; Out='docs/superpowers/specs/2026-10-20-v1-4-ship-as-is-design.md'},
    @{Hash='9a12c2e'; Path='docs/superpowers/plans/2026-10-20-v1-4-ship-as-is.md';          Out='docs/superpowers/plans/2026-10-20-v1-4-ship-as-is.md'},
    @{Hash='6694054'; Path='docs/OPERATIONS.md';                                          Out='docs/OPERATIONS.md'},
    @{Hash='af9ef7d'; Path='docs/KNOWN_ISSUES.md';                                       Out='docs/KNOWN_ISSUES.md'}
)

# Make sure target dirs exist
New-Item -Path docs/superpowers/specs -ItemType Directory -Force | Out-Null
New-Item -Path docs/superpowers/plans -ItemType Directory -Force | Out-Null

foreach ($f in $docsToAdd) {
    Write-Host "  Restoring $($f.Path) from $($f.Hash)"
    git show "$($f.Hash):$($f.Path)" | Out-File -FilePath $f.Out -Encoding UTF8
}

# 2. Update .gitignore with our session patterns (append, do NOT reset)
$gitignoreAdditions = @'

# BLOQUE 67+ session debug logs
*.pytest_*.txt
*.smoke_*.txt
*.finalverify.txt
*.shield_*.txt
*.diff_*.txt
*.main_smoke.txt
.tests_*.txt
tests_*.txt
tests_dbg.txt
tests_full.txt
tests_run.txt
tests_baseline.txt

# BLOQUE 67+ temp artifacts
tmp_*.json
output/
.Trash
.Trash/

# BLOQUE 67+ one-off capture artefacts (Mavis session debug files)
luffy_*.png

# BLOQUE 67+ task-step debug logs (left over from agent runs)
.task*_step*.out
.task*_step*_dbg*.out

# BLOQUE 67+ local github token (must NEVER be committed)
github_token.txt
github_token

# BLOQUE 67+ boss-sprite backplate leftover dirs
Assets/sprites/bosses/goliath/_backplate/
'@
Add-Content -Path .gitignore -Value $gitignoreAdditions -Encoding UTF8

# 3. Stage everything (no commit — that's the next task)
git add docs/OPERATIONS.md docs/KNOWN_ISSUES.md docs/superpowers/specs/2026-10-20-v1-4-ship-as-is-design.md docs/superpowers/plans/2026-10-20-v1-4-ship-as-is.md .gitignore

# 4. Verify
Write-Host ""
Write-Host "=== Staged files (will be the next commit) ==="
git diff --cached --stat
Write-Host ""
Write-Host "=== Working tree ==="
git status --short | Select-Object -First 20
