"""Иконка и кнопка панели задач для окна Tk без стандартной рамки."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path

def identity():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('RG.JARVIS.Assistant')

def taskbar(root):
    root.update_idletasks()
    user32=ctypes.windll.user32
    user32.GetParent.argtypes=[wintypes.HWND];user32.GetParent.restype=wintypes.HWND
    hwnd=user32.GetParent(root.winfo_id()) or root.winfo_id()
    get=getattr(user32,'GetWindowLongPtrW',user32.GetWindowLongW)
    set_=getattr(user32,'SetWindowLongPtrW',user32.SetWindowLongW)
    get.argtypes=[wintypes.HWND,ctypes.c_int];get.restype=ctypes.c_ssize_t
    set_.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t];set_.restype=ctypes.c_ssize_t
    style=get(hwnd,-20)
    set_(hwnd,-20,(style & ~0x80) | 0x40000) # APPWINDOW вместо TOOLWINDOW
    user32.SetWindowPos.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
    user32.SetWindowPos(hwnd,None,0,0,0,0,0x37) # FRAMECHANGED, без перемещения/активации
    icon=Path(os.environ.get('LOCALAPPDATA',''))/'JARVISASSISTENT'/'JARVIS.ico'
    if icon.exists():root.iconbitmap(default=str(icon))
    return get(hwnd,-20)
