{ lib
, python3Packages
}:

python3Packages.buildPythonApplication {
  pname = "hearth";
  version = "0.1.0";
  pyproject = true;
  src = ./.;

  build-system = [ python3Packages.setuptools ];

  # The core engine (store + signal + CLI) is pure standard library. Only `hearth tui` needs textual
  # (lazy-imported), so the CLI still runs on a host without it.
  dependencies = [ python3Packages.textual ];

  doCheck = false;
  pythonImportsCheck = [ "hearth" "hearth.tui" ];

  meta = {
    description = "Schema-driven settings store with a change-diff signal (one JSON store, per-key reload signal)";
    homepage = "https://github.com/sihooleebd/hearth";
    license = lib.licenses.mit;
    mainProgram = "hearth";
    platforms = lib.platforms.linux;
  };
}
