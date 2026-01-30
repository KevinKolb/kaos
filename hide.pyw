import sys
import subprocess

def check_and_install_dependencies():
    """Check for required packages and install if missing"""
    packages = {
        'pystray': 'pystray',
        'PIL': 'Pillow',
        'pyautogui': 'pyautogui'
    }
    
    missing = []
    for module, package in packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("Packages installed successfully!")
            return True
        except subprocess.CalledProcessError:
            print(f"Failed to install packages. Please install manually with: pip install {' '.join(missing)}")
            return False
    else:
        print("All dependencies OK")
        return True

if not check_and_install_dependencies():
    sys.exit(1)

import ctypes
from ctypes import wintypes
import pystray
from PIL import Image, ImageDraw
import threading
import time
import os
import tempfile
import pyautogui

user32 = ctypes.windll.user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_K = 0x4B

# All Windows cursor types
CURSOR_TYPES = [
    32512,  # IDC_ARROW
    32513,  # IDC_IBEAM
    32514,  # IDC_WAIT
    32515,  # IDC_CROSS
    32516,  # IDC_UPARROW
    32640,  # IDC_SIZE (obsolete)
    32641,  # IDC_ICON (obsolete)
    32642,  # IDC_SIZENWSE
    32643,  # IDC_SIZENESW
    32644,  # IDC_SIZEWE
    32645,  # IDC_SIZENS
    32646,  # IDC_SIZEALL
    32648,  # IDC_NO
    32649,  # IDC_HAND
    32650,  # IDC_APPSTARTING
    32651,  # IDC_HELP
]

class MouseHider:
    def __init__(self):
        self.hidden = False
        self.icon = None
        self.running = True
        self.blank_cursor = None
        self.monitor_thread = None
        self.mouse_move_thread = None
        
    def create_blank_cursor(self):
        """Create a blank cursor that works with large cursors"""
        # Create a large transparent cursor (128x128 to handle extra large cursors)
        img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        
        # Save as .cur file in temp directory
        temp_dir = tempfile.gettempdir()
        cursor_path = os.path.join(temp_dir, 'blank_cursor.cur')
        
        # Save as ICO (Windows treats .cur and .ico similarly)
        ico_path = cursor_path.replace('.cur', '.ico')
        img.save(ico_path, format='ICO')
        
        return ico_path
    
    def load_blank_cursor(self):
        """Load the blank cursor"""
        if not self.blank_cursor:
            cursor_path = self.create_blank_cursor()
            # Load cursor from file
            LR_LOADFROMFILE = 0x00000010
            IMAGE_CURSOR = 2
            self.blank_cursor = user32.LoadImageW(
                0,
                cursor_path,
                IMAGE_CURSOR,
                0,
                0,
                LR_LOADFROMFILE
            )
            print(f"Blank cursor handle: {self.blank_cursor}")
        return self.blank_cursor
    
    def monitor_and_hide(self):
        """Continuously replace ALL cursor types with blank"""
        blank = self.load_blank_cursor()
        while self.hidden and self.running:
            if blank:
                # Replace ALL system cursor types
                for cursor_type in CURSOR_TYPES:
                    try:
                        user32.SetSystemCursor(user32.CopyIcon(blank), cursor_type)
                    except:
                        pass
                user32.SetCursor(blank)
            time.sleep(0.1)
    
    def move_mouse_periodically(self):
        """Move mouse every 3 minutes"""
        while self.running:
            try:
                # Get current mouse position
                current_x, current_y = pyautogui.position()
                
                # Move by 5 pixels, then back to original position
                pyautogui.moveTo(current_x + 5, current_y)
                time.sleep(0.1)
                pyautogui.moveTo(current_x, current_y)
                
                # Wait 3 minutes before next movement
                time.sleep(180)
            except Exception as e:
                print(f"Error moving mouse: {e}")
                time.sleep(180)
    
    def hide_cursor(self):
        if not self.hidden:
            self.hidden = True
            
            blank = self.load_blank_cursor()
            if blank:
                # Replace ALL system cursors with blank cursor
                for cursor_type in CURSOR_TYPES:
                    try:
                        user32.SetSystemCursor(user32.CopyIcon(blank), cursor_type)
                    except Exception as e:
                        print(f"Failed to set cursor type {cursor_type}: {e}")
                
                user32.SetCursor(blank)
                print("All cursor types set to blank")
            else:
                print("Failed to load blank cursor")
            
            # Start monitoring thread to keep all cursors blank
            self.monitor_thread = threading.Thread(target=self.monitor_and_hide, daemon=True)
            self.monitor_thread.start()
            
            self.update_icon_title()
            print(">>> MOUSE CURSOR HIDDEN <<<")
    
    def show_cursor(self):
        if self.hidden:
            self.hidden = False
            
            # Restore ALL system cursors to default
            user32.SystemParametersInfoW(0x0057, 0, None, 0)  # SPI_SETCURSORS
            
            # Force refresh
            time.sleep(0.1)
            hCursor = user32.LoadCursorW(0, 32512)  # IDC_ARROW
            user32.SetCursor(hCursor)
            
            self.update_icon_title()
            print(">>> MOUSE CURSOR VISIBLE <<<")
    
    def toggle_cursor(self):
        if self.hidden:
            self.show_cursor()
        else:
            self.hide_cursor()
    
    def update_icon_title(self):
        if self.icon:
            status = "Hidden" if self.hidden else "Visible"
            self.icon.title = f"Mouse Hider - Cursor: {status}\nCtrl+Alt+K to toggle"
    
    def create_icon_image(self):
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        draw.polygon([(10, 10), (10, 50), (25, 35), (35, 50), (40, 45), (30, 30), (45, 30)], 
                     fill='black', outline='black')
        return image
    
    def quit_app(self, icon, item):
        print("Quitting...")
        self.running = False
        if self.hidden:
            self.show_cursor()
        user32.UnregisterHotKey(None, 1)
        icon.stop()
        sys.exit(0)
    
    def on_toggle_from_menu(self, icon, item):
        self.toggle_cursor()
    
    def setup_tray_icon(self):
        icon_image = self.create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Toggle Cursor (Ctrl+Alt+K)", self.on_toggle_from_menu),
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.icon = pystray.Icon("mouse_hider", icon_image, 
                                 "Mouse Hider - Cursor: Visible\nCtrl+Alt+K to toggle", 
                                 menu)
        icon_thread = threading.Thread(target=self.icon.run, daemon=True)
        icon_thread.start()
        
        # Start the mouse movement thread
        self.mouse_move_thread = threading.Thread(target=self.move_mouse_periodically, daemon=True)
        self.mouse_move_thread.start()

def main():
    hider = MouseHider()
    hider.setup_tray_icon()
    
    print("Mouse Hide Toggle running in system tray")
    print("Press CTRL+ALT+K to toggle cursor visibility")
    print("Mouse will move every 3 minutes to prevent system sleep")
    print("Right-click tray icon to quit")
    print("\nNOTE: If you have custom/large cursors enabled, this will replace them temporarily.")
    
    if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT, VK_K):
        print("Failed to register hotkey!")
        return
    
    print("Hotkey registered successfully!")
    
    try:
        msg = wintypes.MSG()
        while hider.running:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0 or result == -1:
                break
            if msg.message == 0x0312:  # WM_HOTKEY
                hider.toggle_cursor()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, 1)
        if hider.hidden:
            hider.show_cursor()

if __name__ == "__main__":
    main()