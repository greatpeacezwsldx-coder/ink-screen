$count = 0
$lastCount = 0
$stuckCount = 0
while ($count -lt 453) {
    python -u process_continuous.py 2>&1 | Out-Null
    $output = python check_db.py 2>&1
    $count = [int]$output.Trim()
    Write-Host "Progress: $count/453"
    if ($count -eq $lastCount) {
        $stuckCount++
        if ($stuckCount -ge 5) {
            Write-Host "Stuck at $count, exiting"
            break
        }
    } else {
        $stuckCount = 0
    }
    $lastCount = $count
}
Write-Host "Done!"
