param(
    [string]$Profile = "config/profiles/default.json",
    [Parameter(Mandatory)]
    [string]$AnchorName,
    [string]$Description = "",
    [int]$DelaySeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lib/Common.ps1"
. "$PSScriptRoot/lib/CapCut.Automation.ps1"

$profileConfig = Load-ProfileConfig -ProfilePath $Profile

Write-Host "Posicione o mouse sobre a âncora '$AnchorName'."
Write-Host "Captura em $DelaySeconds segundo(s)..."
Start-Sleep -Seconds $DelaySeconds

$anchor = Save-CalibrationAnchor -Profile $profileConfig -AnchorName $AnchorName -Description $Description

Write-Host ""
Write-Host "Âncora salva em: $($profileConfig.capcut.calibrationFile)"
Write-Host "Nome: $AnchorName"
Write-Host "X: $($anchor.x)"
Write-Host "Y: $($anchor.y)"
