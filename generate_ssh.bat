@echo off
"C:\Program Files\Git\usr\bin\ssh-keygen.exe" -t ed25519 -C "wanglin141319@gmail.com" -f "C:\Users\ZhuanZ（无密码）\.ssh\id_ed25519" -P ""
echo.
echo Public key:
type "C:\Users\ZhuanZ（无密码）\.ssh\id_ed25519.pub"
pause
