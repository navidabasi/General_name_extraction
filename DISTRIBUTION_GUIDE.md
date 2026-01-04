# Distribution Guide for macOS

## Build and Package Workflow

### Step 1: Build the Application
```bash
pyinstaller gui_app_macos.spec
```

**Output:** `dist/Name_Extractor.app` (Apple Silicon format if built on M1/M2/M3 Mac)

### Step 2: Create DMG File
```bash
# Option 1: Use Python script (recommended)
python3 create_dmg.py

# Option 2: Use shell script
./create_dmg.sh
```

**Output:** `dist/Name_Extractor.dmg`

### Step 3: Upload to WebDAV Server

Upload the DMG file to your WebDAV server:
```
https://u442456-sub1.your-storagebox.de/Updates/Name_Extractor/Name_Extractor.dmg
```

### Step 4: Update Version.json

Your `Version.json` on the server should look like:
```json
{
  "version": "1.0.3",
  "release_notes": "Bug fixes and improvements...",
  "download_url": "https://u442456-sub1.your-storagebox.de/Updates/Name_Extractor/Name_Extractor"
}
```

**Note:** The updater will automatically append `.dmg` for macOS or `.exe` for Windows.

## User Download Experience

### How Users Get the Update

1. **Automatic Update Check:**
   - App checks for updates on startup (if enabled)
   - Shows update dialog if new version available

2. **Manual Update Check:**
   - User clicks "Check for Updates" in menu
   - App downloads `Name_Extractor.dmg` from server

3. **After Download:**
   - DMG file opens automatically (mounts)
   - Finder window shows:
     - `Name_Extractor.app`
     - `Applications` folder (symlink)
   - User drags `.app` to Applications folder
   - Replaces old version

### First-Time Gatekeeper Warning

When users first open the app (after dragging to Applications):

1. **Right-click** on `Name_Extractor.app`
2. Select **"Open"** from context menu
3. Click **"Open"** in security dialog
4. App is added to exception list
5. Future launches work normally (double-click)

## Architecture Notes

### Apple Silicon (M1/M2/M3) Build
- Built on Apple Silicon Mac → Creates `arm64` binary
- Works on: Apple Silicon Macs only
- File size: ~50-100 MB (depends on dependencies)

### Intel Mac Build
- Built on Intel Mac → Creates `x86_64` binary  
- Works on: Intel Macs only
- File size: ~50-100 MB

### Universal Binary (Both Architectures)
To support both, you would need to:
1. Build on both architectures
2. Use `lipo` to combine binaries
3. Larger file size (~100-200 MB)

**Recommendation:** Build for your primary user base. Most modern Macs are Apple Silicon.

## File Structure on Server

```
Updates/Name_Extractor/
  ├── Version.json
  ├── Name_Extractor.exe    (Windows)
  └── Name_Extractor.dmg     (macOS)
```

## Testing the Update Flow

1. Build app: `pyinstaller gui_app_macos.spec`
2. Create DMG: `python3 create_dmg.py`
3. Upload DMG to server
4. Update Version.json with new version number
5. Test in app: Check for updates → Download → Install

## Troubleshooting

### DMG Won't Open
- Check file integrity: `hdiutil verify dist/Name_Extractor.dmg`
- Recreate DMG if corrupted

### App Won't Launch After Installation
- Check Console.app for errors
- Verify architecture matches user's Mac
- Ensure all dependencies are included

### Update Check Fails
- Verify Version.json is accessible
- Check WebDAV credentials
- Ensure download URL is correct

