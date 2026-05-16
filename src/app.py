import time
import subprocess
import threading
import sys
import io
import os
import shutil
import urllib.request
from PIL import Image
from pypresence import Presence
import pystray
import customtkinter as ctk

# --- 設定項目 ---
PROCESS_NAME = "BlueArchive.exe"
CLIENT_ID = '1496482810007912479'
ICON_URL = "https://get.rec877.com/get/barpc/halo.ico"

# 監視間隔
IDLE_INTERVAL = 2
ACTIVE_INTERVAL = 5

# パス設定
SAVE_DIR = r"C:\rec877dev\BARPC\halos"
ICON_PATH = os.path.join(SAVE_DIR, "halo.ico")
EXE_SOURCE_PATH = r"C:\rec877dev\BARPC\barpc.exe"
STARTUP_FOLDER = os.path.join(os.getenv('APPDATA'), r"Microsoft\Windows\Start Menu\Programs\Startup")
STARTUP_EXE_PATH = os.path.join(STARTUP_FOLDER, "barpc.exe")

def ensure_icon_exists():
    if not os.path.exists(SAVE_DIR):
        try:
            os.makedirs(SAVE_DIR)
        except: pass

    if not os.path.exists(ICON_PATH):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(ICON_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(ICON_PATH, "wb") as f:
                    f.write(response.read())
        except:
            return Image.new('RGBA', (64, 64), color=(0, 162, 232, 255))

    try:
        return Image.open(ICON_PATH).convert("RGBA")
    except:
        return Image.new('RGBA', (64, 64), color=(0, 162, 232, 255))

class BlueArchiveRPC:
    def __init__(self):
        self.rpc = None
        self.is_connected = False
        self.running = True
        self.rpc_enabled = True

    def is_process_running(self):
        try:
            output = subprocess.check_output(f'tasklist /nh /fi "IMAGENAME eq {PROCESS_NAME}"', 
                                             shell=True, text=True, errors='ignore')
            return PROCESS_NAME.lower() in output.lower()
        except:
            return False

    def monitor_loop(self):
        while self.running:
            if not self.rpc_enabled:
                if self.is_connected: self.disconnect_rpc()
                time.sleep(1)
                continue

            is_active = self.is_process_running()

            if is_active and not self.is_connected:
                self.connect_rpc()
                current_sleep = ACTIVE_INTERVAL
            elif not is_active and self.is_connected:
                self.disconnect_rpc()
                current_sleep = IDLE_INTERVAL
            else:
                current_sleep = ACTIVE_INTERVAL if is_active else IDLE_INTERVAL

            time.sleep(current_sleep)

    def connect_rpc(self):
        for pipe in range(10):
            try:
                self.rpc = Presence(CLIENT_ID, pipe=pipe)
                self.rpc.connect()
                self.rpc.update(
                    large_image="bluearchive",
                    large_text="BlueArchive",
                    small_image="bluearchive",
                    start=int(time.time()),
                    buttons=[
                        {"label": "Download Client", "url": "https://bluearchive.jp"},
                        {"label": "Download RPC", "url": "https://github.com/Banana-Niku87729/Get_Rec877Pages/releases/download/barpc-1.0.1/bluearchive-rpc-setup.exe"}
                    ]
                )
                self.is_connected = True
                return
            except: continue

    def disconnect_rpc(self):
        try:
            if self.rpc:
                self.rpc.clear()
                self.rpc.close()
        except: pass
        self.rpc = None
        self.is_connected = False

    def stop(self):
        self.running = False
        self.disconnect_rpc()

class ControlPanel(ctk.CTk):
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.geometry("400x350")
        self.title("BlueArchive RPC")
        self.after(200, self.set_window_icon)

        # RPCスイッチ
        self.rpc_switch_var = ctk.IntVar(value=1)
        ctk.CTkLabel(self, text="BlueArchive RPC", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        self.rpc_switch = ctk.CTkSwitch(self, text="Discord RPCを有効にする", variable=self.rpc_switch_var, command=self.sync_settings)
        self.rpc_switch.pack(pady=10)

        # スタートアップスイッチ
        initial_startup = 1 if os.path.exists(STARTUP_EXE_PATH) else 0
        self.startup_var = ctk.IntVar(value=initial_startup)
        self.startup_switch = ctk.CTkSwitch(self, text="Windows起動時に実行する", variable=self.startup_var, command=self.toggle_startup)
        self.startup_switch.pack(pady=10)

        ctk.CTkLabel(self, text="※閉じてもトレイで監視を続けます", font=ctk.CTkFont(size=12)).pack(pady=20)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

    def set_window_icon(self):
        if os.path.exists(ICON_PATH):
            try: self.iconbitmap(ICON_PATH)
            except: pass

    def sync_settings(self):
        self.backend.rpc_enabled = self.rpc_switch_var.get() == 1

    def toggle_startup(self):
        if self.startup_var.get() == 1:
            try:
                if os.path.exists(EXE_SOURCE_PATH):
                    shutil.copy2(EXE_SOURCE_PATH, STARTUP_EXE_PATH)
                    print("スタートアップに登録しました。")
                else:
                    print(f"エラー: 元のファイルが見つかりません: {EXE_SOURCE_PATH}")
                    self.startup_var.set(0)
            except Exception as e:
                print(f"登録失敗: {e}")
                self.startup_var.set(0)
        else:
            try:
                if os.path.exists(STARTUP_EXE_PATH):
                    os.remove(STARTUP_EXE_PATH)
                    print("スタートアップから解除しました。")
            except Exception as e:
                print(f"解除失敗: {e}")
                self.startup_var.set(1)

def main():
    backend = BlueArchiveRPC()
    icon_image = ensure_icon_exists()

    threading.Thread(target=backend.monitor_loop, daemon=True).start()

    gui = ControlPanel(backend)
    
    # 【重要】起動時にウィンドウを表示しない
    gui.withdraw()

    def on_quit(icon, item):
        backend.stop()
        icon.stop()
        gui.quit()
        gui.destroy()

    menu = pystray.Menu(
        pystray.MenuItem("設定を開く", lambda: gui.deiconify()),
        pystray.MenuItem("終了", on_quit)
    )
    
    icon = pystray.Icon("BARPC", icon_image, "BlueArchive RPC", menu)
    threading.Thread(target=icon.run, daemon=True).start()

    gui.mainloop()

if __name__ == "__main__":
    main()