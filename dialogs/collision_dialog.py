"""
collision_dialog.py
===================

Modal dialog shown while a mod is imported and some of its GUIDs collide
(see core/collisions.py): defined in another mod, defined more than once in
the mod itself, or reserved in the Free GUIDs list of another project. The
"Problem" column lists all reasons of a GUID.

For every colliding GUID the user decides:

* **Accept** (default) – import it anyway. The GUID is shown in red with
  "!" in the database table and this collision is not reported again.
* **Migrate** – the imported mod gets a new, free GUID instead. The
  proposed GUID is shown in the table; the caller rewrites the mod's files.
  Not possible for duplicates inside one mod (the tool cannot know which
  definition should change); such rows stay on "Accept".

The decision buttons only SET the decision of the selected rows (a status
line confirms it). "Continue Import" applies the decisions and closes the
window; "Cancel Import" (or closing the window) cancels the import of this
mod. The bottom rows are packed first, so they stay visible however small
the window is.
"""

from tkinter import ttk

import customtkinter as ctk

DECISION_ACCEPT = "accept"
DECISION_MIGRATE = "migrate"


class CollisionDialog(ctk.CTkToplevel):
    """Let the user decide per colliding GUID: accept or migrate.

    :param app:        main window (translation, parent)
    :param mod_label:  name of the imported mod / file shown in the heading
    :param collisions: list of :class:`ImportCollision`
    :param proposals:  ``{(guid, offender_mod): new_guid}`` – free GUIDs
                       reserved for a migration

    Use :meth:`show`; it blocks until the dialog is closed.
    """

    def __init__(self, app, mod_label, collisions, proposals):
        super().__init__(app)
        self.app = app
        self.collisions = collisions
        self.proposals = proposals
        #: guid -> DECISION_ACCEPT / DECISION_MIGRATE
        self.decisions = {c.guid: DECISION_ACCEPT for c in collisions}
        #: None = cancelled, otherwise a copy of ``decisions``
        self.result = None

        tr = app.tr
        self.title(tr("col_dlg_title"))
        self.geometry("1180x540")
        self.minsize(760, 380)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        ctk.CTkLabel(
            self, text=tr("col_dlg_heading").format(len(collisions), mod_label),
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w", justify="left",
        ).pack(padx=15, pady=(15, 5), fill="x")
        body = ctk.CTkLabel(self, text=tr("col_dlg_body"), anchor="w", justify="left", wraplength=1140)
        body.pack(padx=15, pady=(0, 10), fill="x")
        # Re-wrap the explanation to the window width when it is resized.
        self.bind("<Configure>", lambda e: self._rewrap(body, 300), add="+")

        # Bottom rows first (side="bottom"): when the window is too small,
        # the table shrinks instead of pushing the buttons out of view.
        # From the bottom up: Continue / Cancel, status line, decision buttons.
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", padx=15, pady=(5, 15), fill="x")
        self.lbl_status = ctk.CTkLabel(self, text="", anchor="w", justify="left")
        self.lbl_status.pack(side="bottom", padx=15, pady=(8, 0), fill="x")
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(side="bottom", padx=15, pady=(8, 0), fill="x")

        # --- Table ------------------------------------------------------
        table = ctk.CTkFrame(self)
        table.pack(padx=15, pady=0, fill="both", expand=True)
        self.tree = ttk.Treeview(
            table, columns=("guid", "comment", "problem", "offenders", "decision"),
            show="headings", selectmode="extended",
        )
        for column, key, width in (
            ("guid", "tree_guid", 100), ("comment", "tree_comment", 150),
            ("problem", "col_col_problem", 520), ("offenders", "col_col_offenders", 160),
            ("decision", "col_col_decision", 150),
        ):
            self.tree.heading(column, text=tr(key), anchor="w")
            self.tree.column(column, width=width, minwidth=80, anchor="w")
        self.tree.tag_configure(DECISION_MIGRATE, foreground="#2b8a3e")
        self.tree.tag_configure(DECISION_ACCEPT, foreground="#d9534f")
        self.tree.bind("<Control-a>", self._select_all)
        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(5, 0), pady=5)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)

        for c in collisions:
            self.tree.insert("", "end", iid=c.guid, values=(
                c.guid, c.comment, self._problem_text(c), ", ".join(c.offenders), "",
            ))

        # --- Decision buttons ------------------------------------------
        # Migrating needs a proposed free GUID for every offending mod of
        # every row that can be migrated at all.
        migratable = [c for c in collisions if c.can_migrate]
        can_migrate = bool(migratable) and all(
            (c.guid, m) in proposals for c in migratable for m in c.offenders)
        ctk.CTkButton(action_row, text=tr("col_btn_migrate"), fg_color="#2b8a3e", hover_color="#216a2f",
                      state="normal" if can_migrate else "disabled",
                      command=lambda: self._set_selected(DECISION_MIGRATE)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(action_row, text=tr("col_btn_accept"), fg_color="#d9534f", hover_color="#c9302c",
                      command=lambda: self._set_selected(DECISION_ACCEPT)).pack(side="left", padx=(0, 8))
        if can_migrate or not migratable:
            hint = tr("col_dlg_hint")
        else:
            hint = tr("col_dlg_no_free")
        hint_label = ctk.CTkLabel(action_row, text=hint, text_color="gray", anchor="w", justify="left")
        hint_label.pack(side="left", padx=10, fill="x", expand=True)
        self.bind("<Configure>", lambda e: self._rewrap(hint_label, 150), add="+")

        # --- Status + Continue / Cancel ---------------------------------
        ctk.CTkButton(bottom, text=tr("col_btn_cancel"), fg_color="gray40", hover_color="gray30",
                      command=self._cancel).pack(side="right")
        ctk.CTkButton(bottom, text=tr("col_btn_continue"), width=200, height=36,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._continue).pack(side="right", padx=(0, 8))
        self._flash_job = None

        self._refresh_decisions()

        # Modal: grab the input once the window is visible.
        self.after(100, self._grab)

    @staticmethod
    def _rewrap(label, minimum):
        """Wrap ``label`` at its current width (only if that width changed)."""
        width = max(label.winfo_width() - 10, minimum)
        if label.cget("wraplength") != width:
            label.configure(wraplength=width)

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass  # window already closed

    # ------------------------------------------------------------------
    def _problem_text(self, c):
        """All reasons of a collision, e.g. "also in [Mod] v1 · defined 2× in this mod"."""
        tr = self.app.tr
        parts = []
        if c.owner_mods:
            parts.append(tr("col_reason_mods").format(", ".join(c.owner_mods)))
        for files in c.duplicates.values():
            names = sorted({f.rsplit("/", 1)[-1] for f in files})
            parts.append(tr("col_reason_duplicate").format(len(files), ", ".join(names)))
        if c.reserved_in:
            text = tr("col_reason_reserved").format(", ".join(c.reserved_in))
            if c.own_list:
                text += " " + tr("col_reason_own_list").format(c.own_list)
            parts.append(text)
        return "  ·  ".join(parts)

    def _decision_text(self, collision):
        """Text of the decision column: "Accept (!)" or "→ new GUID (mod)"."""
        if self.decisions[collision.guid] == DECISION_ACCEPT:
            return self.app.tr("col_dec_accept")
        targets = [self.proposals[(collision.guid, mod)] for mod in collision.offenders]
        if len(targets) == 1:
            return f"→ {targets[0]}"
        return ", ".join(f"→ {new} ({mod})" for new, mod in zip(targets, collision.offenders))

    def _refresh_decisions(self):
        """Update the decision column and the status line below the table."""
        for c in self.collisions:
            self.tree.set(c.guid, "decision", self._decision_text(c))
            self.tree.item(c.guid, tags=(self.decisions[c.guid],))
        decisions = list(self.decisions.values())
        self.lbl_status.configure(text=self.app.tr("col_dlg_status").format(
            decisions.count(DECISION_ACCEPT), decisions.count(DECISION_MIGRATE)))

    def _flash_status(self):
        """Highlight the status line briefly, so a click visibly did something
        (even if the decision did not change)."""
        if self._flash_job:
            self.after_cancel(self._flash_job)
        self.lbl_status.configure(text_color=("#2b8a3e", "#6fbf73"),
                                  font=ctk.CTkFont(weight="bold"))
        self._flash_job = self.after(1500, lambda: self.lbl_status.configure(
            text_color=("gray10", "gray90"), font=ctk.CTkFont(weight="normal")))

    def _set_selected(self, decision):
        """Apply ``decision`` to the selected rows (all rows if none is selected).

        Rows that cannot be migrated (duplicates) keep "Accept".
        """
        guids = self.tree.selection() or self.tree.get_children()
        by_guid = {c.guid: c for c in self.collisions}
        for guid in guids:
            if decision == DECISION_MIGRATE and not by_guid[guid].can_migrate:
                continue
            self.decisions[guid] = decision
        self._refresh_decisions()
        self._flash_status()

    def _select_all(self, event=None):
        self.tree.selection_set(self.tree.get_children())
        return "break"

    def _continue(self):
        self.result = dict(self.decisions)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def show(self):
        """Block until the dialog is closed; return the decisions or None."""
        self.wait_window()
        return self.result
