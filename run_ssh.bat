@echo off
set SSH_KEYGEN="D:\Program Files\Git\usr\bin\ssh-keygen.exe"
set KEY_PATH=C:\Users\ZhuanZ（无密码）\.ssh\id_ed25519

echo Generating SSH key (press Enter 3 times for default options)...
echo.
(echo.
echo.
echo.) | "%SSH_KEYGEN%" -t ed25519 -C "wanglin141319@gmail.com" -f "%KEY_PATH%"

echo.
echo === YOUR PUBLIC KEY (copy everything below) ===
type "%KEY_PATH%.pub"
echo.
echo === END OF PUBLIC KEY ===
echo.
pause
