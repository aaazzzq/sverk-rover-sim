$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    docker compose up --build -d
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Gazebo is starting at http://localhost:6081/vnc.html"
