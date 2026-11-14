import QtQuick
import Quickshell
import qs.Commons
import qs.Ui

// Omtopia Personalizer bar button: a palette glyph that toggles the
// customizer overlay. The overlay itself is the UI — this widget is only
// the launcher, so there is no panel here. While the overlay is open the
// glyph is tinted accent; a short poll keeps that state fresh, because
// isPluginOpen is a function call, not a bindable property.
BarWidget {
  id: root

  moduleName: "kamradsmeshnyavy.customizer"

  // True while the customizer overlay is open.
  property bool customizerOpen: false

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

  BarIconButton {
    id: button

    anchors.fill: parent
    bar: root.bar
    // Palette glyph (Nerd Font mdi-palette) — the same icon the
    // customizer uses for its Theme category.
    text: "󰏘"
    tooltipText: root.customizerOpen ? "Omtopia Personalizer — open" : "Omtopia Personalizer"
    active: root.customizerOpen
    activeColor: Color.accent
    onPressed: function (buttonCode) {
      if (buttonCode === Qt.LeftButton)
        root.toggleCustomizer()
    }
  }
}
