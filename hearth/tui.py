#!/usr/bin/env python3
"""hearth tui -- a keyboard-driven settings browser (Textual).

A file-browser-style tree of categories with the setting leaves. Pick a leaf to see its details, edit
the value (validated against the schema, then written + signalled live). `/` searches every setting,
`.` reveals advanced ("hidden") ones, `d` resets a setting to its default.
"""
import sys
import json

from . import main as hearth

# Braille mark shown on the TUI landing screen. Kept in sync with ../logo.txt via .logo-gen.py.
HEARTH_LOGO = """
⠀⢠⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⣤⡄⠀
⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠇⠀
⠀⠀⢸⣿⣿⣿⣿⣿⡿⠿⠿⠿⠿⢿⣿⣿⣿⣿⣿⡇⠀⠀
⠀⠀⢸⣿⣿⣿⡿⠃⠀⠀⠀⠀⠀⠀⠘⢿⣿⣿⣿⡇⠀⠀
⠀⠀⢸⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣿⡇⠀⠀
⠀⠀⢸⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⡇⠀⠀
⠀⠀⢸⣿⣿⣿⠀⠀⠀⠀⣴⣧⠀⠀⠀⠀⣿⣿⣿⡇⠀⠀
⠀⠀⢸⣿⣿⣿⠀⠀⣠⢠⣿⣿⡆⣦⡀⠀⣿⣿⣿⡇⠀⠀
⠀⠀⢸⣿⣿⣿⠀⣸⣿⣾⣿⣿⣷⣿⣇⠀⣿⣿⣿⡇⠀⠀
⠀⠀⢸⣿⣿⣿⠀⣿⣿⣿⣿⣿⣿⣿⣿⠀⣿⣿⣿⡇⠀⠀
⢀⣀⣸⣿⣿⣿⣀⣿⣿⣿⣿⣿⣿⣿⣿⣀⣿⣿⣿⣇⣀⡀
⠸⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠇
"""


def _fmt(v):
    if isinstance(v, bool):
        return "on" if v else "off"
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    return "" if v is None else str(v)


def run(argv=None):
    argv = argv or []
    try:
        from textual.app import App
        from textual.binding import Binding
        from textual.containers import Horizontal, Vertical
        from textual.widgets import Tree, Input, Static, Footer
    except ImportError:
        sys.stderr.write("hearth tui: textual is not installed\n")
        return 1

    class HearthApp(App):
        CSS = """
        #left   { width: 46%; }
        #search { margin: 0 1; }
        #detail { width: 1fr; padding: 1 2; }
        #ed     { margin-top: 1; display: none; }
        #msg    { margin-top: 1; color: $text-muted; }
        """
        BINDINGS = [
            Binding("slash", "search", "Search"),
            Binding("full_stop", "advanced", "Advanced"),
            Binding("d", "reset", "Reset"),
            Binding("escape", "to_tree", "Back"),
            Binding("q", "quit", "Quit"),
        ]

        def __init__(self):
            super().__init__()
            self.schema = hearth._schema()
            self.advanced = False
            self.filter = ""
            self.key = None

        def compose(self):
            with Horizontal():
                with Vertical(id="left"):
                    yield Input(placeholder="/ to search", id="search")
                    yield Tree("bonfire \U0001f525", id="tree")
                with Vertical(id="detail"):
                    yield Static("", id="info")
                    yield Input(id="ed")
                    yield Static("", id="msg")
            yield Footer()

        def on_mount(self):
            self.title = "hearth settings"
            self._build()
            self._home()

        # ---- landing screen: the hearth mark + a hint ----
        def _banner(self):
            fire = ["#f6c453", "#f4a833", "#ef8d2f", "#e5702a", "#d8542a",
                    "#e5702a", "#ef8d2f", "#f4a833", "#f6c453", "#ef8d2f", "#e5702a", "#d8542a"]
            rows = HEARTH_LOGO.strip("\n").split("\n")
            out = [f"[{fire[i % len(fire)]}]{r}[/]" for i, r in enumerate(rows)]
            out += ["", "[b]hearth[/b] [dim]— unified settings[/dim]",
                    "[dim]pick a setting from the tree to view or change it.[/dim]"]
            return "\n".join(out)

        def _home(self):
            self.key = None
            self.query_one("#info", Static).update(self._banner())
            ed = self.query_one("#ed", Input)
            ed.value = ""
            ed.styles.display = "none"
            self.query_one("#msg", Static).update(
                "[dim]↑↓ navigate · ⏎ select · / search · . advanced · q quit[/dim]")

        # ---- build the category tree from the dotted keys ----
        def _build(self):
            tree = self.query_one("#tree", Tree)
            tree.clear()
            eff = hearth._effective()
            cats = {}
            flt = self.filter.lower()
            for k in sorted(self.schema):
                ent = self.schema[k]
                if ent.get("tier") == "advanced" and not self.advanced:
                    continue
                if flt and flt not in k.lower() and flt not in str(ent.get("label", "")).lower():
                    continue
                parts = k.split(".")
                parent, pref = tree.root, ""
                for seg in parts[:-1]:
                    pref = f"{pref}.{seg}" if pref else seg
                    if pref not in cats:
                        cats[pref] = parent.add(seg, expand=True)
                    parent = cats[pref]
                badge = "" if ent.get("scope", "runtime") == "runtime" else "  ⚙"
                parent.add_leaf(f"{ent.get('label', parts[-1])} = {_fmt(eff.get(k))}{badge}", data=k)
            tree.root.expand()

        # ---- selecting a leaf shows its detail + opens the editor ----
        def on_tree_node_selected(self, event):
            key = event.node.data
            if key:
                self.key = key
                self._show(key)

        def _show(self, key):
            ent = self.schema.get(key, {})
            val = hearth._effective().get(key)
            c = ent.get("constraints", {}) or {}
            lines = [
                f"[b]{ent.get('label', key)}[/b]",
                f"[dim]{key}[/dim]",
                "",
                ent.get("help", ""),
                "",
                f"type:    {ent.get('type')}",
                f"value:   {_fmt(val)}",
                f"default: {_fmt(ent.get('default'))}",
                f"scope:   {ent.get('scope', 'runtime')}"
                + ("   [yellow]needs rebuild[/yellow]" if ent.get("scope") == "build" else ""),
            ]
            opts = c.get("options")
            if opts:
                lines.append("options: " + ", ".join(str(o.get("value", o) if isinstance(o, dict) else o) for o in opts))
            if "min" in c or "max" in c:
                lines.append(f"range:   {c.get('min', '')}..{c.get('max', '')} {c.get('unit', '')}".rstrip())
            self.query_one("#info", Static).update("\n".join(l for l in lines if l is not None))
            ed = self.query_one("#ed", Input)
            ed.value = _fmt(val)
            ed.styles.display = "block"
            self.query_one("#msg", Static).update("[dim]⏎ apply · d reset · . advanced · / search[/dim]")
            self.set_focus(ed)

        # ---- edits + search ----
        def on_input_submitted(self, event):
            if event.input.id != "ed" or not self.key:
                return
            ok, res = hearth.set_value(self.key, event.value)
            msg = self.query_one("#msg", Static)
            if ok:
                msg.update(f"[green]set {self.key} = {_fmt(res)}[/green]")
                self._build()
                self._show(self.key)
            else:
                msg.update(f"[red]{res}[/red]")

        def on_input_changed(self, event):
            if event.input.id == "search":
                self.filter = event.value
                self._build()

        def action_search(self):
            self.set_focus(self.query_one("#search", Input))

        def action_advanced(self):
            self.advanced = not self.advanced
            self._build()
            self.query_one("#msg", Static).update(
                f"[dim]advanced {'shown' if self.advanced else 'hidden'}[/dim]")

        def action_reset(self):
            if self.key:
                hearth.reset_value(self.key)
                self._build()
                self._show(self.key)
                self.query_one("#msg", Static).update(f"[yellow]reset {self.key}[/yellow]")

        def action_to_tree(self):
            self.set_focus(self.query_one("#tree", Tree))
            self._home()                               # Escape returns to the landing screen

    if "--selftest" in argv:                       # headless construction/mount check (no TTY needed)
        import asyncio

        async def _t():
            app = HearthApp()
            async with app.run_test():
                pass

        asyncio.run(_t())
        print("hearth tui selftest OK")
        return 0

    HearthApp().run()
    return 0
