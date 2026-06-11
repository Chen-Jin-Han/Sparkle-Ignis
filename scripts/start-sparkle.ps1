$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location -LiteralPath $RepoRoot

if (-not (Test-Path ".env.sparkle")) {
    Copy-Item ".env.sparkle.example" ".env.sparkle"
    Write-Host "Created .env.sparkle from .env.sparkle.example. Add DEEPSEEK_API_KEY there to enable DeepSeek polishing."
}

$envFile = Resolve-Path ".env.sparkle"
docker compose --env-file $envFile -f docker-compose.sparkle.yml up -d --build

$portLine = Get-Content ".env.sparkle" | Where-Object { $_ -match "^SPARKLE_PORT=" } | Select-Object -First 1
$port = if ($portLine) { ($portLine -split "=", 2)[1].Trim() } else { "8080" }
$url = "http://localhost:$port"

Write-Host "Sparkle is running at $url"
Start-Process $url
