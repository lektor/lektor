$app = Get-WmiObject -Class Win32_Product | Where-Object {
    $_.Name -match "lektor"
}

Remove-Item *
$app.Uninstall()
