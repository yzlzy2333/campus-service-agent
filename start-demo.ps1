
param(
    [switch]$Live,
    [ValidateSet('rag','full')]
    [string]$Mode = 'rag'
)

$ErrorActionPreference = 'Stop'
$bundledPython = Join-Path $PSScriptRoot 'runtime\python\python.exe'
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$localDependencies = Join-Path $PSScriptRoot '.runtime'
$originalPythonPath = $env:PYTHONPATH
$originalUtf8 = $env:PYTHONUTF8
Push-Location -LiteralPath $PSScriptRoot
try {
    if (Test-Path -LiteralPath $bundledPython) {
        $python = $bundledPython
    } elseif (Test-Path -LiteralPath $venvPython) {
        $python = $venvPython
    } elseif (Test-Path -LiteralPath $localDependencies) {
        $node = Get-Command node -ErrorAction SilentlyContinue
        if ($node -and $node.Source -like '*\dependencies\node\bin\node.exe') {
            $runtime = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $node.Source))
            $python = Join-Path $runtime 'python\python.exe'
        } else {
            $python = 'python'
        }
        $env:PYTHONPATH = $localDependencies
    } else {
        $python = 'python'
    }
    $env:PYTHONUTF8 = '1'
    $arguments = @('-B', '-X', 'utf8', '-m', 'campus', '--mode', $Mode)
    if (-not $Live) { $arguments += '--offline' }
    if ($MyInvocation.ExpectingInput) {
        $input | & $python @arguments
    } else {
        & $python @arguments
    }
    exit $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $originalPythonPath
    $env:PYTHONUTF8 = $originalUtf8
    Pop-Location
}
