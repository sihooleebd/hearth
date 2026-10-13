# hearth

**A tiny, schema-driven settings store with a change-diff signal.** One JSON file every part of a
system reads; a per-key "what just changed" signal so each part reloads only its own slice. App- and
language-agnostic — it manages JSON and nothing else, so a QML panel, a Lua config, and a shell script
can all share one source of truth.

Built for a bespoke Hyprland desktop (to replace a sprawl of hardcoded values and `sed -i` menus) but
it knows nothing about that desktop: you generate a `schema.json`, point `$HEARTH_DIR` at it, and drive
it from a TUI, a keybind, or a script.

## Model

```
schema.json   (you generate it)   flat registry of typed setting records, keyed by dotted path
      │
      ▼  hearth  (the only writer)
overrides.json        only the keys you changed      (survives regeneration of the schema)
settings.json         effective values, NESTED        ← every consumer reads this
settings.signal.json  { version, changed:[keys], ts } ← the "git diff"; watchers fire on it
```

`settings.json = defaults(from schema) ⊕ overrides`, nested so `jq '.panel.geometry.width'` just works.

### A setting record (`schema.json`)

```jsonc
{ "settings": {
    "panel.geometry.width": {
      "type": "int", "default": 800, "label": "Panel width",
      "help": "Width of the panel.", "tier": "common", "scope": "runtime",
      "constraints": { "min": 480, "max": 1200, "step": 10, "unit": "px" }
    },
    "panel.colors.tile_bg": {
      "type": "color", "default": "#16ffffff", "label": "Inactive tile",
      "constraints": { "alpha": true }
    }
} }
```

Types: `bool int float string enum color font path list` (+ anything you add a reader for). The key is
the address: store path, tree position, and diff identity in one.

## CLI

```sh
hearth get  panel.geometry.width          # -> 800        (effective value, JSON)
hearth set  panel.geometry.width 820      # validate, override, re-materialise, signal
hearth reset panel.geometry.width         # back to default
hearth dump                               # whole effective store (nested JSON)
hearth sync                               # re-materialise + signal diffs (run after regenerating schema)
hearth watch panel hyprland               # block; print changed keys under these prefixes, per batch
```

A consumer is three lines in any language:

```sh
hearth watch panel | while read -r keys; do
  reload_panel $keys            # only the keys under "panel" that actually changed
done
```

`$HEARTH_DIR` defaults to `$XDG_STATE_HOME/hearth` (`~/.local/state/hearth`).

## Install

```nix
{
  inputs.hearth.url = "github:sihooleebd/hearth";
  environment.systemPackages = [ inputs.hearth.packages.${pkgs.system}.default ];
}
```

## Development

```sh
nix develop
HEARTH_DIR=/tmp/hearth python -m hearth.main dump
```

It's one file, `hearth/main.py`, pure standard library.

## License

[MIT](LICENSE) © Benjamin Lee
