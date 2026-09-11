Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ProjectRoot {
    $libRoot = Split-Path -Parent $PSScriptRoot
    return Split-Path -Parent $libRoot
}

function Resolve-ProjectPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return [System.IO.Path]::GetFullPath((Join-Path (Get-ProjectRoot) $Path))
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        [void](New-Item -ItemType Directory -Path $Path -Force)
    }
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        $InputObject
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        Ensure-Directory -Path $parent
    }

    $json = $InputObject | ConvertTo-Json -Depth 100
    Set-Content -LiteralPath $Path -Value $json -Encoding UTF8
}

function ConvertTo-HashtableDeep {
    param(
        [Parameter(Mandatory)]
        $InputObject
    )

    if ($null -eq $InputObject) {
        return $null
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        $hash = @{}
        foreach ($key in $InputObject.Keys) {
            $hash[$key] = ConvertTo-HashtableDeep -InputObject $InputObject[$key]
        }
        return $hash
    }

    if ($InputObject -is [System.Management.Automation.PSCustomObject]) {
        $hash = @{}
        foreach ($property in $InputObject.PSObject.Properties) {
            $hash[$property.Name] = ConvertTo-HashtableDeep -InputObject $property.Value
        }
        return $hash
    }

    if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
        $items = @()
        foreach ($item in $InputObject) {
            $items += ,(ConvertTo-HashtableDeep -InputObject $item)
        }
        return $items
    }

    return $InputObject
}

function Merge-Hashtable {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Base,

        [Parameter(Mandatory)]
        [hashtable]$Override
    )

    $result = @{}
    foreach ($key in $Base.Keys) {
        $result[$key] = $Base[$key]
    }

    foreach ($key in $Override.Keys) {
        if (
            $result.ContainsKey($key) -and
            $result[$key] -is [hashtable] -and
            $Override[$key] -is [hashtable]
        ) {
            $result[$key] = Merge-Hashtable -Base $result[$key] -Override $Override[$key]
        }
        else {
            $result[$key] = $Override[$key]
        }
    }

    return $result
}

function Load-ProfileConfig {
    param(
        [Parameter(Mandatory)]
        [string]$ProfilePath
    )

    $defaultPath = Resolve-ProjectPath -Path "config/profiles/default.json"
    $profileAbsolutePath = Resolve-ProjectPath -Path $ProfilePath

    $defaultConfig = ConvertTo-HashtableDeep -InputObject (Read-JsonFile -Path $defaultPath)
    $profileConfig = ConvertTo-HashtableDeep -InputObject (Read-JsonFile -Path $profileAbsolutePath)
    $merged = Merge-Hashtable -Base $defaultConfig -Override $profileConfig

    $merged.profilePath = $profileAbsolutePath
    $merged.projectRoot = Get-ProjectRoot
    $merged.workspaceRoot = Resolve-ProjectPath -Path $merged.workspaceRoot
    $merged.sourceFolder = Resolve-ProjectPath -Path $merged.sourceFolder
    $merged.capcut.calibrationFile = Resolve-ProjectPath -Path $merged.capcut.calibrationFile

    return $merged
}

function Resolve-CommandPath {
    param(
        [Parameter(Mandatory)]
        [string]$CommandName
    )

    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Comando não encontrado: $CommandName"
    }

    return $command.Source
}

function Format-NumberInvariant {
    param(
        [Parameter(Mandatory)]
        [double]$Value
    )

    return $Value.ToString("0.###", [System.Globalization.CultureInfo]::InvariantCulture)
}

function Join-ProcessArguments {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    $quoted = foreach ($argument in $Arguments) {
        if ($argument -match '[\s"]') {
            '"' + ($argument -replace '"', '\"') + '"'
        }
        else {
            $argument
        }
    }

    return ($quoted -join " ")
}

function Invoke-ProcessCapture {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,

        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = Join-ProcessArguments -Arguments $Arguments
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()

    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut = $stdout
        StdErr = $stderr
        StdOutLines = @($stdout -split "`r?`n" | Where-Object { $_ -ne "" })
        StdErrLines = @($stderr -split "`r?`n" | Where-Object { $_ -ne "" })
        AllLines = @(
            @($stdout -split "`r?`n" | Where-Object { $_ -ne "" }) +
            @($stderr -split "`r?`n" | Where-Object { $_ -ne "" })
        )
    }
}

function Get-SafeFileStem {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $invalidChars = [System.IO.Path]::GetInvalidFileNameChars()
    $builder = New-Object System.Text.StringBuilder

    foreach ($char in $Text.ToCharArray()) {
        if ($invalidChars -contains $char) {
            [void]$builder.Append("_")
        }
        else {
            [void]$builder.Append($char)
        }
    }

    return ($builder.ToString().Trim() -replace "\s+", " ")
}

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host ""
    Write-Host "== $Message =="
}
