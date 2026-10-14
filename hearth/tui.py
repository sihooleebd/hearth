#!/usr/bin/env python3
"""hearth tui -- a settings app (Textual), macOS-System-Settings shaped.

A sidebar of categories on the left; on the right, a scrolling FORM where each setting gets the control
its type deserves -- a Switch for on/off, a Select (dropdown) for choose-one, a text field for the rest
-- editable in place, applied live. `/` searches every setting, `.` reveals advanced ones, `d` resets
the focused one. Warm bonfire palette throughout.
"""
import sys
import json

from . import main as hearth

FIRE = ["#ffd23f", "#ffb627", "#ff9505", "#ff7518", "#f0580f",
        "#e5440f", "#ff7518", "#ff9505", "#ffb627", "#ff9505", "#e5440f", "#c23208"]
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
        from textual.containers import Horizontal, Vertical, VerticalScroll
        from textual.widgets import OptionList, Input, Switch, Select, Static, Footer
        from textual.widgets.option_list import Option
        from rich.text import Text
    except ImportError:
        sys.stderr.write("hearth tui: textual is not installed\n")
        return 1

    class HearthApp(App):
        CSS = """
        Screen { background: #1a1310; color: #efe1d1; }
        #sidebar { width: 24; background: #140e0a; border-right: solid #a8531f; }
        .brand { height: 1; padding: 0 1; color: #ff9505; text-style: bold; background: #140e0a; }
        #search { margin: 1 1 0 1; background: #241a13; color: #efe1d1; border: round #a8531f; }
        #search:focus { border: round #ff9505; }
        #cats { background: transparent; height: 1fr; }
        #cats > .option-list--option-highlighted { background: #6b3317; color: #fff2e4; }
        #cats:focus > .option-list--option-highlighted { background: #8f4420; color: #fff2e4; text-style: bold; }
        #form { padding: 1 2; height: 1fr; }
        .formhdr { color: #ff9505; text-style: bold; padding: 0 0 1 0; }
        .row { layout: horizontal; height: auto; padding: 1 1; border-bottom: solid #2c2017; }
        .lblbox { width: 1fr; height: auto; }
        .lbl { color: #efe1d1; }
        .hlp { color: #9c8268; }
        .row Switch { background: #241a13; }
        .row Switch.-on > .switch--slider { color: #ff9505; }
        .row Select { width: 30; }
        .row Input { width: 40; background: #2c2017; color: #ffe9d4; border: round #a8531f; }
        .row Input:focus { border: round #ff9505; }
        #msg { dock: bottom; height: 1; padding: 0 2; color: #b89878; background: #140e0a; }
        Footer { background: #120c09; }
        """
        BINDINGS = [
            Binding("slash", "search", "Search"),
            Binding("full_stop", "advanced", "Advanced"),
            Binding("d", "reset", "Reset focused"),
            Binding("q", "quit", "Quit"),
        ]

        def __init__(self):
            super().__init__()
            self.schema = hearth._schema()
            self.advanced = False
            self.filter = ""
            self.category = None
            self._loading = False

        def compose(self):
            with Horizontal():
                with Vertical(id="sidebar"):
                    yield Static("🔥 bonfire", classes="brand")
                    yield Input(placeholder="search…", id="search")
                    yield OptionList(id="cats")
                yield VerticalScroll(id="form")
            yield Static("", id="msg")
            yield Footer()

        async def on_mount(self):
            self.title = "bonfire settings"
            self._build_cats()
            await self._load_form()

        # ---- data ----
        def _cats(self):
            found = {k.split(".", 1)[0] for k in self.schema}
            return [c for c in ORDER if c in found] + sorted(found - set(ORDER))

        def _visible(self, k):
            ent = self.schema[k]
            if ent.get("tier") == "advanced" and not self.advanced:
                return False
            flt = self.filter.lower()
            if flt and flt not in k.lower() and flt not in str(ent.get("label", "")).lower():
                return False
            return True

        def _form_keys(self):
            if self.filter:
                return [k for k in sorted(self.schema) if self._visible(k)]
            return [k for k in sorted(self.schema)
                    if k.split(".", 1)[0] == self.category and self._visible(k)]

        # ---- sidebar ----
        def _build_cats(self):
            ol = self.query_one("#cats", OptionList)
            ol.clear_options()
            for ci, c in enumerate(self._cats()):
                ol.add_option(Option(Text(f" {c}", style=FIRE[ci % len(FIRE)]), id=c))
            if self.category is None and self._cats():
                self.category = self._cats()[0]

        # ---- the form (type-aware controls) ----
        def _control(self, k, ent, val):
            t = ent.get("type")
            c = ent.get("constraints", {}) or {}
            if t == "bool":
                w = Switch(value=bool(val))
            elif t == "enum":
                opts = [str(o.get("value", o) if isinstance(o, dict) else o) for o in (c.get("options") or [])]
                sval = _fmt(val)
                w = Select([(o, o) for o in opts], value=(sval if sval in opts else (opts[0] if opts else None)),
                           allow_blank=not opts)
            else:
                w = Input(value=_fmt(val))
            w._hkey = k
            return w

        def _row(self, k, eff):
            ent = self.schema[k]
            sub = k[len(self.category) + 1:] if (not self.filter and self.category and k.startswith(self.category + ".")) else k
            box = Vertical(classes="lblbox")
            box.compose_add_child(Static(ent.get("label", sub), classes="lbl"))
            help_txt = ent.get("help", "")
            if ent.get("scope") == "build":
                help_txt = (help_txt + "  ↻ needs rebuild").strip()
            if help_txt:
                box.compose_add_child(Static(help_txt, classes="hlp"))
            row = Horizontal(classes="row")
            row.compose_add_child(box)
            row.compose_add_child(self._control(k, ent, eff.get(k)))
            return row

        async def _load_form(self):
            form = self.query_one("#form", VerticalScroll)
            await form.remove_children()
            eff = hearth._effective()
            keys = self._form_keys()
            head = (self.category or "all").upper() if not self.filter else f"SEARCH: {self.filter}"
            rows = [Static(head, classes="formhdr")]
            for k in keys:
                rows.append(self._row(k, eff))
            if not keys:
                rows.append(Static("no settings match", classes="hlp"))
            self._loading = True
            await form.mount(*rows)
            self._loading = False

        # ---- sidebar selection ----
        async def on_option_list_option_highlighted(self, event):
            if event.option is not None and event.option.id and event.option.id != self.category:
                self.category = event.option.id
                self.filter = ""
                await self._load_form()

        # ---- live edits (each control type) ----
        def _set(self, key, raw):
            ok, res = hearth.set_value(key, raw)
            self.query_one("#msg", Static).update(
                f"[#9ad27a]✓ {key} = {_fmt(res)}[/]" if ok else f"[#ff8a7a]✗ {res}[/]")
            return ok

        def on_switch_changed(self, event):
            if not self._loading and getattr(event.switch, "_hkey", None):
                self._set(event.switch._hkey, event.value)

        def on_select_changed(self, event):
            if not self._loading and getattr(event.select, "_hkey", None) and event.value is not Select.BLANK:
                self._set(event.select._hkey, event.value)

        def on_input_submitted(self, event):
            if event.input.id == "search":
                self.filter = event.value
                self.run_worker(self._load_form())
                return
            if getattr(event.input, "_hkey", None):
                self._set(event.input._hkey, event.value)

        def on_input_changed(self, event):
            if event.input.id == "search":
                self.filter = event.value
                self.run_worker(self._load_form())

        # ---- actions ----
        def action_search(self):
            self.set_focus(self.query_one("#search", Input))

        def action_advanced(self):
            self.advanced = not self.advanced
            self.run_worker(self._load_form())
            self.query_one("#msg", Static).update(
                f"[#b89878]advanced settings {'glowing' if self.advanced else 'banked'}[/]")

        def action_reset(self):
            w = self.focused
            key = getattr(w, "_hkey", None)
            if key:
                hearth.reset_value(key)
                self.run_worker(self._load_form())
                self.query_one("#msg", Static).update(f"[#e0a35f]↺ {key} back to default[/]")

    if "--selftest" in argv:                       # headless construction/mount check (no TTY needed)
        import asyncio
        deep = "--deep" in argv
        from textual.widgets import Switch as _Sw, Select as _Se, Input as _In

        calls = []
        if deep:                                   # don't mutate the real store while driving the UI
            hearth.set_value = lambda k, v: (calls.append(("set", k)) or (True, v))
            hearth.reset_value = lambda k: calls.append(("reset", k))

        async def _t():
            app = HearthApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                if deep:
                    # wander a few categories (rebuilds the form each time)
                    cats = app.query_one("#cats")
                    for _ in range(min(3, cats.option_count)):
                        await pilot.press("down")
                        await pilot.pause()
                    # flip the first Switch in the current form, pick in the first Select, type an Input
                    for w in app.query(_Sw):
                        w.toggle(); await pilot.pause(); break
                    for w in app.query(_Se):
                        opts = [o for o in getattr(w, "_options", [])]
                        if opts:
                            w.value = opts[-1].value; await pilot.pause()
                        break
                    for w in app.query(_In):
                        if getattr(w, "_hkey", None):
                            w.value = w.value; app.on_input_submitted(_In.Submitted(w, w.value)); await pilot.pause()
                            break
                    # search, advanced, reset
                    app.action_search(); await pilot.pause()
                    s = app.query_one("#search", _In); s.value = "wall"
                    app.on_input_changed(_In.Changed(s, "wall")); await pilot.pause()
                    s.value = ""; app.on_input_changed(_In.Changed(s, "")); await pilot.pause()
                    app.action_advanced(); await pilot.pause()
                    app.action_advanced(); await pilot.pause()
                    # reset the focused control
                    for w in app.query(_Sw):
                        app.set_focus(w); await pilot.pause(); app.action_reset(); await pilot.pause(); break
                    kinds = {c[0] for c in calls}
                    assert "set" in kinds and "reset" in kinds, f"controls did not fire set/reset: {calls}"

        asyncio.run(_t())
        print("hearth tui deep OK" if deep else "hearth tui selftest OK")
        return 0

    HearthApp().run()
    return 0
