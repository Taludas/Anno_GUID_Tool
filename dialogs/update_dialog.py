"""
update_dialog.py
================

Popup window shown when a newer version is available on GitHub.

Content:
  * title and hint text with the installed and the new version
  * clickable link to the GitHub project page (opens the default browser)
  * "OK" button (also closed with Enter / Escape)

The window is modal (grab_set) and centered over the main window.
"""

import webbrowser

import customtkinter as ctk

from core.update_checker import GITHUB_REPO_URL


class UpdateDialog(ctk.CTkToplevel):
    """Modal "update available" popup.

    :param app:            the main :class:`GUIDManagerApp` (parent + ``tr``)
    :param local_version:  installed version, e.g. "v1.23.45"
    :param remote_version: version found on GitHub, e.g. "v1.24.0"
    """

    def __init__(self, app, local_version, remote_version):
        super().__init__(app)
        tr = app.tr
        self.title(tr("update_title"))
        self.resizable(False, False)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(padx=25, pady=20)

        ctk.CTkLabel(
            frame, text=tr("update_heading"), font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(
            frame, justify="left",
            text=tr("update_body").format(local_version, remote_version),
        ).pack(anchor="w")

        # Clickable link: blue, underlined, hand cursor.
        link = ctk.CTkLabel(
            frame, text=GITHUB_REPO_URL, cursor="hand2",
            text_color=("#1a5fb4", "#62a0ea"),
            font=ctk.CTkFont(underline=True),
        )
        link.pack(anchor="w", pady=(8, 15))
        link.bind("<Button-1>", lambda e: webbrowser.open(GITHUB_REPO_URL))

        btn_ok = ctk.CTkButton(frame, text="OK", width=100, command=self.destroy)
        btn_ok.pack(anchor="e")

        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())

        # Modal + centered over the main window. CTkToplevel needs a short
        # delay before grab/focus work reliably on Windows.
        self.transient(app)
        self.after(50, lambda: self._center_and_focus(app, btn_ok))

    def _center_and_focus(self, app, button):
        """Center the popup over ``app``, bring it to front and make it modal."""
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + (app.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.lift()
        self.grab_set()
        button.focus_set()
