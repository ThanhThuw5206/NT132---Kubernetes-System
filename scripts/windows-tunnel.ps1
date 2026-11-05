param(
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [string]$Zone = "asia-southeast1-a"
)
$ErrorActionPreference = "Stop"
& gcloud compute ssh cp-01 "--project=$ProjectId" "--zone=$Zone" --tunnel-through-iap -- -N -L 8443:127.0.0.1:8443 -L 8080:127.0.0.1:8080 -L 20001:127.0.0.1:20001
if ($LASTEXITCODE -ne 0) { throw "SSH tunnel stopped with exit code $LASTEXITCODE" }
