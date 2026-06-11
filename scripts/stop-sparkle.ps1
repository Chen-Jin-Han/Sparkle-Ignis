$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location -LiteralPath $RepoRoot

$envFile = if (Test-Path ".env.sparkle") { Resolve-Path ".env.sparkle" } else { Resolve-Path ".env.sparkle.example" }
docker compose --env-file $envFile -f docker-compose.sparkle.yml down

Write-Host "Sparkle has stopped."
