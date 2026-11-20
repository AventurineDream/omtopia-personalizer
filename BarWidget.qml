import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// Omtopia Personalizer bar button: a palette glyph that toggles the
// customizer overlay. The overlay itself is the UI — this widget is only
// the launcher, so there is no panel here. While the overlay is open the
// glyph is tinted accent; a short poll keeps that state fresh, because
// isPluginOpen is a function call, not a bindable property. The tooltip
// follows the Customizer's language (`customizer.sh lang`, i18n/<lang>.json),
// re-read whenever the overlay opens, as the overlay itself does.
BarWidget {
  id: root

  moduleName: "kamradsmeshnyavy.customizer"

  // True while the customizer overlay is open.
  property bool customizerOpen: false
  // i18n/<lang>.json of the Customizer's language; empty for English.
  property var i18n: ({})

  // English string -> its translation, or the string itself when there is none.
  function tr(s) { return root.i18n[s] !== undefined ? root.i18n[s] : s }

  // The overlay can change its language while open; pick the change up on the next open.
  onCustomizerOpenChanged: if (root.customizerOpen) root.reloadLanguage()
  Component.onCompleted: root.reloadLanguage()

  function reloadLanguage() {
    langProc.running = false
    langProc.running = true
  }

  function refreshOpenState() {
    if (root.bar && root.bar.shell && typeof root.bar.shell.isPluginOpen === "function")
      root.customizerOpen = root.bar.shell.isPluginOpen("kamradsmeshnyavy.customizer")
    else
      root.customizerOpen = false
  }

  function toggleCustomizer() {
    if (root.bar && root.bar.shell && typeof root.bar.shell.toggle === "function")
      root.bar.shell.toggle("kamradsmeshnyavy.customizer", "{}")
    else
      Quickshell.execDetached(["omarchy-shell", "shell", "toggle", "kamradsmeshnyavy.customizer"])
    // Refresh the indicator at once instead of waiting for the next poll.
    Qt.callLater(root.refreshOpenState)
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Timer {
    interval: 1000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refreshOpenState()
  }

  Process {
    id: langProc
    command: [decodeURIComponent(String(Qt.resolvedUrl("customizer.sh")).replace(/^file:\/\//, "")), "lang"]
    stdout: StdioCollector {
      onStreamFinished: {
        var lang = text.trim()
        if (!lang || lang === "en") { root.i18n = ({}); return }
        var path = decodeURIComponent(String(Qt.resolvedUrl("i18n/" + lang + ".json")).replace(/^file:\/\//, ""))
        // A FileView does not reload for an unchanged path (ru -> en -> ru would keep the empty table).
        if (i18nFile.path === path) i18nFile.reload()
        else i18nFile.path = path
      }
    }
  }

  FileView {
    id: i18nFile
    printErrors: false
    onLoaded: {
      try { root.i18n = JSON.parse(text()) } catch (e) { root.i18n = ({}) }
    }
    onLoadFailed: root.i18n = ({})
  }

  BarIconButton {
    id: button

    anchors.fill: parent
    bar: root.bar
    // Palette glyph (Nerd Font mdi-palette) — the same icon the
    // customizer uses for its Theme category.
    text: "󰏘"
    tooltipText: root.customizerOpen ? root.tr("Omtopia Personalizer — open") : "Omtopia Personalizer"
    active: root.customizerOpen
    activeColor: Color.accent
    onPressed: function (buttonCode) {
      if (buttonCode === Qt.LeftButton)
        root.toggleCustomizer()
    }
  }
}
