# EthernetMonitor

![icon](./logo.png) <!-- Optional: Replace with actual path or badge -->

**EthernetMonitor** is a lightweight Windows system tray utility that monitors your Ethernet adapter's link speed and notifies you if it drops below an expected threshold. It’s useful for power users, gamers, and network administrators who want to be alerted of degraded network conditions due to faulty cables, auto-negotiation failures, or hardware issues.

---

## 🚀 Features

- ⚙️ **Monitors a specific network interface** (e.g., "Ethernet") for status and link speed.
- 🔔 **Displays native Windows 10/11 toast notifications** when the speed drops below a configured threshold.
- 🎛️ **Fully configurable via a tray menu**:
  - Select network adapter
  - Set expected link speed
  - Adjust monitoring and notification intervals
  - Toggle autostart on system boot
- 📁 Configuration stored in `config.json` (auto-generated)
- 🪟 Minimal, icon-based tray presence with dynamic icon change on warning
- 📜 Log file (`ethernet_monitor.log`) for activity and error tracking

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
- 🔴 **Red icon** – Speed is lower than expected or connection is down.

### Right-click the tray icon to open the menu. Here's what each option does:

| **Menu Option**                     | **Description**                                                                 |
|------------------------------------|---------------------------------------------------------------------------------|
| `Current: <interface>`             | Displays the currently monitored network adapter.                              |
| `Select Interface`                 | Lists all detected network interfaces. Click to switch monitoring target.      |
| `Expected Speed`                   | Choose the minimum link speed (e.g., 1000 Mbps) you expect from your adapter.  |
| `Expected: <speed>`                | Displays your currently set expected speed.                                    |
| `Current Link Speed:`              | Shows the current link speed of the selected adapter.                          |
| `Check Interval`                   | Frequency (in seconds or minutes) to check the adapter status.                 |
| `Notification Interval`            | How often to show speed warnings (prevents spamming).                          |
| `Open Config Folder`               | Opens the folder where `config.json` and log files are stored.                 |
| `Start with Windows`               | Enable/disable automatic start when Windows boots.                             |
| `About`                            | Shows version info and credits.                                                |
| `GitHub Repository`                | Opens the project GitHub page in your browser.                                 |
| `Quit`                             | Exits the application and removes tray icon.                                   |

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

You normally don’t need to edit this manually – use the tray menu instead.

---

## 🛡️ Requirements

- Windows 10 or 11
  
-------Optional--------
- Python 3.10+ (only for development; end-users can use compiled `.exe`)
- Libraries (included in packaged build):
  - `psutil`
  - `pystray`
  - `Pillow`
  - `winotify`
  - `pywin32`
  - `winshell`

---

## 🏃‍♂️ Running python script directly (without build)

To run the program with python without building it:

```bash
python ethernet_monitor.py
```

---

## 🧰 Building from Source (Optional)

To build your own `.exe` using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm ethernet_monitor.spec
```

If you're using `.png` icons or external files, you may need to update the `.spec` file to include them.

---

## 🐞 Troubleshooting

- **No error shows up?**
  - Open config folder (right click on tray or in `%appdata%\EthernetMonitor\`) and check `ethernet_monitor.log` for errors.
    
---

## 📜 License

This project is licensed under the **GNU AGPLv3**. See the [LICENSE](LICENSE) file for details.

---

## 🤝 Credits

- Developed by **St0RM53**
- Notification system by [winotify](https://github.com/versa-syahptr/winotify)

---

## 🌐 Links

- 🔗 GitHub: [https://github.com/St0RM53/EthernetMonitor](https://github.com/St0RM53/EthernetMonitor)
- 💬 Issues or suggestions? [Open an issue](https://github.com/St0RM53/EthernetMonitor/issues)
