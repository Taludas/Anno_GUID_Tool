"""
file_drop.py
============

Drag & drop of files / folders from the Windows Explorer into a window.

Tkinter has no built-in drag & drop support, and the usual add-on
``tkinterdnd2`` needs bundled Tcl extensions (and fails to import on newer
Python versions). This module uses the native Win32 mechanism instead,
via :mod:`ctypes` only:

1. ``DragAcceptFiles(hwnd)`` marks the window as a drop target, so the
   Explorer sends ``WM_DROPFILES`` to it. Drops on any child widget are
   delivered to that window as well.
2. ``SetWindowSubclass`` installs a small window procedure that handles
   ``WM_DROPFILES``, reads the dropped paths with ``DragQueryFileW`` and
   passes them to a Python callback. All other messages go to the original
   window procedure unchanged.

On other platforms :func:`enable_file_drop` does nothing and returns False.

No Tkinter import here: the caller passes the native window handle, e.g.
``int(root.wm_frame(), 16)``.

IMPORTANT: the callback is called from inside the window procedure, i.e. in
the middle of Tk's own event processing. It must NOT call any Tkinter method
(not even ``after()``) - re-entering ``_tkinter`` there crashes Python with
"PyEval_RestoreThread: ... GIL is released". Pass the paths on through a
``queue.Queue`` and let the UI thread poll it instead.
"""

import sys

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    WM_DROPFILES = 0x0233
    WM_COPYDATA = 0x004A
    WM_COPYGLOBALDATA = 0x0049
    MSGFLT_ALLOW = 1

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    _comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)

    LRESULT = ctypes.c_ssize_t
    SUBCLASSPROC = ctypes.WINFUNCTYPE(
        LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
        ctypes.c_size_t, ctypes.c_size_t,
    )

    _shell32.DragAcceptFiles.argtypes = (wintypes.HWND, wintypes.BOOL)
    _shell32.DragAcceptFiles.restype = None
    _shell32.DragQueryFileW.argtypes = (wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT)
    _shell32.DragQueryFileW.restype = wintypes.UINT
    _shell32.DragFinish.argtypes = (wintypes.HANDLE,)
    _shell32.DragFinish.restype = None

    _comctl32.SetWindowSubclass.argtypes = (wintypes.HWND, SUBCLASSPROC, ctypes.c_size_t, ctypes.c_size_t)
    _comctl32.SetWindowSubclass.restype = wintypes.BOOL
    _comctl32.DefSubclassProc.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    _comctl32.DefSubclassProc.restype = LRESULT

    _user32.ChangeWindowMessageFilterEx.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.DWORD, ctypes.c_void_p)
    _user32.ChangeWindowMessageFilterEx.restype = wintypes.BOOL

#: Window procedures that are still installed. ctypes callbacks must stay
#: referenced, otherwise they are garbage-collected and Windows would call
#: freed memory on the next message.
_installed = {}


def _query_paths(hdrop):
    """Return the list of file / folder paths stored in a ``HDROP`` handle."""
    count = _shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
    paths = []
    for index in range(count):
        length = _shell32.DragQueryFileW(hdrop, index, None, 0)
        buffer = ctypes.create_unicode_buffer(length + 1)
        _shell32.DragQueryFileW(hdrop, index, buffer, length + 1)
        paths.append(buffer.value)
    return paths


def enable_file_drop(hwnd, callback):
    """Let the window ``hwnd`` accept files / folders dropped from the Explorer.

    :param hwnd:     native handle of the top-level window
    :param callback: called with the list of dropped paths (absolute,
                     Windows separators) for every drop
    :return: True if drag & drop is active, False if not supported
             (non-Windows platform or a Win32 call failed)
    """
    if sys.platform != "win32" or hwnd in _installed:
        return hwnd in _installed

    def window_proc(h, msg, wparam, lparam, _subclass_id, _ref_data):
        if msg == WM_DROPFILES:
            try:
                paths = _query_paths(wparam)
            finally:
                _shell32.DragFinish(wparam)
            try:
                callback(paths)
            except Exception as e:  # never let an exception escape into Windows
                print(f"Error handling dropped files: {e}")
            return 0
        return _comctl32.DefSubclassProc(h, msg, wparam, lparam)

    proc = SUBCLASSPROC(window_proc)
    if not _comctl32.SetWindowSubclass(hwnd, proc, 1, 0):
        return False
    _installed[hwnd] = proc

    # If the tool runs as administrator, Windows blocks drag & drop messages
    # coming from the (non-elevated) Explorer unless they are allowed here.
    for msg in (WM_DROPFILES, WM_COPYDATA, WM_COPYGLOBALDATA):
        _user32.ChangeWindowMessageFilterEx(hwnd, msg, MSGFLT_ALLOW, None)

    _shell32.DragAcceptFiles(hwnd, True)
    return True
