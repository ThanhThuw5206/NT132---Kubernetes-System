# Install a checksum-pinned portable SDK inside the ignored repository cache.
[CmdletBinding()]
param([switch]$ResumePartial)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$sdkVersion = '592.0.0'
$archiveName = "google-cloud-sdk-$sdkVersion-windows-x86_64-bundled-python.zip"
$expectedSha256 = '65002e0d679fc2ade00163b97637f45656d6fd5250d6f5962e4a1a555f2628ea'
$downloadUrl = "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/$archiveName"
$cacheRoot = Join-Path $repoRoot '.cache'
$sdkParent = Join-Path $cacheRoot "gcloud-$sdkVersion"
$sdkCommand = Join-Path $sdkParent 'google-cloud-sdk\bin\gcloud.cmd'
$sdkVersionFile = Join-Path $sdkParent 'google-cloud-sdk\VERSION'
$completeMarker = Join-Path $sdkParent 'tv3-install-complete.json'

if (-not [Environment]::Is64BitOperatingSystem) {
    throw 'This portable package targets Windows x64.'
}
if ((Test-Path -LiteralPath $completeMarker) -and (Test-Path -LiteralPath $sdkCommand)) {
    if ((Get-Content -LiteralPath $sdkVersionFile -Raw).Trim() -ne $sdkVersion) {
        throw 'Existing SDK version does not match the pinned version; inspect it before continuing.'
    }
    Write-Output "Portable Google Cloud CLI $sdkVersion is already installed: $sdkCommand"
    exit 0
}
if ((Test-Path -LiteralPath $sdkParent) -and -not $ResumePartial) {
    throw "Partial SDK directory already exists; inspect it before retrying: $sdkParent"
}
$downloads = Join-Path $cacheRoot 'downloads'
New-Item -ItemType Directory -Path $downloads -Force | Out-Null
$archivePath = Join-Path $downloads $archiveName
if (-not (Test-Path -LiteralPath $archivePath)) {
    $curlCommand = Get-Command curl.exe -ErrorAction Stop
    & $curlCommand.Source --fail --location --silent --show-error --connect-timeout 15 --max-time 300 --output $archivePath $downloadUrl
    if ($LASTEXITCODE -ne 0) { throw "SDK download failed with exit code $LASTEXITCODE" }
}
$actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) {
    throw "SDK archive checksum mismatch; it has not been extracted. Inspect $archivePath"
}
New-Item -ItemType Directory -Path $sdkParent -Force | Out-Null
$sdkPython = $null
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCommand) {
    $previousUvCache = $env:UV_CACHE_DIR
    try {
        $env:UV_CACHE_DIR = Join-Path $cacheRoot 'uv'
        $foundPython = & $uvCommand.Source python find --offline
        if ($LASTEXITCODE -eq 0) { $sdkPython = ($foundPython | Select-Object -Last 1).Trim() }
    } finally {
        $env:UV_CACHE_DIR = $previousUvCache
    }
}
if ($sdkPython -and (Test-Path -LiteralPath $sdkPython)) {
    @'
import pathlib, shutil, sys, zipfile
archive_path = pathlib.Path(sys.argv[1])
destination = pathlib.Path(sys.argv[2]).resolve()
with zipfile.ZipFile(archive_path) as archive:
    for index, member in enumerate(archive.infolist(), 1):
        target = destination / member.filename
        if not target.resolve().is_relative_to(destination):
            raise ValueError('Archive entry escapes SDK directory')
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                output = target.open('wb')
            except PermissionError:
                target.chmod(0o666)
                output = target.open('wb')
            with archive.open(member) as source, output:
                shutil.copyfileobj(source, output)
        if index % 5000 == 0:
            print('SDK files extracted:', index, flush=True)
'@ | & $sdkPython - $archivePath $sdkParent
    if ($LASTEXITCODE -ne 0) { throw "SDK extraction failed with exit code $LASTEXITCODE" }
} else {
    Expand-Archive -LiteralPath $archivePath -DestinationPath $sdkParent -Force
}
if (-not (Test-Path -LiteralPath $sdkCommand)) { throw 'Downloaded SDK is missing gcloud.cmd.' }
if ((Get-Content -LiteralPath $sdkVersionFile -Raw).Trim() -ne $sdkVersion) { throw 'Unexpected extracted SDK version.' }
@{ version = $sdkVersion; sha256 = $actualSha256; source = $downloadUrl } |
    ConvertTo-Json | Set-Content -LiteralPath $completeMarker -Encoding UTF8
Write-Output "Installed portable Google Cloud CLI ${sdkVersion}: $sdkCommand"
Write-Output 'Run .\scripts\gcloud-local.ps1 --version to verify; no login or cloud operation was performed.'
