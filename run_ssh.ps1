$sshKeygen = "D:\Program Files\Git\usr\bin\ssh-keygen.exe"
$keyPath = "C:\Users\ZhuanZ（无密码）\.ssh\id_ed25519"
$email = "wanglin141319@gmail.com"

Write-Host "Generating SSH key..."

$proc = Start-Process -FilePath $sshKeygen -ArgumentList "-t", "ed25519", "-C", $email, "-f", $keyPath -NoNewWindow -Wait -PassThru

Write-Host "Done! Public key:"
Get-Content "$keyPath.pub"
