Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/Common.ps1"

function Get-VideoFiles {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Profile
    )

    $extensions = @($Profile.videoExtensions | ForEach-Object { $_.ToLowerInvariant() })
    $searchOption = if ($Profile.preparation.recursive) { "AllDirectories" } else { "TopDirectoryOnly" }

    $files = Get-ChildItem -LiteralPath $Profile.sourceFolder -File -Recurse:$Profile.preparation.recursive |
        Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() } |
        Sort-Object DirectoryName, Name

    return $files
}

function Get-MediaDurationSeconds {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $ffprobe = Resolve-CommandPath -CommandName "ffprobe"
    $args = @(
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1",
        $Path
    )

    $result = Invoke-ProcessCapture -FilePath $ffprobe -Arguments $args
    if ($result.ExitCode -ne 0) {
        throw "ffprobe falhou ao ler duração de '$Path': $($result.StdErr)"
    }

    return [double]::Parse(($result.StdOutLines | Select-Object -First 1).Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-SilenceIntervals {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [hashtable]$Profile
    )

    $ffmpeg = Resolve-CommandPath -CommandName "ffmpeg"
    $noise = "{0}dB" -f (Format-NumberInvariant -Value ([double]$Profile.silence.noiseThresholdDb))
    $minDuration = Format-NumberInvariant -Value ([double]$Profile.silence.minimumDurationSeconds)

    $args = @(
        "-nostats",
        "-hide_banner",
        "-i", $Path,
        "-vn",
        "-sn",
        "-af", "silencedetect=noise=${noise}:d=${minDuration}",
        "-f", "null", "-"
    )

    $result = Invoke-ProcessCapture -FilePath $ffmpeg -Arguments $args
    if ($result.ExitCode -ne 0) {
        throw "ffmpeg falhou ao detectar silêncio em '$Path': $($result.StdErr)"
    }

    $intervals = @()
    $currentStart = $null

    foreach ($line in $result.StdErrLines) {
        if ($line -match "silence_start:\s*([0-9\.]+)") {
            $currentStart = [double]::Parse($matches[1], [System.Globalization.CultureInfo]::InvariantCulture)
            continue
        }

        if ($line -match "silence_end:\s*([0-9\.]+)\s*\|\s*silence_duration:\s*([0-9\.]+)") {
            $end = [double]::Parse($matches[1], [System.Globalization.CultureInfo]::InvariantCulture)
            $duration = [double]::Parse($matches[2], [System.Globalization.CultureInfo]::InvariantCulture)
            $start = if ($null -ne $currentStart) { $currentStart } else { [Math]::Max(0, $end - $duration) }
            $intervals += [pscustomobject]@{
                Start = $start
                End = $end
                Duration = $duration
            }
            $currentStart = $null
        }
    }

    if ($null -ne $currentStart) {
        $intervals += [pscustomobject]@{
            Start = $currentStart
            End = $null
            Duration = $null
        }
    }

    return $intervals
}

function Get-TrimPlan {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [hashtable]$Profile
    )

    $duration = Get-MediaDurationSeconds -Path $Path
    if (-not $Profile.silence.enabled) {
        return [pscustomobject]@{
            Duration = $duration
            HeadTrim = 0.0
            TailTrim = 0.0
            OutputDuration = $duration
            Intervals = @()
        }
    }

    $intervals = Get-SilenceIntervals -Path $Path -Profile $Profile
    $leadingSlack = [double]$Profile.silence.leadingDetectionSlackSeconds
    $trailingSlack = [double]$Profile.silence.trailingDetectionSlackSeconds
    $headPadding = [double]$Profile.silence.keepHeadPaddingSeconds
    $tailPadding = [double]$Profile.silence.keepTailPaddingSeconds
    $extraHead = [double]$Profile.silence.extraHeadTrimSeconds
    $extraTail = [double]$Profile.silence.extraTailTrimSeconds
    $maxHead = [double]$Profile.silence.maxHeadTrimSeconds
    $maxTail = [double]$Profile.silence.maxTailTrimSeconds
    $minOutput = [double]$Profile.silence.minimumOutputDurationSeconds

    $headTrim = 0.0
    $tailTrim = 0.0

    $leadingInterval = $intervals | Where-Object { $_.Start -le $leadingSlack -and $null -ne $_.End } | Select-Object -First 1
    if ($leadingInterval) {
        $headTrim = [Math]::Max(0, ($leadingInterval.End - $headPadding) + $extraHead)
        $headTrim = [Math]::Min($headTrim, $maxHead)
    }

    $trailingInterval = $intervals |
        Where-Object {
            $_.Start -lt $duration -and (
                ($null -eq $_.End) -or
                ([Math]::Abs($duration - $_.End) -le $trailingSlack)
            )
        } |
        Select-Object -Last 1

    if ($trailingInterval) {
        $baseTail = [Math]::Max(0, ($duration - $trailingInterval.Start) - $tailPadding)
        $tailTrim = [Math]::Max(0, $baseTail + $extraTail)
        $tailTrim = [Math]::Min($tailTrim, $maxTail)
    }

    if (($duration - $headTrim - $tailTrim) -lt $minOutput) {
        $overflow = $minOutput - ($duration - $headTrim - $tailTrim)
        if ($tailTrim -ge $overflow) {
            $tailTrim -= $overflow
        }
        elseif ($headTrim -ge $overflow) {
            $headTrim -= $overflow
        }
        else {
            $headTrim = 0.0
            $tailTrim = 0.0
        }
    }

    return [pscustomobject]@{
        Duration = $duration
        HeadTrim = [Math]::Max(0, $headTrim)
        TailTrim = [Math]::Max(0, $tailTrim)
        OutputDuration = [Math]::Max(0, $duration - $headTrim - $tailTrim)
        Intervals = $intervals
    }
}

function New-StagedClipName {
    param(
        [Parameter(Mandatory)]
        [int]$Index,

        [Parameter(Mandatory)]
        [System.IO.FileInfo]$File,

        [Parameter(Mandatory)]
        [hashtable]$Profile,

        [string]$ExtensionOverride
    )

    $prefix = $Index.ToString(("D{0}" -f [int]$Profile.preparation.prefixWidth))
    $folderName = Get-SafeFileStem -Text $File.Directory.Name
    $fileName = Get-SafeFileStem -Text $File.BaseName
    $extension = if ($ExtensionOverride) { $ExtensionOverride } else { $Profile.preparation.outputExtension }

    return "{0}_{1}_{2}{3}" -f $prefix, $folderName, $fileName, $extension
}

function Invoke-PrepareCapCutMedia {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Profile
    )

    $ffmpeg = Resolve-CommandPath -CommandName "ffmpeg"
    $workspace = $Profile.workspaceRoot
    $preparedFolder = Join-Path $workspace $Profile.preparation.stagingFolder
    $manifestFolder = Join-Path $workspace $Profile.preparation.manifestFolder

    Ensure-Directory -Path $workspace
    Ensure-Directory -Path $preparedFolder
    Ensure-Directory -Path $manifestFolder

    $files = Get-VideoFiles -Profile $Profile
    if (-not $files -or $files.Count -eq 0) {
        throw "Nenhum vídeo encontrado em '$($Profile.sourceFolder)'."
    }

    $manifest = @()
    $index = 1

    foreach ($file in $files) {
        $trimPlan = Get-TrimPlan -Path $file.FullName -Profile $Profile

        $needsTrim = ($trimPlan.HeadTrim -gt 0.001) -or ($trimPlan.TailTrim -gt 0.001)
        $canCopyWithoutContainerMismatch = $file.Extension.ToLowerInvariant() -eq $Profile.preparation.outputExtension.ToLowerInvariant()
        $useSourceExtension = (-not $needsTrim) -and $Profile.preparation.copyUnchangedFiles -and $Profile.preparation.preserveSourceExtensionOnCopy
        $extensionOverride = if ($useSourceExtension) { $file.Extension } else { $null }
        $clipName = New-StagedClipName -Index $index -File $file -Profile $Profile -ExtensionOverride $extensionOverride
        $outputPath = Join-Path $preparedFolder $clipName

        if ((-not $needsTrim) -and $Profile.preparation.copyUnchangedFiles -and ($canCopyWithoutContainerMismatch -or $useSourceExtension)) {
            Copy-Item -LiteralPath $file.FullName -Destination $outputPath -Force
            $operation = "copy"
        }
        else {
            $startAt = Format-NumberInvariant -Value ([double]$trimPlan.HeadTrim)
            $endAt = Format-NumberInvariant -Value ([double]($trimPlan.Duration - $trimPlan.TailTrim))
            $args = @(
                "-y",
                "-v", "error",
                "-hide_banner",
                "-ss", $startAt,
                "-to", $endAt,
                "-i", $file.FullName,
                "-c:v", $Profile.preparation.ffmpegVideoCodec,
                "-preset", $Profile.preparation.ffmpegPreset,
                "-crf", [string]$Profile.preparation.ffmpegVideoCrf,
                "-c:a", $Profile.preparation.ffmpegAudioCodec,
                "-b:a", $Profile.preparation.ffmpegAudioBitrate,
                "-movflags", "+faststart",
                $outputPath
            )

            $result = Invoke-ProcessCapture -FilePath $ffmpeg -Arguments $args
            if ($result.ExitCode -ne 0) {
                throw "ffmpeg falhou ao gerar '$outputPath': $($result.StdErr)"
            }
            $operation = "transcode"
        }

        $manifest += [pscustomobject]@{
            Order = $index
            SourcePath = $file.FullName
            PreparedPath = $outputPath
            PreparedName = $clipName
            DurationOriginalSeconds = [Math]::Round($trimPlan.Duration, 3)
            TrimHeadSeconds = [Math]::Round($trimPlan.HeadTrim, 3)
            TrimTailSeconds = [Math]::Round($trimPlan.TailTrim, 3)
            DurationPreparedSeconds = [Math]::Round($trimPlan.OutputDuration, 3)
            Operation = $operation
        }

        $index += 1
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $csvPath = Join-Path $manifestFolder "manifest-$timestamp.csv"
    $jsonPath = Join-Path $manifestFolder "manifest-$timestamp.json"
    $orderPath = Join-Path $manifestFolder "import-order-$timestamp.txt"

    $manifest | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
    Write-JsonFile -Path $jsonPath -InputObject $manifest
    Set-Content -LiteralPath $orderPath -Value ($manifest.PreparedName -join [Environment]::NewLine) -Encoding UTF8

    return [pscustomobject]@{
        PreparedFolder = $preparedFolder
        ManifestCsv = $csvPath
        ManifestJson = $jsonPath
        ImportOrder = $orderPath
        Clips = $manifest
    }
}
