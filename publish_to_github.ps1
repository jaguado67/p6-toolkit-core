# Publishes this clean source folder to an existing EMPTY GitHub repository.
# This script does not create the GitHub repository or alter the application.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$remote = 'https://github.com/jaguado67/p6-toolkit-core.git'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is not installed or is not available in PATH.' }
if (-not (Test-Path '.git')) { git init }
$remotes = @(git remote)
if ($remotes -notcontains 'origin') { git remote add origin $remote }
else {
    $origin = git remote get-url origin
    if ($origin.Trim() -ne $remote) { throw "Existing origin points to $origin; expected $remote. Nothing was pushed." }
}
git add .
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { git commit -m 'Publish P6 Toolkit v0.2.2 for Streamlit Community Cloud' }
git branch -M main
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Push failed. Verify GitHub authentication and that the empty repository exists.' }
Write-Host "Published to https://github.com/jaguado67/p6-toolkit-core" -ForegroundColor Green
