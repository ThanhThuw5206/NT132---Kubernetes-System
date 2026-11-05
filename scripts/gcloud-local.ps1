# Use the portable SDK with isolated ignored config; do not change the user's PATH.
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$GcloudArguments
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$sdkCommand = Join-Path $repoRoot '.cache\gcloud-592.0.0\google-cloud-sdk\bin\gcloud.cmd'
if (-not (Test-Path -LiteralPath $sdkCommand)) {
    throw 'Portable SDK is missing. Run .\scripts\install-gcloud-local.ps1 first.'
}
$completeMarker = Join-Path $repoRoot '.cache\gcloud-592.0.0\tv3-install-complete.json'
if (-not (Test-Path -LiteralPath $completeMarker)) {
    throw 'Portable SDK extraction is incomplete. Check the installer before running gcloud.'
}
$sdkConfig = Join-Path $repoRoot '.cache\tv3-gcloud-config'
New-Item -ItemType Directory -Path $sdkConfig -Force | Out-Null
$previous = @{}
$settings = @{
    CLOUDSDK_CONFIG = $sdkConfig
    CLOUDSDK_CORE_DISABLE_USAGE_REPORTING = 'true'
    CLOUDSDK_COMPONENT_MANAGER_DISABLE_UPDATE_CHECK = 'true'
}
foreach ($setting in $settings.Keys) {
    $previous[$setting] = [Environment]::GetEnvironmentVariable($setting, 'Process')
    [Environment]::SetEnvironmentVariable($setting, $settings[$setting], 'Process')
}
try {
    & $sdkCommand @GcloudArguments
    $gcloudExitCode = $LASTEXITCODE
} finally {
    foreach ($setting in $settings.Keys) {
        [Environment]::SetEnvironmentVariable($setting, $previous[$setting], 'Process')
    }
}
exit $gcloudExitCode
