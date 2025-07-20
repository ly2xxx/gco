#!/bin/bash

# GCO Golf League Data Downloader
# Downloads the latest data from Google Sheets using browser credentials

set -e

SHEET_ID="1ZvtWd8zHMI0k2GQGMWhtFHl5xuDbciOW"
OUTPUT_FILE="gco_data.csv"
BACKUP_FILE="gco_data_backup.csv"

echo "🏌️ GCO Golf League Data Downloader"
echo "=================================="

# Backup existing data if it exists
if [ -f "$OUTPUT_FILE" ]; then
    echo "📋 Backing up existing data..."
    cp "$OUTPUT_FILE" "$BACKUP_FILE"
fi

# Function to try downloading with curl using various methods
download_with_curl() {
    local url="$1"
    local output="$2"
    
    echo "🔄 Attempting download with curl..."
    
    # Try with browser-like headers
    if curl -L -s \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
        -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" \
        -H "Accept-Language: en-US,en;q=0.5" \
        -H "Accept-Encoding: gzip, deflate" \
        -H "DNT: 1" \
        -H "Connection: keep-alive" \
        -H "Upgrade-Insecure-Requests: 1" \
        --compressed \
        "$url" -o "$output"; then
        
        # Check if we got valid CSV data (not HTML error page)
        if head -1 "$output" | grep -v "<!DOCTYPE" > /dev/null 2>&1; then
            echo "✅ Successfully downloaded data with curl"
            return 0
        else
            echo "⚠️ Downloaded file appears to be HTML error page"
            rm -f "$output"
            return 1
        fi
    else
        echo "❌ Curl download failed"
        return 1
    fi
}

# Function to try downloading with wget
download_with_wget() {
    local url="$1"
    local output="$2"
    
    echo "🔄 Attempting download with wget..."
    
    if command -v wget > /dev/null 2>&1; then
        if wget -q --timeout=30 \
            --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
            --header="Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
            "$url" -O "$output"; then
            
            # Check if we got valid CSV data
            if head -1 "$output" | grep -v "<!DOCTYPE" > /dev/null 2>&1; then
                echo "✅ Successfully downloaded data with wget"
                return 0
            else
                echo "⚠️ Downloaded file appears to be HTML error page"
                rm -f "$output"
                return 1
            fi
        else
            echo "❌ Wget download failed"
            return 1
        fi
    else
        echo "⚠️ wget not available"
        return 1
    fi
}

# Function to open browser for manual download
manual_download() {
    echo ""
    echo "🌐 Opening browser for manual download..."
    echo "📥 Please download the file and save it as '$OUTPUT_FILE'"
    echo ""
    
    # Try different export URLs
    EXPORT_URLS=(
        "https://docs.google.com/spreadsheets/d/$SHEET_ID/export?format=csv&gid=0"
        "https://docs.google.com/spreadsheets/d/$SHEET_ID/export?format=csv"
        "https://docs.google.com/spreadsheets/d/$SHEET_ID/gviz/tq?tqx=out:csv"
    )
    
    echo "🔗 Export URLs to try:"
    for url in "${EXPORT_URLS[@]}"; do
        echo "   $url"
    done
    echo ""
    
    # Open the first URL in default browser
    if command -v xdg-open > /dev/null 2>&1; then
        xdg-open "${EXPORT_URLS[0]}" 2>/dev/null &
    elif command -v open > /dev/null 2>&1; then
        open "${EXPORT_URLS[0]}" 2>/dev/null &
    elif command -v start > /dev/null 2>&1; then
        start "${EXPORT_URLS[0]}" 2>/dev/null &
    else
        echo "ℹ️ Please manually open one of the URLs above in your browser"
    fi
    
    echo "⏳ Waiting for manual download... (Press Enter when done, or Ctrl+C to cancel)"
    read -r
    
    if [ -f "$OUTPUT_FILE" ]; then
        echo "✅ Manual download completed successfully!"
        return 0
    else
        echo "❌ File not found. Please ensure you saved the file as '$OUTPUT_FILE'"
        return 1
    fi
}

# Main download logic
echo "📡 Starting data download..."

# List of URLs to try
URLS=(
    "https://docs.google.com/spreadsheets/d/$SHEET_ID/export?format=csv&gid=0"
    "https://docs.google.com/spreadsheets/d/$SHEET_ID/export?format=csv"
    "https://docs.google.com/spreadsheets/d/$SHEET_ID/gviz/tq?tqx=out:csv&gid=0"
)

# Try automated download first
DOWNLOAD_SUCCESS=false

for url in "${URLS[@]}"; do
    echo ""
    echo "🎯 Trying URL: $url"
    
    if download_with_curl "$url" "$OUTPUT_FILE"; then
        DOWNLOAD_SUCCESS=true
        break
    elif download_with_wget "$url" "$OUTPUT_FILE"; then
        DOWNLOAD_SUCCESS=true
        break
    fi
done

# If automated download failed, try manual download
if [ "$DOWNLOAD_SUCCESS" = false ]; then
    echo ""
    echo "⚠️ Automated download failed. The Google Sheet may require authentication."
    echo "💡 Trying manual download using your browser's Google credentials..."
    
    if manual_download; then
        DOWNLOAD_SUCCESS=true
    fi
fi

# Validate the downloaded file
if [ "$DOWNLOAD_SUCCESS" = true ] && [ -f "$OUTPUT_FILE" ]; then
    echo ""
    echo "🔍 Validating downloaded data..."
    
    # Check file size
    if [ ! -s "$OUTPUT_FILE" ]; then
        echo "❌ Downloaded file is empty"
        exit 1
    fi
    
    # Check for basic CSV structure
    if head -1 "$OUTPUT_FILE" | grep -q ","; then
        echo "✅ File appears to be valid CSV format"
        
        # Show basic stats
        LINE_COUNT=$(wc -l < "$OUTPUT_FILE")
        echo "📊 File contains $LINE_COUNT lines"
        
        # Show first few lines (header)
        echo ""
        echo "📋 File preview:"
        head -3 "$OUTPUT_FILE"
        
        echo ""
        echo "🎉 Data download completed successfully!"
        echo "🚀 You can now run: streamlit run streamlit_app.py"
        
    else
        echo "⚠️ Downloaded file may not be valid CSV format"
        echo "📄 First line of file:"
        head -1 "$OUTPUT_FILE"
    fi
else
    echo ""
    echo "❌ Failed to download data"
    
    # Restore backup if available
    if [ -f "$BACKUP_FILE" ]; then
        echo "🔄 Restoring backup data..."
        mv "$BACKUP_FILE" "$OUTPUT_FILE"
        echo "✅ Backup restored"
    fi
    
    echo ""
    echo "💡 Manual alternative:"
    echo "1. Open: https://docs.google.com/spreadsheets/d/$SHEET_ID/htmlview"
    echo "2. Click File → Download → CSV"
    echo "3. Save the file as '$OUTPUT_FILE' in this directory"
    
    exit 1
fi

# Clean up backup if everything went well
if [ -f "$BACKUP_FILE" ]; then
    rm -f "$BACKUP_FILE"
fi

echo ""
echo "✨ All done! The GCO Golf League app now has fresh data."