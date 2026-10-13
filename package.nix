{ lib
, python3Packages
}:

python3Packages.buildPythonApplication {
  pname = "hearth";
  version = "0.1.0";
  pyproject = true;
  src = ./.;

  build-system = [ python3Packages.setuptools ];

  # Pure standard library -- no runtime dependencies, nothing to wrap. hearth only reads/writes JSON
  # files and polls an mtime; the app that embeds it generates schema.json and points $HEARTH_DIR at it.
  doCheck = false;
  pythonImportsCheck = [ "hearth" ];

  meta = {
    description = "Schema-driven settings store with a change-diff signal (one JSON store, per-key reload signal)";
    homepage = "https://github.com/sihooleebd/hearth";
    license = lib.licenses.mit;
    mainProgram = "hearth";
    platforms = lib.platforms.linux;
  };
}
