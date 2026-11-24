$count = 0
while ($count -lt 453) {
    python -u analyze_photos.py 2>&1 | Out-Null
    $output = python check_db.py 2>&1
    $count = [int]$output.Trim()
    Write-Host "Progress: $count/453"
    Start-Sleep -Milliseconds 500
}
Write-Host "All done!"
