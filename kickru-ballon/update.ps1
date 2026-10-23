# Updates this folder to the latest code from GitHub.
# Keeps: collected data (data\raw, data\recon, data\runs), browser profile (.pw-profile), your config.json.
# Called by run.bat. ASCII only on purpose (Windows PowerShell 5.1 reads files without BOM as ANSI).
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repo   = 'Manners523/Kangwon'
$branch = 'claude/great-albattani-2npld4'
$dest   = (Get-Location).Path
$tmp    = Join-Path $env:TEMP ('kickru-update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null

try {
    $zip = Join-Path $tmp 'repo.zip'
    Invoke-WebRequest -Uri "https://github.com/$repo/archive/refs/heads/$branch.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath (Join-Path $tmp 'x') -Force

    $root = Get-ChildItem (Join-Path $tmp 'x') -Directory | Select-Object -First 1
    $src  = Join-Path $root.FullName 'kickru-ballon'
    if (-not (Test-Path $src)) { throw 'kickru-ballon folder not found in the downloaded archive' }

    # Never touch collected data or the browser profile. run.bat / update.ps1 are not overwritten while running.
    $skipDirs = @('data\raw', 'data\recon', 'data\runs', '.pw-profile', '.venv', '__pycache__') | ForEach-Object { Join-Path $dest $_ }
    robocopy $src $dest /E /XD $skipDirs /XF run.bat update.ps1 .career_budget.json config.json /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "copy failed (robocopy exit code $LASTEXITCODE)" }

    # config.json: only create it if missing, so your edited limits are kept.
    $cfgDest = Join-Path $dest 'bot\config.json'
    if (-not (Test-Path $cfgDest)) { Copy-Item (Join-Path $src 'bot\config.json') $cfgDest }

    $version = 'unknown'
    try {
        $sha = (Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/commits/$branch" -Headers @{ 'User-Agent' = 'kickru-updater' }).sha
        $version = $sha.Substring(0, 7)
    } catch { }
    Set-Content -Path (Join-Path $dest 'VERSION.txt') -Value $version
    Write-Host "Updated. Version: $version"
}
finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
