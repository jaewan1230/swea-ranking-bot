param(
    [string]$Python = "python",
    [string]$DistPath = "dist"
)

$ErrorActionPreference = "Stop"

$pythonCommand = Get-Command $Python -ErrorAction Stop
$pythonExe = $pythonCommand.Source
$pythonPrefix = & $pythonExe -c "import sys; print(sys.prefix)"

$localAppData = [Environment]::GetFolderPath("LocalApplicationData")
$playwrightPath = Join-Path $localAppData "ms-playwright"
if (-not (Test-Path $playwrightPath)) {
    throw "Playwright browsers not found at $playwrightPath. Run: python -m playwright install chromium"
}

$tkinterPyd = Join-Path $pythonPrefix "DLLs\_tkinter.pyd"
$tclDllCandidates = @(
    (Join-Path $pythonPrefix "Library\bin\tcl86t.dll"),
    (Join-Path $pythonPrefix "DLLs\tcl86t.dll")
)
$tkDllCandidates = @(
    (Join-Path $pythonPrefix "Library\bin\tk86t.dll"),
    (Join-Path $pythonPrefix "DLLs\tk86t.dll")
)
$tclDataCandidates = @(
    (Join-Path $pythonPrefix "Library\lib\tcl8.6"),
    (Join-Path $pythonPrefix "tcl\tcl8.6")
)
$tkDataCandidates = @(
    (Join-Path $pythonPrefix "Library\lib\tk8.6"),
    (Join-Path $pythonPrefix "tcl\tk8.6")
)

$tclDll = $tclDllCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$tkDll = $tkDllCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$tclData = $tclDataCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$tkData = $tkDataCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

foreach ($required in @($tkinterPyd, $tclDll, $tkDll, $tclData, $tkData)) {
    if (-not $required) {
        throw "Could not locate a required Tcl/Tk build dependency. Python prefix: $pythonPrefix"
    }
}

& $pythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "SWEA Ranking Bot" `
    --distpath $DistPath `
    --workpath "build" `
    --hidden-import tkinter `
    --hidden-import _tkinter `
    --add-binary "$tkinterPyd;." `
    --add-binary "$tclDll;." `
    --add-binary "$tkDll;." `
    --add-data "$tclData;_tcl_data" `
    --add-data "$tkData;_tk_data" `
    --add-data "$playwrightPath;ms-playwright" `
    swea_ranking_gui.py

$outputDir = Join-Path $DistPath "SWEA Ranking Bot"
$checks = @(
    @{ Name = "exe"; Path = (Join-Path $outputDir "SWEA Ranking Bot.exe") },
    @{ Name = "_tkinter.pyd"; Path = (Join-Path $outputDir "_internal\_tkinter.pyd") },
    @{ Name = "Tcl data"; Path = (Join-Path $outputDir "_internal\_tcl_data\init.tcl") },
    @{ Name = "Tk data"; Path = (Join-Path $outputDir "_internal\_tk_data\tk.tcl") },
    @{ Name = "Playwright browsers"; Path = (Join-Path $outputDir "_internal\ms-playwright") }
)

foreach ($check in $checks) {
    if (-not (Test-Path $check.Path)) {
        throw "Build output is missing $($check.Name): $($check.Path)"
    }
}

Write-Host "Build complete: $(Join-Path $outputDir 'SWEA Ranking Bot.exe')"
