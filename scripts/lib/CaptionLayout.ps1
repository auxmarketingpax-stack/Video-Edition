Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/Common.ps1"

function Get-CaptionTokens {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $normalized = ($Text -replace "\r\n", " " -replace "\n", " " -replace "\s+", " ").Trim()
    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return @()
    }

    return @($normalized -split " " | Where-Object { $_ -ne "" })
}

function Get-TokenGroupLength {
    param(
        [Parameter(Mandatory)]
        [string[]]$Tokens
    )

    if (-not $Tokens -or $Tokens.Count -eq 0) {
        return 0
    }

    return (($Tokens -join " ").Length)
}

function Get-PreferredCaptionLineCount {
    param(
        [Parameter(Mandatory)]
        [int]$TokenCount
    )

    if ($TokenCount -le 0) {
        return 0
    }

    if ($TokenCount -le 3) {
        return 1
    }

    return [Math]::Ceiling($TokenCount / 2.0)
}

function Get-CaptionBreakScore {
    param(
        [Parameter(Mandatory)]
        [string[]]$GroupTokens,

        [Parameter(Mandatory)]
        [double]$TargetLength,

        [Parameter(Mandatory)]
        [int]$TargetWordsPerLine
    )

    $wordCount = $GroupTokens.Count
    $lineLength = Get-TokenGroupLength -Tokens $GroupTokens
    $score = [Math]::Pow(($lineLength - $TargetLength), 2)

    if ($wordCount -lt 1 -or $wordCount -gt 3) {
        $score += 1000
    }

    $score += [Math]::Pow(($wordCount - $TargetWordsPerLine), 2) * 2

    $firstToken = $GroupTokens[0]
    if ($firstToken -match '^[,.;:!?)]') {
        $score += 25
    }

    $lastToken = $GroupTokens[$GroupTokens.Count - 1]
    if ($lastToken -match '^[("]$') {
        $score += 10
    }

    if ($GroupTokens.Count -gt 1) {
        for ($i = 0; $i -lt ($GroupTokens.Count - 1); $i++) {
            if ($GroupTokens[$i] -match '[,;:]$') {
                $score += 14
            }
        }
    }

    return $score
}

function ConvertTo-CaptionLines {
    param(
        [Parameter(Mandatory)]
        [string]$Text,

        [int]$MinimumWordsPerLine = 1,
        [int]$MaximumWordsPerLine = 3
    )

    $tokens = Get-CaptionTokens -Text $Text
    if ($tokens.Count -le 1) {
        return $tokens
    }

    $preferredLineCount = Get-PreferredCaptionLineCount -TokenCount $tokens.Count
    $targetLength = [Math]::Max(4, (($tokens -join " ").Length / [Math]::Max(1, $preferredLineCount)))
    $targetWordsPerLine = [Math]::Min($MaximumWordsPerLine, [Math]::Max($MinimumWordsPerLine, [Math]::Round($tokens.Count / [Math]::Max(1, $preferredLineCount))))

    $scores = @{}
    $paths = @{}
    $scores[$tokens.Count] = 0.0
    $paths[$tokens.Count] = @()

    for ($index = $tokens.Count - 1; $index -ge 0; $index--) {
        $bestScore = [double]::PositiveInfinity
        $bestPath = $null

        for ($size = $MinimumWordsPerLine; $size -le $MaximumWordsPerLine; $size++) {
            $nextIndex = $index + $size
            if ($nextIndex -gt $tokens.Count) {
                continue
            }

            if (-not $scores.ContainsKey($nextIndex)) {
                continue
            }

            $groupTokens = @($tokens[$index..($nextIndex - 1)])
            $groupScore = Get-CaptionBreakScore -GroupTokens $groupTokens -TargetLength $targetLength -TargetWordsPerLine $targetWordsPerLine
            $linePenalty = 0.35
            $totalScore = $groupScore + $scores[$nextIndex] + $linePenalty

            if ($totalScore -lt $bestScore) {
                $bestScore = $totalScore
                $bestPath = @(($groupTokens -join " ")) + @($paths[$nextIndex])
            }
        }

        $scores[$index] = $bestScore
        $paths[$index] = $bestPath
    }

    return @($paths[0])
}

function Format-CaptionText {
    param(
        [Parameter(Mandatory)]
        [string]$Text,

        [string]$LineBreak = "`r`n",

        [int]$MinimumWordsPerLine = 1,
        [int]$MaximumWordsPerLine = 3
    )

    $lines = ConvertTo-CaptionLines -Text $Text -MinimumWordsPerLine $MinimumWordsPerLine -MaximumWordsPerLine $MaximumWordsPerLine
    return ($lines -join $LineBreak).Trim()
}

function Convert-SrtContentToBalancedLines {
    param(
        [Parameter(Mandatory)]
        [string]$Content,

        [int]$MinimumWordsPerLine = 1,
        [int]$MaximumWordsPerLine = 3
    )

    $blocks = [regex]::Split($Content.Trim(), "\r?\n\r?\n")
    $outputBlocks = @()

    foreach ($block in $blocks) {
        $lines = @($block -split "\r?\n")
        if ($lines.Count -lt 3) {
            $outputBlocks += $block
            continue
        }

        $header = @($lines[0], $lines[1])
        $text = (($lines | Select-Object -Skip 2) -join " ").Trim()
        $formatted = Format-CaptionText -Text $text -MinimumWordsPerLine $MinimumWordsPerLine -MaximumWordsPerLine $MaximumWordsPerLine
        $outputBlocks += (($header + @($formatted)) -join "`r`n")
    }

    return ($outputBlocks -join "`r`n`r`n") + "`r`n"
}
