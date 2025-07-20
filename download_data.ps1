# GCO Golf League Data Downloader - PowerShell Version
# Downloads the latest data from Google Sheets using browser credentials

param(
    [switch]$Manual,
    [string]$OutputFile = "gco_data.csv"
)

$SheetId = "1ZvtWd8zHMI0k2GQGMWhtFHl5xuDbciOW"
$BackupFile = "gco_data_backup.csv"

Write-Host "🏌️ GCO Golf League Data Downloader" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Backup existing data if it exists
if (Test-Path $OutputFile) {
    Write-Host "📋 Backing up existing data..." -ForegroundColor Yellow
    Copy-Item $OutputFile $BackupFile -Force
}

# Function to download with Invoke-WebRequest
function Download-WithWebRequest {
    param($Url, $Output)
    
    Write-Host "🔄 Attempting download with Invoke-WebRequest..." -ForegroundColor Cyan
    
    try {
        $headers = @{
            'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            'Accept' = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            'Accept-Language' = 'en-US,en;q=0.5'
            'DNT' = '1'
            'Connection' = 'keep-alive'
            'Upgrade-Insecure-Requests' = '1'
        }
        
        $response = Invoke-WebRequest -Uri $Url -Headers $headers -TimeoutSec 30 -UseBasicParsing
        
        # Check if we got valid CSV data (not HTML error page)
        if ($response.Content -and -not $response.Content.StartsWith('<!DOCTYPE')) {
            $response.Content | Out-File -FilePath $Output -Encoding UTF8
            Write-Host "✅ Successfully downloaded data" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠️ Downloaded content appears to be HTML error page" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "❌ Download failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to download using browser session
function Download-WithBrowserSession {
    param($Url, $Output)
    
    Write-Host "🔄 Attempting download with browser session..." -ForegroundColor Cyan
    
    try {
        # Try to use existing browser session/cookies
        $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        
        $response = Invoke-WebRequest -Uri $Url -WebSession $session -TimeoutSec 30 -UseBasicParsing
        
        if ($response.Content -and -not $response.Content.StartsWith('<!DOCTYPE')) {
            $response.Content | Out-File -FilePath $Output -Encoding UTF8
            Write-Host "✅ Successfully downloaded data with browser session" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠️ Downloaded content appears to be HTML error page" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "❌ Browser session download failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to open browser for manual download
function Start-ManualDownload {
    Write-Host ""
    Write-Host "🌐 Opening browser for manual download..." -ForegroundColor Cyan
    Write-Host "📥 Please download the file and save it as '$OutputFile'" -ForegroundColor Yellow
    Write-Host ""
    
    $ExportUrls = @(
        "https://docs.google.com/spreadsheets/d/$SheetId/export?format=csv&gid=0",
        "https://docs.google.com/spreadsheets/d/$SheetId/export?format=csv",
        "https://docs.google.com/spreadsheets/d/$SheetId/gviz/tq?tqx=out:csv"
    )
    
    Write-Host "🔗 Export URLs to try:" -ForegroundColor Cyan
    foreach ($url in $ExportUrls) {
        Write-Host "   $url" -ForegroundColor Gray
    }
    Write-Host ""
    
    # Open the first URL in default browser
    try {
        Start-Process $ExportUrls[0]
    }
    catch {
        Write-Host "ℹ️ Please manually open one of the URLs above in your browser" -ForegroundColor Blue
    }
    
    Write-Host "⏳ Waiting for manual download... (Press Enter when done, or Ctrl+C to cancel)" -ForegroundColor Yellow
    Read-Host
    
    if (Test-Path $OutputFile) {
        Write-Host "✅ Manual download completed successfully!" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ File not found. Please ensure you saved the file as '$OutputFile'" -ForegroundColor Red
        return $false
    }
}

# Main download logic
Write-Host "📡 Starting data download..." -ForegroundColor Cyan

# List of URLs to try
$Urls = @(
    "https://docs.google.com/spreadsheets/d/$SheetId/export?format=csv&gid=0",
    "https://docs.google.com/spreadsheets/d/$SheetId/export?format=csv",
    "https://docs.google.com/spreadsheets/d/$SheetId/gviz/tq?tqx=out:csv&gid=0"
)

$DownloadSuccess = $false

# Skip automated download if Manual switch is specified
if (-not $Manual) {
    # Try automated download first
    foreach ($url in $Urls) {
        Write-Host ""
        Write-Host "🎯 Trying URL: $url" -ForegroundColor Cyan
        
        if (Download-WithWebRequest $url $OutputFile) {
            $DownloadSuccess = $true
            break
        } elseif (Download-WithBrowserSession $url $OutputFile) {
            $DownloadSuccess = $true
            break
        }
    }
}

# If automated download failed or manual was requested, try manual download
if (-not $DownloadSuccess) {
    Write-Host ""
    if (-not $Manual) {
        Write-Host "⚠️ Automated download failed. The Google Sheet may require authentication." -ForegroundColor Yellow
        Write-Host "💡 Trying manual download using your browser's Google credentials..." -ForegroundColor Blue
    }
    
    if (Start-ManualDownload) {
        $DownloadSuccess = $true
    }
}

# Validate the downloaded file
if ($DownloadSuccess -and (Test-Path $OutputFile)) {
    Write-Host ""
    Write-Host "🔍 Validating downloaded data..." -ForegroundColor Cyan
    
    $fileInfo = Get-Item $OutputFile
    
    # Check file size
    if ($fileInfo.Length -eq 0) {
        Write-Host "❌ Downloaded file is empty" -ForegroundColor Red
        exit 1
    }
    
    # Check for basic CSV structure
    $firstLine = Get-Content $OutputFile -First 1
    if ($firstLine -match ",") {
        Write-Host "✅ File appears to be valid CSV format" -ForegroundColor Green
        
        # Show basic stats
        $lineCount = (Get-Content $OutputFile | Measure-Object).Count
        Write-Host "📊 File contains $lineCount lines" -ForegroundColor Blue
        
        # Show first few lines (header)
        Write-Host ""
        Write-Host "📋 File preview:" -ForegroundColor Cyan
        Get-Content $OutputFile -First 3 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
        
        Write-Host ""
        Write-Host "🎉 Data download completed successfully!" -ForegroundColor Green
        Write-Host "🚀 You can now run: streamlit run streamlit_app.py" -ForegroundColor Blue
        
    } else {
        Write-Host "⚠️ Downloaded file may not be valid CSV format" -ForegroundColor Yellow
        Write-Host "📄 First line of file:" -ForegroundColor Cyan
        Write-Host $firstLine -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "❌ Failed to download data" -ForegroundColor Red
    
    # Restore backup if available
    if (Test-Path $BackupFile) {
        Write-Host "🔄 Restoring backup data..." -ForegroundColor Yellow
        Move-Item $BackupFile $OutputFile -Force
        Write-Host "✅ Backup restored" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "💡 Manual alternative:" -ForegroundColor Blue
    Write-Host "1. Open: https://docs.google.com/spreadsheets/d/$SheetId/htmlview"
    Write-Host "2. Click File → Download → CSV"
    Write-Host "3. Save the file as '$OutputFile' in this directory"
    
    exit 1
}

# Clean up backup if everything went well
if (Test-Path $BackupFile) {
    Remove-Item $BackupFile -Force
}

Write-Host ""
Write-Host "✨ All done! The GCO Golf League app now has fresh data." -ForegroundColor Green