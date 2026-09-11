param(
    [string]$Profile = "config/profiles/default.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lib/Common.ps1"
. "$PSScriptRoot/lib/VideoPrep.ps1"

$profileConfig = Load-ProfileConfig -ProfilePath $Profile

Write-Section -Message "Preparando mídia para o CapCut"
Write-Host "Perfil: $($profileConfig.name)"
Write-Host "Origem: $($profileConfig.sourceFolder)"
Write-Host "Workspace: $($profileConfig.workspaceRoot)"

$result = Invoke-PrepareCapCutMedia -Profile $profileConfig

Write-Host ""
Write-Host "Clipes preparados: $($result.Clips.Count)"
Write-Host "Pasta pronta para importação: $($result.PreparedFolder)"
Write-Host "Manifesto CSV: $($result.ManifestCsv)"
Write-Host "Manifesto JSON: $($result.ManifestJson)"
Write-Host "Ordem de importação: $($result.ImportOrder)"
