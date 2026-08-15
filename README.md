# EthernetMonitor

![icon](./logo.png) <!-- Optional: Replace with actual path or badge -->

**EthernetMonitor** is a lightweight Windows system tray utility that monitors your Ethernet adapter's link speed and notifies you if it drops below an expected threshold. It's useful for power users, gamers, and network administrators who want to be alerted of degraded network conditions due to faulty cables, auto-negotiation failures, or hardware issues.

---

## 🚀 Features

- ⚙️ **Monitors a specific network interface** (e.g., "Ethernet") for status and link speed.
- 🔔 **Displays native Windows 10/11 toast notifications** when:
  * The link speed drops below your configured threshold.
  * The cable is unplugged (no link detected).
  * The adapter is disabled.
  * The selected adapter can't be found (removed or renamed).
- 🖱️ **Left-click the tray icon** to jump straight to Windows' Network Adapters window.
- 🔄 **"Current Link Speed" refreshes instantly** when you right-click the tray icon — no waiting for the next check interval.
- 🎛️ **Fully configurable via a tray menu**:
  * Select network adapter
  * Set expected link speed
  * Adjust monitoring and notification intervals
  * Toggle autostart on system boot
- 🔒 **Single-instance protection** — launching a second copy while one is already running exits immediately instead of creating a duplicate tray icon.
- 📁 Configuration stored in `config.json` (auto-generated)
- 🪟 Minimal, icon-based tray presence with dynamic icon change on warning
- 📜 Rotating log file (`ethernet_monitor.log`, capped at 10 MB) for activity and error tracking

Example:

<img width="363" height="327" alt="image" src="https://github.com/user-attachments/assets/47dab729-d380-4f0b-bf1e-7933926e0044" />

---

## 🖥️ Installation

To use **EthernetMonitor**:

1. **Download the latest release** from the [Releases](https://github.com/St0RM53/EthernetMonitor/releases) page.
2. Run `EthernetMonitor.exe`.
3. Configure the program by right clicking the tray icon and selecting your prefered settings. Don't forget to select the correct network interface you will be monitoring!

No installation is required. It runs in the background from the system tray.

---

## 🧭 First-Time Usage Guide

When you run the program for the first time, a tray icon will appear:

- ⚪ **Standard icon** – Ethernet is running at or above the expected speed.
- 🔴 **Red icon** – Speed is lower than expected, the cable is unplugged, the adapter is disabled, or the selected adapter can't be found.

### Right-click the tray icon to open the menu. Here's what each option does:

| **Menu Option**         | **Description**                                                               |
| ----------------------- | ----------------------------------------------------------------------------- |
| `Current: <interface>`  | Displays the currently monitored network adapter.                             |
| `Select Interface`      | Lists all detected network interfaces. Click to switch monitoring target.     |
| `Expected Speed`        | Choose the minimum link speed (e.g., 1000 Mbps) you expect from your adapter. |
| `Expected: <speed>`     | Displays your currently set expected speed.                                   |
| `Current Link Speed:`   | Shows the current link speed of the selected adapter (or its state, e.g. `Unplugged` / `Disabled` / `Not Found`). |
| `Check Interval`        | Frequency (in seconds or minutes) to check the adapter status.                |
| `Notification Interval` | How often to show speed warnings (prevents spamming).                         |
| `Open Config Folder`    | Opens the folder where `config.json` and log files are stored.                |
| `Open Network Adapters Folder` | Opens Windows' Network Connections panel. Same as left-clicking the tray icon. |
| `Start with Windows`    | Enable/disable automatic start when Windows boots.                            |
| `About`                 | Shows version info and credits.                                               |
| `GitHub Repository`     | Opens the project GitHub page in your browser.                                |
| `Quit`                  | Exits the application and removes tray icon.                                  |

💡 **Tip:** Left-click the tray icon at any time to jump straight to Windows' Network Adapters window.

---

## 🛠️ Configuration File

Located at `config.json`, it stores your preferences. Example structure:

```json
{
  "interface_name": "Ethernet",
  "expected_speed_mbps": 1000,
  "check_interval_seconds": 60,
  "notification_interval_seconds": 60,
  "start_with_windows": false
}
```

You normally don't need to edit this manually – use the tray menu instead.

---

## 🛡️ Requirements

- Windows 10 or 11

-------Optional--------

- Python 3.14 (only for development / running from source; tested on 3.14.4. End-users can use the compiled `.exe` instead.)
- Libraries (included in packaged build, see `requirements.txt`):
  * `psutil`
  * `pystray`
  * `Pillow`
  * `winotify`
  * `pywin32`
  * `winshell`

---

## 🏃‍♂️ Running the Python script directly (without building)

To run the program from source instead of the packaged `.exe`, set up a virtual environment first:

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python ethernet_monitor.py
```

The `.venv` folder is intentionally not tracked in this repository — each user creates their own locally with the commands above.

---

## 🧰 Building from Source (Optional)

To build your own `.exe` using PyInstaller, from the same virtual environment set up above:

```
python -m pip install pyinstaller
python -m pip install -r requirements.txt
pyinstaller --clean --noconfirm ethernet_monitor.spec
```

If you're using `.png` icons or external files, you may need to update the `.spec` file to include them.

---

## 🐞 Troubleshooting

- **No error shows up?**
  * Open config folder (right click on tray or in `%appdata%\EthernetMonitor\`) and check `ethernet_monitor.log` for errors.
- **The app won't start / nothing happens?**
  * EthernetMonitor only allows one running instance at a time. Check whether it's already running in the system tray (including hidden tray icons) before assuming it failed to launch.

---

## 📜 License

This project is licensed under the **GNU AGPLv3**. See the [LICENSE](https://github.com/St0RM53/EthernetMonitor/blob/main/LICENSE) file for details.

---

## 🤝 Credits

- Developed by **St0RM53**
- Notification system by [winotify](https://github.com/versa-syahptr/winotify)

---

## 🌐 Links

- 🔗 GitHub: <https://github.com/St0RM53/EthernetMonitor>
- 💬 Issues or suggestions? [Open an issue](https://github.com/St0RM53/EthernetMonitor/issues)
