param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$ScriptPath,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"

$candidates = @()
if ($env:PYTHON) {
  $candidates += @{ File = $env:PYTHON; Args = @() }
}
$candidates += @{ File = "python"; Args = @() }
$candidates += @{ File = "py"; Args = @("-3") }
$candidates += @{ File = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"; Args = @() }

foreach ($candidate in $candidates) {
  $file = $candidate.File
  $exists = $file -in @("python", "py") -or (Test-Path -LiteralPath $file)
  if (-not $exists) {
    continue
  }

  try {
    & $file @($candidate.Args) $ScriptPath @ScriptArgs
    exit $LASTEXITCODE
  } catch {
    if ($file -notin @("python", "py")) {
      throw
    }
  }
}

throw "Python was not found. Install Python 3 or set the PYTHON environment variable."
