param(
    [string]$FromEmail = "",
    [string]$FromPassword = "",
    [string]$ToEmail = "",
    [string]$SmtpServer = "smtp.gmail.com",
    [int]$SmtpPort = 587
)

$url = "https://jometcode.onrender.com"

Write-Host "مراقبة الموقع jometcode.onrender.com..."
Write-Host "بنتظر يرجع..."

while ($true) {
    try {
        $request = [System.Net.WebRequest]::Create($url)
        $request.Timeout = 10000
        $response = $request.GetResponse()
        $statusCode = [int]$response.StatusCode
        $response.Close()

        if ($statusCode -eq 200) {
            Write-Host "الموقع شغال!" -ForegroundColor Green

            if ($FromEmail -and $ToEmail) {
                $smtp = New-Object Net.Mail.SmtpClient($SmtpServer, $SmtpPort)
                $smtp.EnableSsl = $true
                $smtp.Credentials = New-Object Net.NetworkCredential($FromEmail, $FromPassword)
                $smtp.Send($FromEmail, $ToEmail, "JometCode Online!", "الموقع jometcode.onrender.com رجع شغال !")
                Write-Host "تم إرسال الإيميل!" -ForegroundColor Green
            }
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
    Start-Sleep -Seconds 60
}
