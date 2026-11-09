import QtQuick
import Quickshell
import Quickshell.Io

// Headless CLI bootstrap service (no UI, no bar icon).
// Ensures the native `how` CLI binary is installed to ~/.local/bin/how when the plugin is enabled.
QtObject {
  id: root

  property string pluginDir: Quickshell.env("HOME") + "/.config/omarchy/plugins/io.github.mdsyseng.how"
  property string localBinHow: Quickshell.env("HOME") + "/.local/bin/how"

  property Process bootstrapProc: Process {
    command: [
      "bash",
      "-c",
      "if [ ! -x \"$1\" ] && [ -x \"$0/install.sh\" ]; then \"$0/install.sh\" >/dev/null 2>&1 || true; fi",
      root.pluginDir,
      root.localBinHow
    ]
  }

  Component.onCompleted: {
    if (!bootstrapProc.running) {
      bootstrapProc.running = true
    }
  }
}
