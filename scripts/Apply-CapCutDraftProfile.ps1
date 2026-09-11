param(
    [Parameter(Mandatory)]
    [string]$Profile,

    [Parameter(Mandatory)]
    [string]$DraftDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "Apply-CapCutDraftProfile.py"
python $scriptPath --profile $Profile --draft-dir $DraftDirectory
