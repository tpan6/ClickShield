# 🛡 ClickShield

**Real-time AI-powered anti-scam protection for Windows 11.**

ClickShield runs silently in your system tray. Every 30 seconds it takes a screenshot, reads your active browser URL, and asks a state-of-the-art multimodal AI whether you're looking at something dangerous. If it detects a scam, you get a warning — scaled to how serious the threat is.

---

## Why ClickShield?

Online scams are getting harder to spot. AI-generated phishing pages look pixel-perfect. Fake tech support pop-ups are convincing. Typosquatted domains fool even careful users. Traditional antivirus doesn't catch most of this because the content looks legitimate — it's only dangerous in context.

ClickShield uses the same visual reasoning that makes modern AI assistants useful for understanding what's actually on your screen and whether it's trying to trick you.

---

## How It Works

```
Your Screen
    │
    ▼  (every 30 seconds, or when a URL is pasted)
Screenshot + Active Browser URL + Clipboard URL
    │
    ▼  (sent via HTTPS to Alibaba Cloud DashScope)
Qwen 3.7-plus  ──  multimodal AI vision model
    │
    ▼  (returns severity score 0-10 + explanation)
ClickShield Warning Engine
    │
    ├── Score 0      → Silent (tray icon stays green)
    ├── Score 1-3    → System notification (bottom-right, 8s)
    ├── Score 4-6    → Pop-up overlay with "Continue Anyway" option
    └── Score 7-10  → Full-screen red overlay + alert sound
                       Mouse and keyboard are blocked until you acknowledge
```

---

## Warning Tiers

### 🟢 Clean (0) — Silent
Nothing happens. The tray icon stays green.

### 🟡 Low Risk (1–3) — Toast Notification
A small notification in the corner of your screen. No interruption to your workflow.

### 🟠 Medium Risk (4–6) — Overlay Dialog
A dark semi-transparent dialog appears over your screen. You can read the AI's explanation and choose to "Stay Safe" (recommended) or "Continue Anyway."

![Medium Overlay](docs/screenshots/medium_overlay.png)

### 🔴 High Risk (7–10) — Blocking Overlay
A full-screen red overlay appears with an alert sound. Your mouse and keyboard are temporarily intercepted — you must read the warning before you can dismiss it. A "Dismiss" button appears after 3 seconds. The overlay auto-releases after 60 seconds as a safety net.

![Blocking Overlay](docs/screenshots/blocking_overlay.png)

---

## What It Detects

| Threat Type | Examples |
|---|---|
| **Phishing** | Fake bank login, fake PayPal/Google/Microsoft sign-in, government impersonation |
| **Fake E-Commerce** | Too-good-to-be-true prices, payment harvesting forms, counterfeit product sites |
| **Tech Support Scam** | "Call Microsoft" pop-ups, fake BSOD screens, fake virus alerts with phone numbers |
| **Investment Scam** | Crypto "guaranteed returns," fake trading platforms, pump-and-dump schemes |
| **Lottery/Prize Scam** | "You've won," fake sweepstakes claim pages |
| **Malware Distribution** | Fake Flash/codec installer prompts, fake software update pages |
| **Social Engineering** | Extreme urgency language, threats, impersonation of authority figures |
| **Suspicious URLs** | Typosquatting (`arnazon.com`), misleading subdomains (`paypal.com.evil.xyz`), IDN homograph attacks |

ClickShield scores **0** (silent) for: normal desktop, developer tools, terminals, code editors, and known-legitimate sites (google.com, youtube.com, github.com, amazon.com on its real domain, etc.).

---

## Requirements

- **Windows 11** (Windows 10 may work, untested)
- **Internet connection** — screenshots are sent to Alibaba Cloud for analysis
- **DashScope API key** — free tier is sufficient for typical home use
- **RAM**: 4 GB minimum (ClickShield itself uses ~100 MB; the AI is cloud-based)

---

## Installation

### Option 1: Download the Installer (Recommended)

1. Download `ClickShield-Setup-x.x.x.exe` from the [Releases](../../releases) page
2. Run it — **no administrator / UAC prompt required**. Installs to your user profile.
3. Complete the setup wizard:
   - Accept the privacy disclosure (screenshots go to Alibaba Cloud)
   - Paste your DashScope API key ([how to get one](#getting-a-dashscope-api-key))
   - Choose your scan interval and whether to start with Windows
4. ClickShield starts monitoring immediately. Look for the shield icon in your tray.

### Option 2: Run from Source

```powershell
git clone https://github.com/tpan6/ClickShield
cd ClickShield

# Install dependencies (Python 3.11+ required)
pip install -e .

# Optional: install extra notification library
pip install uiautomation win10toast

# Run
python -m clickshield
```

The setup wizard will launch on first run.

---

## Getting a DashScope API Key

DashScope is Alibaba Cloud's AI platform. Qwen 3.7-plus is available on a free tier.

1. Go to **[dashscope-intl.aliyuncs.com](https://dashscope-intl.aliyuncs.com/)**
2. Create a free account
3. Navigate to **API Keys** in your dashboard
4. Create a new API key (starts with `sk-`)
5. Paste it into ClickShield's setup wizard

**Cost estimate for typical home use:** A screenshot is ~50–100KB as a JPEG. Qwen 3.7-plus charges per token; a typical analysis costs less than $0.001. At the default 30-second scan interval with a browser open for 4 hours/day, monthly cost is under $1.

---

## Configuration

Right-click the tray icon → **Settings** to adjust:

| Setting | Options | Default |
|---|---|---|
| Scan interval | 15s / 30s / 1 min / 5 min | 30s |
| Sound alerts | On / Off | On |
| Monitor clipboard | On / Off | On |
| API provider | DashScope / OpenRouter | DashScope |
| Start with Windows | On / Off | Off |

You can also **pause monitoring** from the tray menu (e.g., when screen sharing sensitive information), then resume it with one click.

### Threat Thresholds

By default:
- Severity ≥ 1 → toast notification
- Severity ≥ 4 → overlay dialog
- Severity ≥ 7 → blocking overlay

---

## Privacy

**What leaves your machine:** A JPEG screenshot (resized to max 1280×720, quality 75%) and the active browser URL are sent to Alibaba Cloud's DashScope API over HTTPS with each scan.

**What is NOT stored by ClickShield:** Nothing. There is no ClickShield server. Screenshots go directly from your computer to DashScope and nowhere else.

**Alibaba Cloud's handling:** Governed by their [privacy policy](https://www.alibabacloud.com/help/en/model-studio/). Per DashScope's terms, inputs to API calls are not used to train models.

**Your API key:** Stored in **Windows Credential Manager** — encrypted by Windows, never written to a plain-text file.

**You can pause ClickShield at any time** from the tray menu to stop all screenshot capture (e.g., when doing online banking, viewing medical records, or screen-sharing).

---

## Architecture

ClickShield is a single Python process using PyQt6 for the UI and a background thread for monitoring.

```
Main Thread (PyQt6 QApplication)
  ├── QSystemTrayIcon           — tray icon, context menu
  ├── MonitorWorker (QThread)   — capture loop (runs every N seconds)
  │     ├── ScreenCapture       — mss library, JPEG base64 encode
  │     ├── URLCapture          — Windows UI Automation reads browser address bar
  │     └── ClipboardMonitor    — detects URL pastes
  ├── LLMAnalyzer               — OpenAI SDK → DashScope API
  └── WarningManager
        ├── ToastNotification   — severity 1–3
        ├── OverlayDialog       — severity 4–6 (PyQt6 frameless window)
        └── BlockingOverlay     — severity 7–10 (grabs mouse + keyboard)
```

### Tech Stack

| Component | Library |
|---|---|
| UI + system tray | PyQt6 |
| Screenshot capture | mss + Pillow |
| Browser URL reading | uiautomation (Windows UIA) |
| AI analysis | openai SDK → DashScope |
| Secure key storage | win32cred (Windows Credential Manager) |
| Packaging | PyInstaller + Inno Setup |

### Supported Browsers (URL reading)

- Google Chrome
- Microsoft Edge
- Brave
- Firefox
- Opera / Vivaldi

URL reading uses the Windows UI Automation framework — no browser extension required, no admin privileges needed.

---

## Building from Source

Requirements: Python 3.11+, [PyInstaller](https://pyinstaller.org/), [Inno Setup 6](https://jrsoftware.org/isinfo.php)

```powershell
# One command — builds ClickShield.exe and the installer
.\installer\build.ps1

# Output:
# dist\ClickShield\ClickShield.exe   (portable)
# dist\ClickShield-Setup-0.1.0.exe  (installer)
```

The installer uses `PrivilegesRequired=lowest` — it installs to `%LOCALAPPDATA%\Programs\ClickShield` without a UAC prompt, making it easy for users to install without admin rights.

---

## Running Tests

```powershell
pip install -e ".[dev]"
pytest tests/ -v
```

The test suite covers the scoring engine and LLM response parser. Tests that require live Win32/UIA APIs (`test_capture.py`) are excluded from CI but can be run locally.

---

## Project Structure

```
ClickShield/
├── clickshield/
│   ├── __main__.py                  # Entry point
│   ├── core/
│   │   ├── scoring.py               # ThreatResult, ThreatLevel, ThreatSuppressor
│   │   ├── analyzer.py              # DashScope API client + JSON response parser
│   │   ├── capture.py               # Screenshot + URL + clipboard capture
│   │   └── monitor.py               # Background QThread capture loop
│   ├── ui/
│   │   ├── tray.py                  # System tray app shell
│   │   ├── toast.py                 # Low-severity toast (severity 1–3)
│   │   ├── overlay_dialog.py        # Medium-severity popup (severity 4–6)
│   │   ├── blocking_overlay.py      # High-severity full-screen lock (severity 7–10)
│   │   └── setup_wizard.py          # First-run wizard + settings dialog
│   ├── config/
│   │   ├── settings.py              # AppSettings dataclass (JSON persistence)
│   │   └── defaults.py              # Default config values
│   ├── utils/
│   │   ├── keystore.py              # Windows Credential Manager wrapper
│   │   ├── autostart.py             # HKCU Run registry key
│   │   ├── audio.py                 # Alert sound playback
│   │   └── logger.py                # Rotating file logger
│   └── resources/
│       ├── icons/                   # Tray icons (normal/scanning/warning/danger)
│       ├── sounds/                  # Alert sound (alert_high.wav)
│       └── prompts/
│           └── scam_analysis.txt    # VLM system prompt
├── installer/
│   ├── clickshield.spec             # PyInstaller spec
│   ├── setup.iss                    # Inno Setup installer script
│   └── build.ps1                    # One-command build script
├── tests/
│   ├── test_scoring.py
│   └── test_analyzer.py
└── .github/workflows/
    ├── ci.yml                       # Lint + tests on push
    └── build-release.yml            # Build .exe on tag push
```

---

## Roadmap

- [ ] Custom domain whitelist (mark a site as "always safe")
- [ ] Alert history log with screenshots
- [ ] Dark/light mode for the overlay dialogs
- [ ] Browser extension for lower-latency URL capture
- [ ] Optional local model mode (Ollama) for fully offline operation
- [ ] macOS support

---

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss significant changes.

```powershell
git clone https://github.com/tpan6/ClickShield
cd ClickShield
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT — see [LICENSE](LICENSE)

---

## Acknowledgements

- [Qwen team](https://github.com/QwenLM) at Alibaba for the multimodal model
- [Alibaba Cloud DashScope](https://dashscope-intl.aliyuncs.com/) for the API
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the UI framework
- [mss](https://python-mss.readthedocs.io/) for fast cross-platform screen capture
