# USB Android Speaker - App-Free Audio Transmitter via Physical Link

[中文说明文档](README_ZH.md)

`USB Android Speaker` is a one-click audio streaming and projection tool designed for Windows PCs and Android phones, featuring **ultra-low latency and no app installation required on the mobile client**.

By utilizing a wired USB link, you can turn your Android phone into an external physical speaker for your Windows PC. The audio-video synchronization latency can be as low as **20ms to 40ms**, delivering a near-instant physical audio transmission experience.

---

## 🌟 Core Features & Architectural Design

This project is built from **first principles** to eliminate the need for users to download and install third-party mobile applications. Instead, it utilizes the phone's native browser and underlying network tunnels for maximum efficiency:

```
[Windows PC Client]                                     [Android Phone Client]
  +------------------+                                      +------------------+
  |  WASAPI Loopback |                                      |  System Browser  |
  | (Capture System) |                                      |                  |
  +--------+---------+                                      +--------+---------+
           |                                                         ^
           v                                                         |
  +--------+---------+                                      +--------+---------+
  |  Python Audio Srv|                                      |   Web Audio API  |
  | (WebSocket PCM)  |                                      | (PCM Playback &  |
  +--------+---------+                                      |  Jitter Buffer)  |
           |                                                +--------+---------+
           |                                                         ^
           +============[ ADB Reverse / USB Cable ]==================+
                     (Physical debug tunnel 127.0.0.1:8000)
```

1. **WASAPI Loopback Capture**:
   Uses `PyAudioWPatch` to access the Windows WASAPI loopback interface, directly capturing the digital audio stream of active speakers/headphones. This preserves native audio quality without hollow room echo.
2. **ADB Reverse Tunneling**:
   Leverages `adb reverse tcp:8000 tcp:8000` to forward port 8000 on the phone to the PC. Communication runs entirely over the physical USB data cable, bypassing WiFi isolation, public AP limits, and Windows firewall blocks.
3. **App-Free Web Client**:
   No app installation needed. The system default browser connects via WebSocket to retrieve raw PCM binary chunks, decoding and playing them directly via Web Audio API.
4. **Self-Healing Multi-Route Fallback**:
   The backend injects all available PC network interface IPs (loopback, USB tethering gateways, WLAN IPs, etc.) into the web page. The client-side JS automatically polls and rotates through these IPs within a second if local loopback fails due to browser sandbox restrictions.
5. **Adaptive Screen Auto-Click**:
   Queries the phone's physical screen resolution dynamically via ADB, calculates the geometric center coordinate, and triggers a background tap command once the WebSocket connection is established. This bypasses the Android browser's Autoplay Policy restriction.

---

## 🚀 Quick Start

### Prerequisites

1. **PC Client**:
   - A USB cable capable of data transfer.
   - `adb` configured in the system PATH (run `adb devices` to verify).
   - Audio playback device enabled (headphones or speakers connected so WASAPI loopback driver works).
2. **Phone Client**:
   - Phone screen unlocked and **"USB Debugging"** enabled in Developer options.
   - When launching the PC client, verify and check "Always allow" on the phone's authorization prompt.

### Running the Application

#### Method 1: Running the Executable (Recommended)

Double-click **`Android_Speaker.exe`** on your desktop.
The application will automatically perform:
- Inbound firewall rule diagnostics (choose "Yes" if UAC prompts to allow port 8000).
- ADB device connection and permission verification.
- Mobile browser launch and auto-click activation.

#### Method 2: Running via Python Source Code

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the script:
   ```bash
   python stream_audio.py
   ```

---

## 🛠️ Local Build & Packaging

If you make modifications to the source code, compile the script into a standalone `.exe` using PyInstaller:

```bash
python -m PyInstaller --onefile --clean --noconfirm --distpath ./dist --name "Android_Speaker" --icon="icon.ico" "stream_audio.py"
```

---

## 🤖 GitHub Actions CI/CD Pipeline

This project is configured with a GitHub Actions workflow (`.github/workflows/build-executable.yml`) for automated builds.

### Build Workflow

On every `git push` to `main`/`master` or when a `release` is created, the pipeline will:
1. Spin up a `windows-latest` virtual machine.
2. Set up Python and restore package dependencies via pip.
3. Run PyInstaller to bundle the script with `icon.ico` embedded.
4. Upload the compiled `Android_Speaker.exe` as a GitHub Action Artifact, allowing immediate download from the Action Run summary page.
