import QtQuick
import Quickshell
import Quickshell.Io

// Headless service for the `how` Omarchy plugin (no UI, no bar icon).
//
// When the plugin is enabled, the shell loads this service, which runs
// scripts/plugin-link.sh from the plugin checkout once. That script makes
// ~/.local/bin/how a symlink to the `how` file in this checkout, so
// `omarchy plugin update` also updates the CLI. It uses no network and no sudo,
// never replaces a file it does not recognise, steps aside for a packaged
// /usr/bin/how, and logs each decision to ~/.local/state/how/plugin.log.
Item {
  id: root
  visible: false

  // Injected by the shell. __sourceDir is the plugin checkout
  // (~/.config/omarchy/plugins/<id>); third-party plugins are documented to
  // find their bundled scripts through it.
  property var manifest: null

  readonly property string pluginDir: {
    if (manifest && manifest.__sourceDir) return String(manifest.__sourceDir)
    // Fallback: the directory this file was loaded from.
    var url = String(Qt.resolvedUrl("."))
    return decodeURIComponent(url.replace(/^file:\/\//, "")).replace(/\/$/, "")
  }

  property bool linked: false

  function link() {
    if (linked || !pluginDir || linkProc.running) return
    linked = true
    linkProc.command = ["bash", pluginDir + "/scripts/plugin-link.sh", pluginDir]
    linkProc.running = true
  }

  onManifestChanged: Qt.callLater(link)
  Component.onCompleted: Qt.callLater(link)

  Process {
    id: linkProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (text.trim()) console.log(text.trim())
    }
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: if (text.trim()) console.warn(text.trim())
    }
  }
}
