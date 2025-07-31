import os
import sys
import json
import time
import threading
import logging
import ctypes
import webbrowser
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

import psutil
import winshell
import win32com.client
from pystray import Icon, MenuItem as item, Menu
from winotify import Notification, audio
from PIL import Image

logging.basicConfig(
    filename="ethernet_monitor.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

print("Script started...")

APP_NAME = "EthernetMonitor"
CONFIG_PATH = Path("config.json")
CONFIG_FILE = 'config.json'

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
    script = os.path.abspath(__file__)
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(shortcut_path)
    shortcut.TargetPath = target
    shortcut.Arguments = f'"{script}"'
    shortcut.WorkingDirectory = os.path.dirname(script)
    shortcut.IconLocation = os.path.abspath("ethernet_monitor_icon.ico")
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
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f)

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

def get_current_link_speed(interface_name):
    stats = psutil.net_if_stats()
    iface = stats.get(interface_name)
    if iface and iface.speed > 0:
        return f"{iface.speed} Mbps"
    return "Unknown"

# --- Notifications ---

def notify_once_every_limited_interval(message, speed):
    global last_notification_time, last_speed
    now = datetime.now()
    config = load_config()
    interval_seconds = config.get("notification_interval_seconds", 60)

    if (last_speed != speed) or not last_notification_time or (now - last_notification_time) > timedelta(seconds=interval_seconds):
        last_notification_time = now
        last_speed = speed
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

def show_about(icon, item):
    info = (
        "Ethernet Monitor\n"
        "Version: 1.0.0-beta\n"
        "Date: 30/07/25\n"
        "Author: St0RM53\n"
        "GitHub: https://github.com/St0RM53/EthernetMonitor\n"
        "License: GNU AGPLv3\n"
        "\n"
        "This tool monitors Ethernet speed and alerts you\n"
        "if it drops below the expected value."
    )
    ctypes.windll.user32.MessageBoxW(0, info, "About Ethernet Monitor", 0x40)

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
        item(lambda item: f"Current: {load_config()['interface_name']}", None, enabled=False),
        item("Select Interface", Menu(*interface_items)),
        item("Expected Speed", speed_menu),
        item(lambda item: f"Expected: {load_config()['expected_speed_mbps']} Mbps", None, enabled=False),
        item(lambda item: f"Current Link Speed: {get_current_link_speed(load_config()['interface_name'])}", None, enabled=False),
        item("Check Interval", Menu(*interval_items)),
        item("Notification Interval", Menu(*notification_interval_items)),
        item("Open Config Folder", lambda i: webbrowser.open(str(CONFIG_PATH.resolve().parent))),
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

        stats = psutil.net_if_stats()
        if interface_name in stats:
            nic = stats[interface_name]
            if nic.isup:
                if nic.speed < expected_speed:
                    notify_once_every_limited_interval(
                        f"{interface_name} speed is {nic.speed} Mbps (expected {expected_speed} Mbps)",
                        nic.speed
                    )
                    if not last_state_warning:
                        icon.icon = icon_warning
                        last_state_warning = True
                else:
                    if last_state_warning:
                        icon.icon = icon_normal
                        last_state_warning = False

        time.sleep(interval)

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

# --- Main Entry Point ---

def main():
    config = load_config()
    try:
        icon_normal = Image.open(resource_path("icon.png")).convert("RGBA")
        icon_warning = Image.open(resource_path("icon_warning.png")).convert("RGBA")
    except Exception as e:
        logging.error(f"Error loading icon: {e}")
        return

    icon = Icon(APP_NAME, icon_normal, APP_NAME)
    icon.menu = build_menu(icon)

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
