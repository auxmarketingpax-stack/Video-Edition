param(
    [string]$Profile = "config/profiles/default.json",
    [string]$Workflow = "config/workflows/capcut.full.json",
    [switch]$SkipPrepare,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lib/Common.ps1"
. "$PSScriptRoot/lib/VideoPrep.ps1"
. "$PSScriptRoot/lib/CapCut.Automation.ps1"
. "$PSScriptRoot/lib/CaptionLayout.ps1"

$profileConfig = Load-ProfileConfig -ProfilePath $Profile

if ($SkipPrepare) {
    $preparedFolder = Join-Path $profileConfig.workspaceRoot $profileConfig.preparation.stagingFolder
    if (-not (Test-Path -LiteralPath $preparedFolder)) {
        throw "A pasta preparada nao existe: $preparedFolder"
    }
    $clips = @(Get-ChildItem -LiteralPath $preparedFolder -File | Sort-Object Name)
}
else {
    Write-Section -Message "Preparando midia"
    $prepared = Invoke-PrepareCapCutMedia -Profile $profileConfig
    $preparedFolder = $prepared.PreparedFolder
    $clips = @($prepared.Clips)
}

$context = @{
    preparedFolder = $preparedFolder
    audioVolumeDb = [string]$profileConfig.capcut.audio.volumeDb
    sourceLanguage = [string]$profileConfig.capcut.captions.sourceLanguage
    bilingualMode = [string]$profileConfig.capcut.captions.bilingualMode
    profileName = [string]$profileConfig.name
    clipCount = $clips.Count
    transitionCount = [Math]::Max(0, $clips.Count - 1)
    effectCount = @($profileConfig.capcut.effects).Count
    captionMinWordsPerLine = if ($profileConfig.capcut.captions.ContainsKey("minWordsPerLine")) { [int]$profileConfig.capcut.captions.minWordsPerLine } else { 1 }
    captionMaxWordsPerLine = if ($profileConfig.capcut.captions.ContainsKey("maxWordsPerLine")) { [int]$profileConfig.capcut.captions.maxWordsPerLine } else { 3 }
}

Write-Section -Message "Executando automacao do CapCut"
Invoke-CapCutWorkflow -Profile $profileConfig -WorkflowPath $Workflow -Context $context -Interactive:(-not $NonInteractive)
