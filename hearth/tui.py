#!/usr/bin/env python3
"""hearth tui -- a warm, keyboard-driven settings browser (Textual).

Not a grid: one flowing, ember-lit column of settings grouped under glowing category embers, with a
"hearth" panel at the foot where you tend the selected one. `/` searches the embers, `.` reveals
advanced ones, `d` resets to default, Esc goes home. Edits validate against the schema, then write +
signal live.
"""
import sys
import json

from . import main as hearth

# Braille mark shown on the landing hearth. Kept in sync with ../logo.txt via .logo-gen.py.
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

# vertical fire gradient for the logo + section embers (top = bright gold, base = deep coal)
FIRE = ["#ffd23f", "#ffb627", "#ff9505", "#ff7518", "#f0580f",
        "#e5440f", "#ff7518", "#ff9505", "#ffb627", "#ff9505", "#e5440f", "#c23208"]

# a warm order for the top-level categories; anything else trails alphabetically
ORDER = ["bonfire", "panel", "dock", "hyprland", "keybind", "hearth"]


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
        from textual.containers import Vertical
        from textual.widgets import OptionList, Input, Static, Footer
        from textual.widgets.option_list import Option
        from rich.text import Text
    except ImportError:
        sys.stderr.write("hearth tui: textual is not installed\n")
        return 1

    class HearthApp(App):
        # Embers, not fluorescent tubes. A warm coal ground, cream text, amber flames.
        CSS = """
        Screen { background: #1a1310; color: #efe1d1; }
        #title { dock: top; height: 1; content-align: center middle; color: #ff9505; text-style: bold; }
        #search {
            dock: top; margin: 0 3 1 3; height: 3;
            background: #241a13; color: #efe1d1; border: round #a8531f;
        }
        #search:focus { border: round #ff9505; }
        OptionList {
            background: transparent; padding: 0 2; scrollbar-color: #a8531f; scrollbar-background: #1a1310;
        }
        OptionList:focus { background: transparent; }
        OptionList > .option-list--option-highlighted { background: #6b3317; color: #fff2e4; }
        OptionList:focus > .option-list--option-highlighted { background: #8f4420; color: #fff2e4; text-style: bold; }
        #hearth {
            dock: bottom; height: 15; margin: 0 3 1 3; padding: 1 2;
            background: #221811; border: round #a8531f;
        }
        #hearth:focus-within { border: round #ff9505; }
        #info { height: 1fr; }
        #ed { background: #2c2017; color: #ffe9d4; border: round #c0632e; }
        #ed:focus { border: round #ff9505; }
        #msg { color: #b89878; height: 1; }
        Footer { background: #120c09; color: #b89878; }
        Footer > .footer--key { background: #6b3317; color: #ffd23f; }
        """
        BINDINGS = [
            Binding("slash", "search", "Search"),
            Binding("full_stop", "advanced", "Advanced"),
            Binding("d", "reset", "Reset"),
            Binding("escape", "home", "Home"),
            Binding("q", "quit", "Quit"),
        ]

        def __init__(self):
            super().__init__()
            self.schema = hearth._schema()
            self.advanced = False
            self.filter = ""
            self.key = None

        def compose(self):
            yield Static("🔥  b o n f i r e   ·   s e t t i n g s", id="title")
            yield Input(placeholder="search the embers…", id="search")
            yield OptionList(id="list")
            with Vertical(id="hearth"):
                yield Static("", id="info")
                yield Input(id="ed")
                yield Static("", id="msg")
            yield Footer()

        def on_mount(self):
            self.title = "bonfire settings"
            self._build_list()
            self._home()

        # ---- data ----
        def _cats(self):
            found = {k.split(".", 1)[0] for k in self.schema}
            ordered = [c for c in ORDER if c in found]
            return ordered + sorted(found - set(ordered))

        def _visible(self, k):
            ent = self.schema[k]
            if ent.get("tier") == "advanced" and not self.advanced:
                return False
            flt = self.filter.lower()
            if flt and flt not in k.lower() and flt not in str(ent.get("label", "")).lower():
                return False
            return True

        def _row(self, k, eff, strip=None):
            ent = self.schema[k]
            name = k[len(strip) + 1:] if (strip and k.startswith(strip + ".")) else k
            val = _fmt(eff.get(k))
            t = Text("   ")
            t.append(ent.get("label", name), style="#efe1d1")
            t.append("   ")
            t.append(val if val != "" else "—", style="#e0a35f")
            if ent.get("scope", "runtime") == "build":
                t.append("  ⚙", style="#9c8268")
            return t

        # ---- build the flowing, grouped list ----
        def _build_list(self):
            ol = self.query_one("#list", OptionList)
            ol.clear_options()
            eff = hearth._effective()
            if self.filter:
                hits = [k for k in sorted(self.schema) if self._visible(k)]
                for k in hits:
                    ol.add_option(Option(self._row(k, eff), id=k))
                if not hits:
                    ol.add_option(Option(Text("   no embers match", style="#b89878"), disabled=True))
                return
            for ci, cat in enumerate(self._cats()):
                ks = [k for k in sorted(self.schema) if k.split(".", 1)[0] == cat and self._visible(k)]
                if not ks:
                    continue
                ember = Text()
                ember.append(" ✦ ", style=FIRE[ci % len(FIRE)])
                ember.append(cat, style=f"bold {FIRE[ci % len(FIRE)]}")
                ol.add_option(Option(ember, disabled=True))
                for k in ks:
                    ol.add_option(Option(self._row(k, eff, strip=cat), id=k))

        # ---- selection ----
        def on_option_list_option_highlighted(self, event):
            if event.option is not None and event.option.id:
                self._show(event.option.id)

        def on_option_list_option_selected(self, event):
            if event.option is not None and event.option.id:
                self._show(event.option.id)
                self.set_focus(self.query_one("#ed", Input))

        def _show(self, key):
            self.key = key
            ent = self.schema.get(key, {})
            val = hearth._effective().get(key)
            c = ent.get("constraints", {}) or {}
            lines = [
                f"[b #ff9505]{ent.get('label', key)}[/]   [#7a6450]{key}[/]",
                "",
                f"[#cdb79e]{ent.get('help', '')}[/]",
                "",
                f"[#9c8268]now[/]  [#e0a35f]{_fmt(val)}[/]     [#9c8268]default[/]  {_fmt(ent.get('default'))}     [#9c8268]type[/]  {ent.get('type')}"
                + ("     [yellow]↻ needs rebuild[/]" if ent.get("scope") == "build" else ""),
            ]
            opts = c.get("options")
            if opts:
                lines.append("[#9c8268]options[/]  " + ", ".join(str(o.get("value", o) if isinstance(o, dict) else o) for o in opts))
            if "min" in c or "max" in c:
                lines.append(f"[#9c8268]range[/]  {c.get('min', '')}–{c.get('max', '')} {c.get('unit', '')}".rstrip())
            self.query_one("#info", Static).update("\n".join(lines))
            ed = self.query_one("#ed", Input)
            ed.value = _fmt(val)
            ed.styles.display = "block"
            self.query_one("#msg", Static).update(
                "[#b89878]⏎ edit · ⏎-in-field apply · d reset to default · . advanced · / search · esc home[/]")

        # ---- edits + search ----
        def on_input_submitted(self, event):
            if event.input.id == "search":
                self.filter = event.value
                self._build_list()
                self.set_focus(self.query_one("#list", OptionList))
                return
            if event.input.id == "ed" and self.key:
                ok, res = hearth.set_value(self.key, event.value)
                msg = self.query_one("#msg", Static)
                if ok:
                    msg.update(f"[#9ad27a]✓ set {self.key} = {_fmt(res)}[/]")
                    self._build_list()
                    self._show(self.key)
                else:
                    msg.update(f"[#ff8a7a]✗ {res}[/]")

        def on_input_changed(self, event):
            if event.input.id == "search":
                self.filter = event.value
                self._build_list()

        # ---- actions ----
        def action_search(self):
            self.set_focus(self.query_one("#search", Input))

        def action_advanced(self):
            self.advanced = not self.advanced
            self._build_list()
            self.query_one("#msg", Static).update(
                f"[#b89878]advanced settings {'glowing' if self.advanced else 'banked'}[/]")

        def action_reset(self):
            if self.key:
                hearth.reset_value(self.key)
                self._build_list()
                self._show(self.key)
                self.query_one("#msg", Static).update(f"[#e0a35f]↺ {self.key} back to default[/]")

        def action_home(self):
            self._home()
            self.set_focus(self.query_one("#list", OptionList))

        # ---- the landing hearth: the campfire, glowing ----
        def _banner(self):
            rows = HEARTH_LOGO.strip("\n").split("\n")
            out = [f"[{FIRE[i % len(FIRE)]}]{r}[/]" for i, r in enumerate(rows)]
            out += ["", "[#cdb79e]pick a setting above to tend it — ↑↓ to wander, / to search the embers.[/]"]
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
