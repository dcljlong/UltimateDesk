$ErrorActionPreference = "Stop"

Set-Location (Resolve-Path "$PSScriptRoot\..")

$results = New-Object System.Collections.Generic.List[string]
$failed = $false

function Add-Pass($name) {
    Write-Host "PASS - $name" -ForegroundColor Green
    $results.Add("- [x] $name")
}

function Add-Fail($name, $message) {
    Write-Host "FAIL - $name" -ForegroundColor Red
    Write-Host $message -ForegroundColor Red
    $script:failed = $true
    $results.Add("- [ ] $name — FAILED: $message")
}

function Run-Check($name, $scriptBlock) {
    try {
        & $scriptBlock
        Add-Pass $name
    } catch {
        Add-Fail $name $_.Exception.Message
    }
}

Write-Host "=== UltimateDesk Manufacturing Pack V1 PowerShell QA ===" -ForegroundColor Cyan

Run-Check "backend/server.py passes py_compile" {
    python -m py_compile ".\backend\server.py"
}

Run-Check "manufacturing pack smoke test passes" {
    python ".\tools\manufacturing_pack_smoke_test.py"
}

Run-Check "temporary smoke outputs removed" {
    Remove-Item ".\tmp_smoke_outputs" -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path ".\tmp_smoke_outputs") {
        throw "tmp_smoke_outputs still exists"
    }
}

Run-Check "frontend build compiles successfully" {
    Set-Location ".\frontend"
    try {
        if (Test-Path ".\yarn.lock") {
            yarn build
        } else {
            npm run build
        }
    } finally {
        Set-Location ".."
    }
}

Run-Check "git diff check passes" {
    git diff --check
}

Run-Check "manufacturing pack source markers present" {
    $raw = Get-Content ".\backend\server.py" -Raw
    $markers = @(
        "Calculated hardware quantities",
        "Approval / Release Sign-Off",
        "Required review sign-offs",
        "Exploded Assembly View",
        "Joint Detail Diagrams",
        "Part Marking / Orientation",
        "Cut Part Labels",
        "Assembly Details",
        "Hardware / Fastener Schedule",
        "draw_approval_signoff_page()",
        "draw_exploded_assembly_page()",
        "draw_joint_detail_diagrams_page()",
        "draw_part_marking_page()",
        "draw_cut_part_labels_page()"
    )

    foreach ($marker in $markers) {
        if ($raw -notmatch [regex]::Escape($marker)) {
            throw "Missing source marker: $marker"
        }
    }
}

Run-Check "local branch is ahead of origin/main" {
    $ahead = git rev-list --count "origin/main..HEAD"
    if ([int]$ahead -lt 1) {
        throw "Expected local commits ahead of origin/main"
    }
}

$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$status = if ($failed) { "FAILED" } else { "PASSED" }

$report = @"
# UltimateDesk Manufacturing Pack V1 QA Checklist

Status: $status  
Generated: $now  
Target tag: manufacturing-pack-v1

## Automated PowerShell QA Results

$($results -join "`n")

## Manual live checks after milestone push

- [ ] Render deploys successfully
- [ ] Live /api/review-drawings/pdf generates PDF
- [ ] Browser Export → Design Review Drawings downloads
- [ ] Live designer page does not go blank
- [ ] Final tag created: manufacturing-pack-v1

## Release note

Only push/tag `manufacturing-pack-v1` after all automated checks pass and the live proof is confirmed.
"@

Set-Content ".\docs\qa\manufacturing-pack-v1-checklist.md" $report -Encoding UTF8

Write-Host ""
Write-Host "QA report written to:" -ForegroundColor Cyan
Write-Host "docs\qa\manufacturing-pack-v1-checklist.md"

if ($failed) {
    throw "Manufacturing Pack V1 QA failed. Do not push."
}

Write-Host ""
Write-Host "PASS - Manufacturing Pack V1 QA completed" -ForegroundColor Green
