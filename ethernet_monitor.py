import os
import re
import sys
import json
import time
import threading
import logging
from logging.handlers import RotatingFileHandler
import ctypes
import webbrowser
import subprocess
from collections import namedtuple
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

import psutil
import winshell
import win32com.client
import win32event
import win32api
import winerror
from pystray import Icon, MenuItem as item, Menu
from winotify import Notification, audio
from PIL import Image

import tkinter as tk
from tkinter import messagebox   # Alternative messagebox solution that works in W11 24H2


APP_NAME = "EthernetMonitor"
APPDATA_DIR = Path(os.getenv("APPDATA")) / APP_NAME
APPDATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APPDATA_DIR / "config.json"
LOG_PATH = APPDATA_DIR / "ethernet_monitor.log"


LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
LOG_BACKUP_COUNT = 2               # keep 2 rotated files (~30 MB total on disk, worst case)

_log_handler = RotatingFileHandler(
    filename=str(LOG_PATH),
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
    encoding="utf-8"
)
_log_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
logging.basicConfig(level=logging.DEBUG, handlers=[_log_handler])


print("Script started...")

DEFAULT_CONFIG = {
    "interface_name": "Ethernet",
    "expected_speed_mbps": 1000,
    "check_interval_seconds": 60,
    "notification_interval_seconds": 60,
    "start_with_windows": False
}

INTERVAL_OPTIONS = {
    "10 sec": 10,
    "1 min": 60,
    "5 min": 300,
    "10 min": 600,
    "30 min": 1800,
    "1 hour": 3600,
    "12 hours": 43200
}

NOTIFICATION_INTERVAL_OPTIONS = {
    "10 sec": 10,
    "30 sec": 30,
    "1 min": 60,
    "5 min": 300,
    "10 min": 600
}

SPEED_OPTIONS = [100, 1000, 2500, 5000, 10000]
last_notification_time = None
last_speed = None

def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.abspath(filename)

# --- Startup Management ---

def get_startup_folder():
    return winshell.startup()

def get_shortcut_path():
    return os.path.join(get_startup_folder(), f"{APP_NAME}.lnk")

def add_to_startup():
    shortcut_path = get_shortcut_path()
    target = sys.executable
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = target
    shortcut.Arguments = ""  # Don't pass script path
    shortcut.WorkingDirectory = os.path.dirname(target)  # Proper start dir
    #shortcut.IconLocation = os.path.abspath("ethernet_monitor_icon.ico")  # Breaks icon for the startup shortcut; when you leave it out explorer uses the targeted exe icon, so it's the simplest solution
    shortcut.Save()
    logging.info(f"[Startup] Added to startup: {shortcut_path}")


def remove_from_startup():
    shortcut_path = get_shortcut_path()
    if os.path.exists(shortcut_path):
        try:
            os.remove(shortcut_path)
            logging.info(f"[Startup] Removed from startup: {shortcut_path}")
        except Exception as e:
            logging.error(f"[Startup] Failed to remove shortcut: {e}")

# --- Configuration ---

def save_config(config_data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config_data, f, indent=4)


def load_config():
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def set_check_interval(seconds):
    config = load_config()
    config["check_interval_seconds"] = seconds
    save_config(config)
    logging.info(f"Check interval set to {seconds} seconds")

# --- Network Interface ---

def list_interfaces():
    return list(psutil.net_if_stats().keys())

def select_interface(interface_name):
    config = load_config()
    config["interface_name"] = interface_name
    save_config(config)
    logging.info(f"Interface changed to: {interface_name}")

# state is one of: "missing", "disabled", "unplugged", "up"
InterfaceStatus = namedtuple("InterfaceStatus", ["state", "speed"])

def get_interface_admin_state(interface_name):
    """
    Returns the Windows "Admin State" ("Enabled"/"Disabled") for the given
    interface via `netsh interface show interface`, or None if it can't be
    determined (netsh failed, or no interface with that exact name exists).

    psutil's isup is only an operational (link) status - it can't tell us
    whether an adapter is administratively disabled vs. just unplugged, so
    we go to netsh for that one extra bit of information.
    """
    try:
        output = subprocess.check_output(
            ["netsh", "interface", "show", "interface"],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        logging.error(f"Failed to query netsh interface state: {e}")
        return None

    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("-") or line.lower().startswith("admin state"):
            continue
        # Columns are separated by runs of 2+ spaces: Admin State | State | Type | Interface Name
        parts = re.split(r"\s{2,}", line)
        if len(parts) < 4:
            continue
        admin_state, name = parts[0], " ".join(parts[3:])
        if name == interface_name:
            return admin_state
    return None

def classify_interface(interface_name):
    """
    Single source of truth for "what's going on with this interface right
    now", used by both the tray menu label and the monitor loop so they
    never disagree.
    """
    stats = psutil.net_if_stats()
    nic = stats.get(interface_name)

    if nic is None:
        # Not present in the OS's adapter list at all: removed, or renamed.
        return InterfaceStatus("missing", None)

    if not nic.isup:
        admin_state = get_interface_admin_state(interface_name)
        if admin_state and admin_state.strip().lower() == "disabled":
            return InterfaceStatus("disabled", None)
        return InterfaceStatus("unplugged", None)

    return InterfaceStatus("up", nic.speed)

def get_current_link_speed(interface_name):
    status = classify_interface(interface_name)
    if status.state == "missing":
        return "Not Found"
    if status.state == "disabled":
        return "Disabled"
    if status.state == "unplugged":
        return "Unplugged"
    if status.speed and status.speed > 0:
        return f"{status.speed} Mbps"
    return "Unknown"

# --- Notifications ---

def notify_once_every_limited_interval(message, dedupe_key):
    """
    dedupe_key identifies "what kind of alert is this" (e.g. a speed value,
    or a state string like "disabled"/"unplugged"/"missing") so a change in
    condition always notifies immediately, while the same condition repeats
    only once per notification_interval_seconds.
    """
    global last_notification_time, last_speed
    now = datetime.now()
    config = load_config()
    interval_seconds = config.get("notification_interval_seconds", 60)

    if (last_speed != dedupe_key) or not last_notification_time or (now - last_notification_time) > timedelta(seconds=interval_seconds):
        last_notification_time = now
        last_speed = dedupe_key
        try:
            toast = Notification(
                app_id="Ethernet Monitor",
                title="Ethernet Speed Alert",
                msg=message,
                icon=os.path.abspath("ethernet_monitor_icon.ico")
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
            logging.info("Notification sent: " + message)
        except Exception as e:
            logging.error(f"Failed to show toast: {e}")

# --- Tray Menu Actions ---

def set_expected_speed(icon, item):
    label = str(item)
    try:
        speed = int(label.split()[0])
        config = load_config()
        config["expected_speed_mbps"] = speed
        save_config(config)
        icon.menu = build_menu(icon)
        print(f"[Info] Expected speed set to {speed} Mbps")
    except Exception as e:
        print(f"[ERROR] Failed to parse expected speed: {e}")

def set_interval_and_refresh(icon=None, item=None, val=60):
    set_check_interval(val)
    if icon:
        icon.menu = build_menu(icon)

def set_notification_interval_and_refresh(icon=None, item=None, val=60):
    config = load_config()
    config["notification_interval_seconds"] = val
    save_config(config)
    if icon:
        icon.menu = build_menu(icon)

def change_interface(icon, interface_name, *_):
    select_interface(interface_name)
    icon.menu = build_menu(icon)

def toggle_startup(icon, item):
    config = load_config()
    config["start_with_windows"] = not config.get("start_with_windows", False)
    save_config(config)
    if config["start_with_windows"]:
        add_to_startup()
    else:
        remove_from_startup()

def quit_action(icon, item):
    icon.visible = False
    icon.stop()

def show_about(icon=None, item=None):
    def show():
        root = tk.Tk()
        root.withdraw()  # Hide main window
        messagebox.showinfo(
            "About Ethernet Monitor",
            "Ethernet Monitor\n"
            "Version: 1.1.0\n"
            "Date: 15/08/26\n"
            "Author: St0RM53\n"
            "GitHub: https://github.com/St0RM53/EthernetMonitor\n"
            "License: GNU AGPLv3\n"
            "\n"
            "This tool monitors Ethernet speed and alerts you\n"
            "if it drops below the expected value."
        )
        root.destroy()

    # Run it in a new thread to avoid blocking the tray
    threading.Thread(target=show).start()

def open_network_adapters(icon=None, item=None):
    try:
        subprocess.Popen(["control.exe", "ncpa.cpl"])
    except Exception as e:
        logging.error(f"Failed to open Network Adapters: {e}")

def open_github(icon, item):
    webbrowser.open("https://github.com/St0RM53/EthernetMonitor")

# --- Tray Menu ---

def build_menu(icon):
    config = load_config()

    interface_items = [
        item(
            interface,
            partial(change_interface, icon, interface),
            checked=lambda i, name=interface: load_config()["interface_name"] == name
        ) for interface in list_interfaces()
    ]

    interval_items = [
        item(
            label,
            partial(set_interval_and_refresh, val=secs),
            checked=lambda item, val=secs: load_config()["check_interval_seconds"] == val
        ) for label, secs in INTERVAL_OPTIONS.items()
    ]

    notification_interval_items = [
        item(
            label,
            partial(set_notification_interval_and_refresh, val=secs),
            checked=lambda item, val=secs: load_config().get("notification_interval_seconds") == val
        ) for label, secs in NOTIFICATION_INTERVAL_OPTIONS.items()
    ]

    speed_menu = Menu(*[
        item(
            f"{speed} Mbps",
            set_expected_speed,
            checked=lambda item, s=speed: load_config().get("expected_speed_mbps") == s
        ) for speed in SPEED_OPTIONS
    ])

    return Menu(
        item("Open Network Adapters (double-click)", open_network_adapters, default=True, visible=False),
        item(lambda item: f"Current: {load_config()['interface_name']}", None, enabled=False),
        item("Select Interface", Menu(*interface_items)),
        item("Expected Speed", speed_menu),
        item(lambda item: f"Expected: {load_config()['expected_speed_mbps']} Mbps", None, enabled=False),
        item(lambda item: f"Current Link Speed: {get_current_link_speed(load_config()['interface_name'])}", None, enabled=False),
        item("Check Interval", Menu(*interval_items)),
        item("Notification Interval", Menu(*notification_interval_items)),
        item("Open Config Folder", lambda i: webbrowser.open(str(CONFIG_PATH.resolve().parent))),
        item("Open Network Adapters Folder", open_network_adapters),
        item("Start with Windows", toggle_startup, checked=lambda item: load_config()["start_with_windows"]),
        item("About", show_about),
        item("GitHub Repository", open_github),
        item("Quit", quit_action)
    )

# --- Monitoring Logic ---

def monitor_loop(icon, config, icon_normal, icon_warning):
    last_state_warning = False

    while True:
        config = load_config()
        interface_name = config.get("interface_name")
        expected_speed = int(config.get("expected_speed_mbps", 1000))
        interval = config.get("check_interval_seconds", 60)

        status = classify_interface(interface_name)

        if status.state == "missing":
            notify_once_every_limited_interval(
                f"'{interface_name}' was not found. It may have been removed, disabled, "
                f"or renamed. Pick another interface from the tray menu if needed.",
                "missing"
            )
            if not last_state_warning:
                icon.icon = icon_warning
                last_state_warning = True

        elif status.state == "disabled":
            notify_once_every_limited_interval(
                f"'{interface_name}' is disabled.",
                "disabled"
            )
            if not last_state_warning:
                icon.icon = icon_warning
                last_state_warning = True

        elif status.state == "unplugged":
            notify_once_every_limited_interval(
                f"'{interface_name}' appears to be unplugged (no link detected).",
                "unplugged"
            )
            if not last_state_warning:
                icon.icon = icon_warning
                last_state_warning = True

        else:  # "up"
            if status.speed < expected_speed:
                notify_once_every_limited_interval(
                    f"{interface_name} speed is {status.speed} Mbps (expected {expected_speed} Mbps)",
                    status.speed
                )
                if not last_state_warning:
                    icon.icon = icon_warning
                    last_state_warning = True
            else:
                if last_state_warning:
                    icon.icon = icon_normal
                    last_state_warning = False

        # Refresh the tray menu so "Current Link Speed" is accurate at the
        # end of every check interval, same as before - just via the
        # lightweight update_menu() (re-renders the existing menu/lambdas)
        # instead of rebuilding the whole Menu/interface list from scratch.
        try:
            icon.update_menu()
        except Exception as e:
            logging.debug(f"Menu refresh skipped: {e}")

        time.sleep(interval)

try:
    from pystray._util import win32 as _pystray_win32
except ImportError:
    _pystray_win32 = None


def hook_right_click_menu_refresh(icon):
    """
    Makes the tray menu refresh itself the instant the user right-clicks,
    without any background polling.

    pystray's win32 backend caches the native context menu (built by
    icon.update_menu()) and only redraws it when update_menu() is called -
    it does NOT re-run the "Current Link Speed" / "Current: <iface>" /
    "checked" lambdas in build_menu() just because the menu is being shown.
    There is no public pystray API to hook "right before the menu opens",
    so this taps the internal handler pystray itself uses to detect a
    right-click (WM_NOTIFY -> WM_RBUTTONUP) and calls update_menu() a
    moment before pystray displays the popup.

    This depends on pystray's private internals (_message_handlers,
    _util.win32) and could break on a pystray update; it fails safe with a
    log warning rather than crashing the app if that happens.
    """
    if _pystray_win32 is None or not hasattr(icon, "_message_handlers"):
        logging.warning("Could not hook right-click menu refresh; pystray internals unavailable")
        return

    original_on_notify = icon._message_handlers.get(_pystray_win32.WM_NOTIFY)
    if original_on_notify is None:
        logging.warning("Could not hook right-click menu refresh; WM_NOTIFY handler not found")
        return

    def on_notify_with_refresh(wparam, lparam):
        if lparam == _pystray_win32.WM_RBUTTONUP:
            try:
                icon.update_menu()
            except Exception as e:
                logging.debug(f"Right-click menu refresh failed: {e}")
        return original_on_notify(wparam, lparam)

    icon._message_handlers[_pystray_win32.WM_NOTIFY] = on_notify_with_refresh


def start_monitoring(icon, icon_normal, icon_warning):
    config = load_config()
    if config.get("start_with_windows"):
        add_to_startup()
    else:
        remove_from_startup()

    def safe_monitor():
        try:
            monitor_loop(icon, config, icon_normal, icon_warning)
        except Exception as e:
            logging.error("Exception in monitor loop", exc_info=True)

    threading.Thread(target=safe_monitor, daemon=True).start()

# --- Single Instance Guard ---

# Kept as a module-level reference so the handle stays alive (and the lock
# held) for the process's lifetime; Windows releases it automatically on
# process exit either way.
_instance_mutex = None

def acquire_single_instance_lock():
    """
    Returns a mutex handle if this is the only running instance, or None if
    another instance already holds the lock (in which case this process
    should exit without starting the tray icon/monitor).
    """
    mutex_name = f"Global\\{APP_NAME}_SingleInstanceMutex"
    mutex = win32event.CreateMutex(None, False, mutex_name)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        return None
    return mutex

# --- Main Entry Point ---

def main():
    global _instance_mutex
    _instance_mutex = acquire_single_instance_lock()
    if _instance_mutex is None:
        logging.warning(f"{APP_NAME} is already running; exiting this instance.")
        print(f"{APP_NAME} is already running.")
        return

    config = load_config()
    try:
        icon_normal = Image.open(resource_path("icon.png")).convert("RGBA")
        icon_warning = Image.open(resource_path("icon_warning.png")).convert("RGBA")
    except Exception as e:
        logging.error(f"Error loading icon: {e}")
        return

    icon = Icon(APP_NAME, icon_normal, APP_NAME)
    icon.menu = build_menu(icon)
    hook_right_click_menu_refresh(icon)

    def after_icon_starts():
        start_monitoring(icon, icon_normal, icon_warning)

    icon.run_detached()
    after_icon_starts()

    try:
        while icon.visible:
            time.sleep(1)
    except KeyboardInterrupt:
        icon.stop()

if __name__ == "__main__":
    main()
