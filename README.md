# 🛡 ClickShield

**Real-time AI-powered anti-scam protection for Windows 11.**

ClickShield runs silently in your system tray. Every 30 seconds it takes a screenshot, reads your active browser URL, fetches the page content, and asks a state-of-the-art multimodal AI whether you're looking at something dangerous. If it detects a scam, you get a warning — scaled to how serious the threat is.

---

## Why ClickShield?

Online scams are getting harder to spot. AI-generated phishing pages look pixel-perfect. Fake tech support pop-ups are convincing. Typosquatted domains fool even careful users. Traditional antivirus doesn't catch most of this because the content looks legitimate — it's only dangerous in context.

ClickShield uses visual reasoning + page content analysis to understand what's actually on your screen and whether it's trying to trick you.

---

## How It Works

```
Your Screen
    │
    ▼  (every 30 seconds, or when a URL is pasted)
Screenshot + Active Browser URL + Page HTML Text + Clipboard URL
    │
    ▼  (sent via HTTPS to OpenAI)
GPT-5.4-nano  ──  multimodal AI vision model
    │
    ▼  (returns severity score 0–10 + explanation)
ClickShield Warning Engine
    │
    ├── Score 0      → Silent (tray icon stays green)
    ├── Score 1–3    → System notification (bottom-right, 8 s)
    ├── Score 4–6    → Pop-up overlay with "Continue Anyway" option
    └── Score 7–10  → Full-screen red overlay + alert sound
                       Mouse and keyboard are blocked until you acknowledge
```

The model receives three signals simultaneously — the screenshot, the live page text (title, body copy, password field detection), and the URL — giving it far more context than a URL checker alone.

---

## Warning Tiers

### 🟢 Clean (0) — Silent
Nothing happens. The tray icon stays green.

### 🟡 Low Risk (1–3) — Toast Notification
A small notification in the corner of your screen. No interruption to your workflow.

### 🟠 Medium Risk (4–6) — Overlay Dialog
A dark semi-transparent dialog appears over your screen. You can read the AI's explanation and choose to "Stay Safe" (recommended) or "Continue Anyway."

### 🔴 High Risk (7–10) — Blocking Overlay
A full-screen red overlay appears with an alert sound. Your mouse and keyboard are temporarily intercepted — you must read the warning before you can dismiss it. A "Dismiss" button appears after 3 seconds. The overlay auto-releases after 60 seconds as a safety net.

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

## Scan History Dashboard

Open the dashboard from the tray menu (**Dashboard…**) to review every scan ClickShield has performed:

- **Filterable table** — filter by All / Threats only / High / Medium / Low / Clean
- **Screenshot preview** — see exactly what was on screen when each scan ran
- **Full detail panel** — AI explanation, indicator bullets, raw model response
- **Auto-refreshes** every 10 seconds while open
- **Clear All** button to delete history and free disk space

Scan records (and their screenshots) are stored locally in `~/.clickshield/`. The last 200 scans are kept; older ones are pruned automatically.

---

## Requirements

- **Windows 11** (Windows 10 may work, untested)
- **Internet connection** — screenshots and page text are sent to OpenAI for analysis
- **OpenAI API key** — standard pay-as-you-go pricing applies
- **RAM**: 4 GB minimum (ClickShield itself uses ~100 MB; the AI is cloud-based)

---

## Installation

### Option 1: Download the Installer (Recommended)

1. Download `ClickShield-Setup-x.x.x.exe` from the [Releases](../../releases) page
2. Run it — **no administrator / UAC prompt required**. Installs to your user profile.
3. Complete the setup wizard:
   - Accept the privacy disclosure (screenshots and page text go to OpenAI)
   - Paste your OpenAI API key ([how to get one](#getting-an-openai-api-key))
   - Choose your scan interval and whether to start with Windows
4. ClickShield starts monitoring immediately. Look for the shield icon in your tray.

### Option 2: Run from Source

```powershell
git clone https://github.com/tpan6/ClickShield
cd ClickShield

# Install dependencies (Python 3.11+ required)
pip install -e .

# Run
python -m clickshield
```

The setup wizard will launch on first run.

---

## Getting an OpenAI API Key

1. Go to **[platform.openai.com/api-keys](https://platform.openai.com/api-keys)**
2. Sign in or create a free account
3. Click **Create new secret key**
4. Copy the key (starts with `sk-`) and paste it into ClickShield's setup wizard

**Cost estimate for typical home use:** GPT-5.4-nano is priced at ~$0.20 per million input tokens. A typical scan (screenshot + page text) costs well under $0.001. At the default 30-second scan interval with a browser open 4 hours/day, monthly cost is under $1.

---

## Configuration

Right-click the tray icon → **Settings** to adjust:

| Setting | Options | Default |
|---|---|---|
| Scan interval | 15 s / 30 s / 1 min / 5 min | 30 s |
| Sound alerts | On / Off | On |
| Monitor clipboard | On / Off | On |
| Fetch page HTML | On / Off | On |
| API provider | OpenAI / OpenRouter | OpenAI |
| Start with Windows | On / Off | Off |

You can also **pause monitoring** from the tray menu (e.g., when screen sharing sensitive information), then resume it with one click.

### Threat Thresholds

By default:
- Severity ≥ 1 → toast notification
- Severity ≥ 4 → overlay dialog
- Severity ≥ 7 → blocking overlay

---

## Privacy

**What leaves your machine:** A JPEG screenshot (resized to max 1280×720, quality 75%), the active browser URL, and stripped page text content are sent to the OpenAI API over HTTPS with each scan.

**What is NOT stored by ClickShield:** There is no ClickShield server. Data goes directly from your computer to OpenAI and nowhere else.

**OpenAI's handling:** Governed by their [privacy policy](https://openai.com/policies/privacy-policy). API inputs are not used to train OpenAI models per their API terms.

**Local scan history:** Screenshots and scan records are saved to `~/.clickshield/` on your machine only. Use the Dashboard's "Clear All" button to delete them at any time.

**Your API key:** Stored in **Windows Credential Manager** — encrypted by Windows, never written to a plain-text file.

**You can pause ClickShield at any time** from the tray menu to stop all screenshot capture (e.g., when doing online banking, viewing medical records, or screen-sharing).

---

## Architecture

ClickShield is a single Python process using PyQt6 for the UI and a background thread for monitoring.

```
Main Thread (PyQt6 QApplication)
  ├── QSystemTrayIcon            — tray icon, context menu
  ├── HistoryStore               — JSON + screenshot persistence (~/.clickshield/)
  ├── DashboardWindow            — scan history viewer (opened on demand)
  └── MonitorWorker (QThread)    — capture loop (runs every N seconds)
        ├── ScreenCapture        — mss library, JPEG base64 encode
        ├── URLCapture           — Windows UI Automation reads browser address bar
        ├── HTMLCapture          — fetches and strips active page text
        ├── ClipboardMonitor     — detects URL pastes
        └── LLMAnalyzer          — OpenAI SDK → GPT-5.4-nano
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
| Page content analysis | requests + stdlib html.parser |
| AI analysis | openai SDK → GPT-5.4-nano |
| Scan history | JSON + JPEG files in `~/.clickshield/` |
| Secure key storage | win32cred (Windows Credential Manager) |
| Packaging | PyInstaller + Inno Setup |

### Supported Browsers (URL + HTML reading)

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

The installer uses `PrivilegesRequired=lowest` — it installs to `%LOCALAPPDATA%\Programs\ClickShield` without a UAC prompt.

---

## Running Tests

```powershell
pip install -e ".[dev]"
pytest tests/ -v
```

The test suite covers the scoring engine and LLM response parser. Tests that require live Win32/UIA APIs are excluded from CI but can be run locally.

---

## Project Structure

```
ClickShield/
├── clickshield/
│   ├── __main__.py                  # Entry point
│   ├── core/
│   │   ├── scoring.py               # ThreatResult, ThreatLevel, ThreatSuppressor
│   │   ├── analyzer.py              # OpenAI API client + JSON response parser
│   │   ├── capture.py               # Screenshot + URL + HTML + clipboard capture
│   │   ├── history.py               # ScanRecord dataclass + HistoryStore persistence
│   │   └── monitor.py               # Background QThread capture loop
│   ├── ui/
│   │   ├── tray.py                  # System tray app shell
│   │   ├── dashboard.py             # Scan history dashboard window
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
│           └── scam_analysis.txt    # LLM system prompt
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
- [ ] Export dashboard history to CSV
- [ ] Dark/light mode for the overlay dialogs
- [ ] Browser extension for lower-latency URL capture
- [ ] Optional local model mode for fully offline operation
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

- [OpenAI](https://openai.com/) for GPT-5.4-nano
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the UI framework
- [mss](https://python-mss.readthedocs.io/) for fast cross-platform screen capture
