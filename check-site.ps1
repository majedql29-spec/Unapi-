$url = "https://jometcode.onrender.com"
$checkInterval = 60

Write-Host "جاري مراقبة الموقع jometcode.onrender.com..."
Write-Host "سأتحقق كل $checkInterval ثانية. انتظر..."

while ($true) {
    try {
        $request = [System.Net.WebRequest]::Create($url)
        $request.Timeout = 10000
        $response = $request.GetResponse()
        $statusCode = [int]$response.StatusCode
        $response.Close()

        if ($statusCode -eq 200) {
            $notification = New-Object -ComObject "Wscript.Shell"
            $notification.Popup("الموقع jometcode.onrender.com شغال الآن!", 0, "JometCode Online", 64)
            Write-Host "الموقع شغال!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
    Start-Sleep -Seconds $checkInterval
}

Read-Host "اضغط Enter للخروج"
