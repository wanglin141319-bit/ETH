$ErrorActionPreference = "Stop"

$sshKeygen = "D:\Program Files\Git\usr\bin\ssh-keygen.exe"
$keyPath = "C:\Users\ZhuanZ（无密码）\.ssh\id_ed25519"
$email = "wanglin141319@gmail.com"

Write-Host "=== SSH Key Generator ==="
Write-Host ""

# Create .ssh directory if not exists
$sshDir = Split-Path $keyPath -Parent
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    Write-Host "Created .ssh directory"
}

# Run ssh-keygen with piped inputs for empty passphrase
Write-Host "Generating SSH key (3x Enter for defaults)..."
$process = Start-Process -FilePath $sshKeygen -ArgumentList "-t", "ed25519", "-C", $email, "-f", $keyPath -PassThru -WindowStyle Hidden

# Wait a bit for the process to start
Start-Sleep -Milliseconds 500

# Send 3 enter keys (for: confirm save location, empty passphrase, confirm passphrase)
$stream = $process.StandardInput
for ($i = 0; $i -lt 3; $i++) {
    $stream.WriteLine("")
    Start-Sleep -Milliseconds 200
}

# Wait for process to complete
$process.WaitForExit()

if ($process.ExitCode -eq 0) {
    Write-Host ""
    Write-Host "=== SUCCESS! Your public key: ==="
    Write-Host ""
    Get-Content "$keyPath.pub"
    Write-Host ""
    Write-Host "=== Copy the above key to GitHub SSH Settings ==="
} else {
    Write-Host "Error generating key. Exit code: $($process.ExitCode)"
}
