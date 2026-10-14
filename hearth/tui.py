#!/usr/bin/env python3
"""hearth tui -- a keyboard-driven settings browser (Textual).

Three panes that scale to a large settings surface: CATEGORIES (the top-level groups) | the SETTINGS in
that category with their live values | DETAIL + an inline editor for the focused setting. `/` searches
every setting across categories, `.` reveals advanced ("hidden") ones, `d` resets to default, Esc goes
home. Edits validate against the schema, then write + signal live.
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
        from textual.widgets import OptionList, Input, Static, Footer
        from textual.widgets.option_list import Option
    except ImportError:
        sys.stderr.write("hearth tui: textual is not installed\n")
        return 1

    class HearthApp(App):
        CSS = """
        Screen { layout: horizontal; }
        #cats   { width: 18; border-right: solid $primary; }
        #mid    { width: 44%; border-right: solid $primary; }
        #detail { width: 1fr; padding: 0 1; }
        .hdr    { color: $accent; text-style: bold; padding: 0 1; }
        #search { margin: 0 1 1 1; }
        OptionList { height: 1fr; }
        #ed     { margin: 1 0; }
        #msg    { color: $text-muted; }
        """
        BINDINGS = [
            Binding("slash", "search", "Search"),
            Binding("full_stop", "advanced", "Advanced"),
            Binding("d", "reset", "Reset"),
            Binding("escape", "back", "Home"),
            Binding("q", "quit", "Quit"),
        ]

        def __init__(self):
            super().__init__()
            self.schema = hearth._schema()
            self.advanced = False
            self.filter = ""
            self.category = None
            self.key = None

        def compose(self):
            with Horizontal():
                with Vertical(id="cats"):
                    yield Static(" categories", classes="hdr")
                    yield OptionList(id="catlist")
                with Vertical(id="mid"):
                    yield Input(placeholder="/ search all settings", id="search")
                    yield OptionList(id="setlist")
                with Vertical(id="detail"):
                    yield Static("", id="info")
                    yield Input(id="ed")
                    yield Static("", id="msg")
            yield Footer()

        def on_mount(self):
            self.title = "hearth settings"
            self._build_cats()
            self._home()

        # ---- data ----
        def _cats(self):
            return sorted({k.split(".", 1)[0] for k in self.schema})

        def _settings(self):
            eff = hearth._effective()
            flt = self.filter.lower()
            out = []
            for k in sorted(self.schema):
                ent = self.schema[k]
                if ent.get("tier") == "advanced" and not self.advanced:
                    continue
                if flt:
                    if flt not in k.lower() and flt not in str(ent.get("label", "")).lower():
                        continue
                elif self.category and k.split(".", 1)[0] != self.category:
                    continue
                out.append(k)
            return out, eff

        # ---- build ----
        def _build_cats(self):
            ol = self.query_one("#catlist", OptionList)
            ol.clear_options()
            cats = self._cats()
            for c in cats:
                ol.add_option(Option(c, id=c))
            if cats and self.category is None:
                self.category = cats[0]
            self._build_settings()

        def _build_settings(self):
            ol = self.query_one("#setlist", OptionList)
            ol.clear_options()
            keys, eff = self._settings()
            for k in keys:
                ent = self.schema[k]
                if not self.filter and self.category and k.startswith(self.category + "."):
                    name = k[len(self.category) + 1:]
                else:
                    name = k
                badge = "" if ent.get("scope", "runtime") == "runtime" else "  ⚙"
                ol.add_option(Option(f"{ent.get('label', name)} = {_fmt(eff.get(k))}{badge}", id=k))
            if not keys:
                ol.add_option(Option("[dim](no settings)[/dim]", id=None, disabled=True))

        # ---- events ----
        def on_option_list_option_highlighted(self, event):
            oid = event.option_list.id
            if oid == "catlist" and event.option is not None:
                self.category = event.option.id
                self.filter = ""
                self.query_one("#search", Input).value = ""
                self._build_settings()
            elif oid == "setlist" and event.option is not None and event.option.id:
                self._show(event.option.id)

        def on_option_list_option_selected(self, event):
            if event.option_list.id == "setlist" and event.option is not None and event.option.id:
                self._show(event.option.id)
                self.set_focus(self.query_one("#ed", Input))

        def _show(self, key):
            self.key = key
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
            self.query_one("#msg", Static).update(
                "[dim]⏎ on a setting: edit · ⏎ in the field: apply · d reset · . advanced · / search[/dim]")

        # ---- edits + search ----
        def on_input_submitted(self, event):
            if event.input.id == "search":
                self.filter = event.value
                self._build_settings()
                self.set_focus(self.query_one("#setlist", OptionList))
                return
            if event.input.id == "ed" and self.key:
                ok, res = hearth.set_value(self.key, event.value)
                msg = self.query_one("#msg", Static)
                if ok:
                    msg.update(f"[green]set {self.key} = {_fmt(res)}[/green]")
                    self._build_settings()
                    self._show(self.key)
                else:
                    msg.update(f"[red]{res}[/red]")

        def on_input_changed(self, event):
            if event.input.id == "search":
                self.filter = event.value
                self._build_settings()

        # ---- actions ----
        def action_search(self):
            self.set_focus(self.query_one("#search", Input))

        def action_advanced(self):
            self.advanced = not self.advanced
            self._build_settings()
            self.query_one("#msg", Static).update(
                f"[dim]advanced {'shown' if self.advanced else 'hidden'}[/dim]")

        def action_reset(self):
            if self.key:
                hearth.reset_value(self.key)
                self._build_settings()
                self._show(self.key)
                self.query_one("#msg", Static).update(f"[yellow]reset {self.key}[/yellow]")

        def action_back(self):
            self._home()
            self.set_focus(self.query_one("#catlist", OptionList))

        # ---- landing ----
        def _banner(self):
            fire = ["#f6c453", "#f4a833", "#ef8d2f", "#e5702a", "#d8542a",
                    "#e5702a", "#ef8d2f", "#f4a833", "#f6c453", "#ef8d2f", "#e5702a", "#d8542a"]
            rows = HEARTH_LOGO.strip("\n").split("\n")
            out = [f"[{fire[i % len(fire)]}]{r}[/]" for i, r in enumerate(rows)]
            out += ["", "[b]hearth[/b] [dim]— unified settings[/dim]",
                    "[dim]tab/←→ panes · ↑↓ navigate · ⏎ edit · / search · . advanced · d reset[/dim]"]
            return "\n".join(out)

        def _home(self):
            self.key = None
            self.query_one("#info", Static).update(self._banner())
            ed = self.query_one("#ed", Input)
            ed.value = ""
            ed.styles.display = "none"
            self.query_one("#msg", Static).update("")

    if "--selftest" in argv:                       # headless construction/mount check (no TTY needed)
        import asyncio

        async def _t():
            app = HearthApp()
            async with app.run_test() as pilot:
                await pilot.pause()

        asyncio.run(_t())
        print("hearth tui selftest OK")
        return 0

    HearthApp().run()
    return 0
