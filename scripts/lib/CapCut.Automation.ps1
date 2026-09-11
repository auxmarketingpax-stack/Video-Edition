Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/Common.ps1"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class CapCutWin32 {
  [StructLayout(LayoutKind.Sequential)]
  public struct POINT {
    public int X;
    public int Y;
  }
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT pt);
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@

$script:MouseEventLeftDown = 0x0002
$script:MouseEventLeftUp = 0x0004

function Get-ScreenSize {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    return [pscustomobject]@{
        Width = $bounds.Width
        Height = $bounds.Height
    }
}

function Get-CursorPosition {
    $point = New-Object CapCutWin32+POINT
    [CapCutWin32]::GetCursorPos([ref]$point) | Out-Null
    $screen = Get-ScreenSize

    return [pscustomobject]@{
        X = $point.X
        Y = $point.Y
        NormalizedX = if ($screen.Width -gt 0) { [Math]::Round($point.X / $screen.Width, 6) } else { 0 }
        NormalizedY = if ($screen.Height -gt 0) { [Math]::Round($point.Y / $screen.Height, 6) } else { 0 }
        ScreenWidth = $screen.Width
        ScreenHeight = $screen.Height
    }
}

function Convert-NormalizedToPixel {
    param(
        [Parameter(Mandatory)]
        [double]$X,

        [Parameter(Mandatory)]
        [double]$Y
    )

    $screen = Get-ScreenSize
    return [pscustomobject]@{
        X = [int][Math]::Round($X * $screen.Width)
        Y = [int][Math]::Round($Y * $screen.Height)
    }
}

function Invoke-LeftClick {
    param(
        [Parameter(Mandatory)]
        [int]$X,

        [Parameter(Mandatory)]
        [int]$Y,

        [int]$Count = 1
    )

    [CapCutWin32]::SetCursorPos($X, $Y) | Out-Null
    Start-Sleep -Milliseconds 150

    for ($i = 0; $i -lt $Count; $i++) {
        [CapCutWin32]::mouse_event($script:MouseEventLeftDown, 0, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 40
        [CapCutWin32]::mouse_event($script:MouseEventLeftUp, 0, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 120
    }
}

function Test-AnchorPresent {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Anchors,

        [Parameter(Mandatory)]
        [string]$AnchorName
    )

    return $Anchors.ContainsKey($AnchorName)
}

function Invoke-AnchorClickByName {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Anchors,

        [Parameter(Mandatory)]
        [string]$AnchorName,

        [int]$Count = 1
    )

    if (-not (Test-AnchorPresent -Anchors $Anchors -AnchorName $AnchorName)) {
        throw "Ancora nao calibrada: $AnchorName"
    }

    $anchor = $Anchors[$AnchorName]
    $point = Convert-NormalizedToPixel -X ([double]$anchor.x) -Y ([double]$anchor.y)
    Activate-CapCutWindow
    Invoke-LeftClick -X $point.X -Y $point.Y -Count $Count
}

function Load-CalibrationAnchors {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Profile
    )

    $path = $Profile.capcut.calibrationFile
    if (-not (Test-Path -LiteralPath $path)) {
        return @{}
    }

    $data = ConvertTo-HashtableDeep -InputObject (Read-JsonFile -Path $path)
    return if ($data.anchors) { $data.anchors } else { @{} }
}

function Save-CalibrationAnchor {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Profile,

        [Parameter(Mandatory)]
        [string]$AnchorName,

        [string]$Description = ""
    )

    $cursor = Get-CursorPosition
    $path = $Profile.capcut.calibrationFile
    $current = if (Test-Path -LiteralPath $path) {
        ConvertTo-HashtableDeep -InputObject (Read-JsonFile -Path $path)
    }
    else {
        @{}
    }

    if (-not $current.ContainsKey("anchors")) {
        $current.anchors = @{}
    }

    $current.updatedAt = (Get-Date).ToString("o")
    $current.screen = @{
        width = $cursor.ScreenWidth
        height = $cursor.ScreenHeight
    }
    $current.anchors[$AnchorName] = @{
        description = $Description
        x = $cursor.NormalizedX
        y = $cursor.NormalizedY
        pixelX = $cursor.X
        pixelY = $cursor.Y
    }

    Write-JsonFile -Path $path -InputObject $current
    return $current.anchors[$AnchorName]
}

function Start-CapCutApplication {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Profile
    )

    $command = $Profile.capcut.launchCommand
    $arguments = @($Profile.capcut.launchArguments)
    Start-Process -FilePath $command -ArgumentList $arguments | Out-Null
}

function Activate-CapCutWindow {
    [void][Microsoft.VisualBasic.Interaction]::AppActivate("CapCut")
    Start-Sleep -Milliseconds 500
}

function Set-ClipboardTextSafe {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    [System.Windows.Forms.Clipboard]::SetText($Text)
}

function Resolve-ContextValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Context,

        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not $Context.ContainsKey($Name)) {
        throw "Valor de contexto nao encontrado: $Name"
    }

    return [string]$Context[$Name]
}

function Get-RepeatCount {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Step,

        [Parameter(Mandatory)]
        [hashtable]$Context
    )

    if ($Step.ContainsKey("count")) {
        return [int]$Step.count
    }

    if ($Step.ContainsKey("countFrom")) {
        $name = [string]$Step.countFrom
        if (-not $Context.ContainsKey($name)) {
            throw "Valor de repeticao nao encontrado: $name"
        }
        return [int]$Context[$name]
    }

    throw "repeatSteps exige 'count' ou 'countFrom'."
}

function Invoke-WorkflowStep {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Step,

        [Parameter(Mandatory)]
        [hashtable]$Context,

        [Parameter(Mandatory)]
        [hashtable]$Anchors,

        [Parameter(Mandatory)]
        [switch]$Interactive,

        [Parameter(Mandatory)]
        [hashtable]$Profile
    )

    switch ($Step.type) {
        "launchCapCut" {
            Start-CapCutApplication -Profile $Profile
            Start-Sleep -Seconds 4
            return
        }
        "checkpoint" {
            Write-Host $Step.message
            if ($Interactive) {
                [void](Read-Host "Pressione Enter para continuar")
            }
            return
        }
        "wait" {
            Start-Sleep -Milliseconds ([int]$Step.milliseconds)
            return
        }
        "sendKeys" {
            Activate-CapCutWindow
            [System.Windows.Forms.SendKeys]::SendWait([string]$Step.keys)
            $delayMs = 250
            if ($Step.ContainsKey("delayMs")) {
                $delayMs = [int]$Step.delayMs
            }
            Start-Sleep -Milliseconds $delayMs
            return
        }
        "setClipboardText" {
            $value = if ($Step.ContainsKey("value")) {
                [string]$Step.value
            }
            else {
                Resolve-ContextValue -Context $Context -Name $Step.valueFrom
            }
            Set-ClipboardTextSafe -Text $value
            return
        }
        "clickAnchor" {
            Invoke-AnchorClickByName -Anchors $Anchors -AnchorName ([string]$Step.anchor) -Count 1
            Start-Sleep -Milliseconds 250
            return
        }
        "doubleClickAnchor" {
            Invoke-AnchorClickByName -Anchors $Anchors -AnchorName ([string]$Step.anchor) -Count 2
            Start-Sleep -Milliseconds 250
            return
        }
        "clickAnchorIfPresent" {
            $anchorName = [string]$Step.anchor
            if (Test-AnchorPresent -Anchors $Anchors -AnchorName $anchorName) {
                Invoke-AnchorClickByName -Anchors $Anchors -AnchorName $anchorName -Count 1
                Start-Sleep -Milliseconds 250
            }
            return
        }
        "repeatSteps" {
            $iterations = Get-RepeatCount -Step $Step -Context $Context
            for ($iteration = 0; $iteration -lt $iterations; $iteration++) {
                $Context["repeatIndex"] = $iteration
                $Context["repeatNumber"] = $iteration + 1
                foreach ($nestedStep in $Step.steps) {
                    Invoke-WorkflowStep -Step $nestedStep -Context $Context -Anchors $Anchors -Interactive:$Interactive -Profile $Profile
                }
            }
            return
        }
        default {
            throw "Tipo de passo nao suportado: $($Step.type)"
        }
    }
}

function Invoke-CapCutWorkflow {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Profile,

        [Parameter(Mandatory)]
        [string]$WorkflowPath,

        [Parameter(Mandatory)]
        [hashtable]$Context,

        [switch]$Interactive
    )

    $workflow = ConvertTo-HashtableDeep -InputObject (Read-JsonFile -Path (Resolve-ProjectPath -Path $WorkflowPath))
    $anchors = Load-CalibrationAnchors -Profile $Profile

    foreach ($step in $workflow.steps) {
        Invoke-WorkflowStep -Step $step -Context $Context -Anchors $anchors -Interactive:$Interactive -Profile $Profile
    }
}
