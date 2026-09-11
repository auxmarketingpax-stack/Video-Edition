param(
    [Parameter(Mandatory)]
    [string]$InputFile,

    [string]$OutputFile,
    [int]$MinimumWordsPerLine = 1,
    [int]$MaximumWordsPerLine = 3
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/lib/Common.ps1"
. "$PSScriptRoot/lib/CaptionLayout.ps1"

$inputPath = Resolve-ProjectPath -Path $InputFile
if (-not $OutputFile) {
    $directory = Split-Path -Parent $inputPath
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($inputPath)
    $extension = [System.IO.Path]::GetExtension($inputPath)
    $OutputFile = Join-Path $directory ("{0}.balanced{1}" -f $stem, $extension)
}

$outputPath = Resolve-ProjectPath -Path $OutputFile
$content = Get-Content -LiteralPath $inputPath -Raw -Encoding UTF8
$balancedContent = Convert-SrtContentToBalancedLines -Content $content -MinimumWordsPerLine $MinimumWordsPerLine -MaximumWordsPerLine $MaximumWordsPerLine
Set-Content -LiteralPath $outputPath -Value $balancedContent -Encoding UTF8

Write-Host "Legenda formatada salva em: $outputPath"
