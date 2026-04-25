$ErrorActionPreference = "Stop"

$versionFile = Join-Path $PSScriptRoot "app_version.py"
$versionText = Get-Content -LiteralPath $versionFile -Raw

function Get-VersionValue([string]$name) {
    $pattern = '(?m)^' + [regex]::Escape($name) + '\s*=\s*"([^"]+)"\s*$'
    $match = [regex]::Match($versionText, $pattern)
    if (-not $match.Success) {
        throw "Could not find $name in app_version.py"
    }
    return $match.Groups[1].Value
}

$appName    = Get-VersionValue "APP_NAME"
$appVersion = Get-VersionValue "APP_VERSION"
$publisher  = Get-VersionValue "APP_PUBLISHER"
$exeName    = Get-VersionValue "APP_EXE_NAME"
$appId      = Get-VersionValue "APP_ID"

$installerPath = "installer-dist\YappForever-Setup-$appVersion.exe"
$tag           = "v$appVersion"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  Building $appName $appVersion"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: PyInstaller ──────────────────────────────────
Write-Host "`n[1/3] Running PyInstaller..."
python -m PyInstaller YappForever.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

# ── Step 2: Inno Setup ──────────────────────────────────
Write-Host "`n[2/3] Building installer with Inno Setup..."
$isccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$isccPath = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $isccPath) {
    throw "Inno Setup (ISCC.exe) not found. Download from https://jrsoftware.org/isdl.php"
}

& $isccPath `
    "/DMyAppName=$appName" `
    "/DMyAppVersion=$appVersion" `
    "/DMyAppPublisher=$publisher" `
    "/DMyAppExeName=$exeName" `
    "/DMyAppId=$appId" `
    "YappForeverInstaller.iss"

if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }

Write-Host "`n  Installer: $installerPath ($('{0:N1}' -f ((Get-Item $installerPath).Length / 1MB)) MB)"

# ── Step 3: GitHub Release ───────────────────────────────
Write-Host "`n[3/3] Publishing GitHub release $tag..."

$ghInstalled = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghInstalled) {
    Write-Host "`n  gh CLI not found — skipping auto-publish."
    Write-Host "  Install from: https://cli.github.com"
    Write-Host "  Then run manually:"
    Write-Host "    gh release create $tag $installerPath --title `"$appName $appVersion`" --generate-notes"
} else {
    # Fail loudly if the tag already exists
    $existingRelease = gh release view $tag 2>&1
    if ($LASTEXITCODE -eq 0) {
        throw "Release $tag already exists on GitHub. Bump the version in app_version.py first."
    }

    gh release create $tag $installerPath `
        --title "$appName $appVersion" `
        --generate-notes

    if ($LASTEXITCODE -ne 0) { throw "gh release create failed." }

    Write-Host "`n  Released: https://github.com/azdhan/yapp-forever/releases/tag/$tag"
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  Done."
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
