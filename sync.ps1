# Define the paths to the music folders on the phone and computer
$phoneMusicPath = "/storage/emulated/0/music"
$computerMusicPath = "C:\Users\$ENV:Username\Music"
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
# Use ADB to get the list of files in the phone music folder
$phoneMusicFiles = & ./adb.exe shell "cd $phoneMusicPath && stat -c %Y%n *.*"
# Use PowerShell to get the list of files in the computer music folder
$computerMusicFiles = Get-ChildItem $computerMusicPath/*.*

$filenames = @()
$timestamps = @()
$processes = @()


Write-Host "`n________________________________________________________________________________"
Write-Host "PHONE TO COMPUTER"
Write-Host "--------------------------------------------------------------------------------`n"

foreach ($phoneFile in $phoneMusicFiles) {
    # Construct the full path of the phone file
	
	$filenames += $phoneFile.Substring(10)
	$timestamps += $phoneFile.Substring(0, 10)
	$phoneFilePath = "$phoneMusicPath/$($filenames[-1])"
    # Check if the phone file exists in the computer folder
    $computerFile = $computerMusicFiles | Where-Object {$_.Name -eq $filenames[-1]}
    if (!$computerFile) {
        # If the phone file doesn't exist on the computer, copy it
		$processes += Start-process -WindowStyle Hidden ./adb "pull -a `"$phoneFilePath`" `"$computerMusicPath`"" -PassThru
		Write-Host "$($filenames[-1])"
    } else {
        # If the phone file exists on the computer, compare the modified dates
		$computerModified = [int]($computerFile.LastWriteTimeUtc - (Get-Date "1/1/1970")).TotalSeconds        
		if ($timestamps[-1] -gt $computerModified) {
            # If the phone file is newer, copy it to the computer
			$processes += Start-process -WindowStyle Hidden ./adb "pull -a `"$phoneFilePath`" `"$computerMusicPath`"" -PassThru		
			Write-Host "$($filenames[-1]) (new version)"
        } else {
            # If the computer file is newer or the same, do nothing
        }
    }
}



Write-Host "`n________________________________________________________________________________"
Write-Host "COMPUTER TO PHONE"
Write-Host "--------------------------------------------------------------------------------`n"
foreach ($computerFile in $computerMusicFiles) {
    # Construct the full path of the computer file
    $computerFilePath = "$computerMusicPath\$computerFile"
	
    # Check if the computer file exists in the phone folder
    $phoneIndex =  $filenames.indexOf($computerFile.Name)
    if ($phoneIndex -eq -1) {
        # If the computer file doesn't exist on the phone, copy it
		$processes += Start-process -WindowStyle Hidden ./adb "push `"$computerFile`" `"$phoneMusicPath`"" -PassThru
		Write-host "$computerFile"
    } else {
        # If the computer file exists on the phone, compare the modified dates
		$computerModified = [int]($computerFile.LastWriteTimeUtc - (Get-Date "1/1/1970")).TotalSeconds        
        if ($computerModified -gt $timestamps[$phoneIndex] + 10) {
            # If the computer file is newer, copy it to the phone
            $processes += Start-process -WindowStyle Hidden ./adb "push `"$computerFilePath`" `"$phoneMusicPath`"" -PassThru
			Write-host "$computerFile (new version)"
        } else {
            # If the phone file is newer or the same, do nothing
        }
    }
}
#>

Write-Host "`nDO NOT UNPLUG YOUR DEVICE"
while ($processes | Where-Object { !$_.HasExited }) {
    Start-Sleep -Milliseconds 20
}
Write-Host "`nIt is now safe to unplug your device."
