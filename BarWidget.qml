import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.mdsyseng.how"

  property string pluginDir: Quickshell.env("HOME") + "/.config/omarchy/plugins/io.github.mdsyseng.how"
  property string localBinHow: Quickshell.env("HOME") + "/.local/bin/how"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Component.onCompleted: {
    if (!bootstrapProc.running) {
      bootstrapProc.running = true
    }
  }

  Process {
    id: bootstrapProc
    command: [
      "bash",
      "-c",
      "if [ ! -x \"$1\" ] && [ -x \"$0/install.sh\" ]; then \"$0/install.sh\" >/dev/null 2>&1 || true; fi",
      root.pluginDir,
      root.localBinHow
    ]
  }

  function launchInteractiveAsk() {
    if (!root.bar) return
    root.bar.run(
      "omarchy-launch-floating-terminal-with-presentation \"bash -c 'printf \\\"\\033[1;36mhow ❯\\033[0m Ask how to do anything: \\\"; read -r q && [ -n \\\"\\$q\\\" ] && how \\$q'\""
    )
  }

  function launchStatus() {
    if (!root.bar) return
    root.bar.run("omarchy-launch-floating-terminal-with-presentation \"how status\"")
  }

  ShellIpc {
    target: "io.github.mdsyseng.how"

    function open(): void {
      root.launchInteractiveAsk()
    }

    function status(): void {
      root.launchStatus()
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰘳"
    slotSize: Style.bar.statusSlot
    tooltipText: "how — Ask how to do anything in Omarchy & Linux (left-click: ask, right-click: status)"
    onPressed: function(mouseButton) {
      if (mouseButton === Qt.RightButton) {
        root.launchStatus()
      } else {
        root.launchInteractiveAsk()
      }
    }
  }
}
