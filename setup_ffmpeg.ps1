$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Join-Path $projectRoot ".tools"
$installRoot = Join-Path $toolsRoot "ffmpeg"
$archivePath = Join-Path $toolsRoot "ffmpeg-9.0.2-full_build-shared.zip"
$downloadUrl = "https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-full_build-shared.zip"
$expectedSha256 = "8d31e162f1616e37aab3fa2db991b97e1b8dbeb1c8465fd81a81be16ff91b328"

$existingFfmpeg = Get-ChildItem -Path $installRoot -Filter "ffmpeg.exe" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
$existingFfprobe = Get-ChildItem -Path $installRoot -Filter "ffprobe.exe" -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if ($existingFfmpeg -and $existingFfprobe) {
    Write-Output "Project-local FFmpeg is already installed at $($existingFfmpeg.DirectoryName)"
    exit 0
}

New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
Write-Output "Downloading the full FFmpeg build into the project..."
Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath

$actualSha256 = (Get-FileHash -Path $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) {
    Remove-Item -Path $archivePath -Force
    throw "FFmpeg archive checksum mismatch. The downloaded file was removed."
}

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
Expand-Archive -LiteralPath $archivePath -DestinationPath $installRoot -Force
Remove-Item -Path $archivePath -Force

$ffmpeg = Get-ChildItem -Path $installRoot -Filter "ffmpeg.exe" -File -Recurse | Select-Object -First 1
$ffprobe = Get-ChildItem -Path $installRoot -Filter "ffprobe.exe" -File -Recurse | Select-Object -First 1
if (-not $ffmpeg -or -not $ffprobe) {
    throw "The archive was extracted, but ffmpeg.exe or ffprobe.exe was not found."
}

Write-Output "Installed project-local FFmpeg at $($ffmpeg.DirectoryName)"