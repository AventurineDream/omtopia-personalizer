import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Services.UPower
import QtQuick 6.11
import QtQuick.Shapes
import qs.Commons
import "Geometry.js" as Geometry
import "nihil" as Nihil

// Nothing-inspired perimeter Glyph lighting for Omarchy.
// Ported from home/shell/frame/GlyphLight.qml and services/Glyph.qml in NIHIL
// by Pol Iglesias (poligle), MIT License — https://github.com/poligle/Nihil-Shell.
//
// Stays completely unmapped (`visible: false`, 0% GPU) until triggered by:
//   - `omarchy-shell -q glyph notify false|true` (from kamradsmeshnyavy.notifications)
//   - `omarchy-shell -q glyph test false|true` / `omarchy-shell -q glyph charge`
//   - Plugging in the laptop charger (UPower.displayDevice)
Item {
  id: root

  property var activeSkin: ({})
  property var activeBar: ({})
  property var palette: ({})
  property string soundScript: ""

  property var cfg: ({})

  readonly property bool enabled: cfg.glyphEnabled === true
  readonly property bool criticalRed: cfg.glyphCriticalRed !== false
  readonly property bool chargerEnabled: cfg.glyphCharger !== false
  readonly property int sweepDuration: Math.max(300, Number(cfg.glyphDuration) || 1100)
  readonly property real coreWidth: Math.max(1, Number(cfg.glyphThickness) || 2.5)
  readonly property string insetMode: String(cfg.glyphInsetMode || "auto")

  function resolveColor(spec, fallback) {
    var s = String(spec || "")
    if (!s) return fallback
    if (s.charAt(0) === "#") return s
    if (s === "bar") return Color.bar.background
    if (s === "background") return Color.background
    if (s === "foreground") return Color.foreground
    if (s === "accent") return Color.accent
    if (s === "muted") return Color.muted
    if (s === "urgent") return Color.urgent
    if (s.indexOf("nihil.") === 0 && Nihil.Palette[s.slice(6)] !== undefined) return Nihil.Palette[s.slice(6)]
    if (root.palette && root.palette[s]) return root.palette[s]
    return fallback
  }

  readonly property color normalColor: resolveColor(cfg.glyphColor || "nihil.fg", Nihil.Palette.fg)
  readonly property color alertColor: resolveColor(cfg.glyphCriticalColor || "nihil.danger", Nihil.Palette.danger)

  readonly property bool useFrame: insetMode === "frame" || (insetMode === "auto" && activeSkin && activeSkin.shape === "frame")
  readonly property string barPos: String((activeBar && activeBar.position) || "top")
  readonly property int barSize: {
    var h = Number(activeSkin && activeSkin.height) || 0
    if (h > 0) return h
    return (barPos === "left" || barPos === "right") ? 28 : 26
  }
  readonly property int frameWidth: useFrame ? Math.max(1, activeSkin && activeSkin.frameWidth !== undefined ? Number(activeSkin.frameWidth) : 8) : 3
  readonly property int leftInset: useFrame && barPos === "left" ? barSize : frameWidth
  readonly property int topInset: useFrame && barPos === "top" ? barSize : frameWidth
  readonly property int rightInset: useFrame && barPos === "right" ? barSize : frameWidth
  readonly property int bottomInset: useFrame && barPos === "bottom" ? barSize : frameWidth
  readonly property int frameRadius: useFrame ? Math.max(8, Number(activeSkin && activeSkin.radius) || 18) : 14

  signal sweep(color tint, int laps, int startEdge)
  signal rise(color tint)

  function parseCritical(arg) {
    var s = String(arg || "").trim().toLowerCase()
    if (s === "true" || s === "1" || s === "critical") return true
    if (s.charAt(0) === "{") {
      try {
        var o = JSON.parse(arg)
        return o.critical === true || String(o.urgency).toLowerCase() === "critical" || o.urgency === 2
      } catch (e) {}
    }
    return false
  }

  function triggerSweep(critical, force) {
    if (!force && !root.enabled) return
    var isCrit = critical && root.criticalRed
    root.sweep(isCrit ? root.alertColor : root.normalColor, critical ? 2 : 1, 1)
  }

  function triggerCharge(force) {
    if (!force && (!root.enabled || !root.chargerEnabled)) return
    root.rise(root.normalColor)
  }

  FileView {
    path: Quickshell.env("HOME") + "/.config/omarchy/glyph.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: {
      try {
        var v = JSON.parse(text() || "{}")
        root.cfg = v && typeof v === "object" ? v : ({})
      } catch (e) { root.cfg = ({}) }
    }
    onLoadFailed: root.cfg = ({})
  }

  // Charger plug-in watcher (armed after 4s so login state doesn't fire).
  readonly property var batteryDevice: UPower.displayDevice
  readonly property bool batteryCharging: batteryDevice !== null && batteryDevice !== undefined
    && (batteryDevice.state === UPowerDeviceState.Charging || batteryDevice.state === UPowerDeviceState.PendingCharge)
  property bool chargerArmed: false

  Timer {
    interval: 4000
    running: true
    onTriggered: root.chargerArmed = true
  }

  onBatteryChargingChanged: {
    if (batteryCharging && chargerArmed) {
      root.triggerCharge(false)
      // Charger sound belongs to the Glyph effect: off together with it.
      if (root.enabled && root.chargerEnabled && root.soundScript) Quickshell.execDetached([root.soundScript, "power"])
    }
  }

  IpcHandler {
    target: "glyph"

    function notify(critical: string): string {
      root.triggerSweep(root.parseCritical(critical), false)
      return "ok"
    }

    function test(critical: string): string {
      root.triggerSweep(root.parseCritical(critical), true)
      return "ok"
    }

    function charge(): string {
      root.triggerCharge(true)
      return "ok"
    }
  }

  Variants {
    model: Quickshell.screens

    PanelWindow {
      id: win
      required property var modelData
      screen: modelData

      property color tint: root.normalColor
      property color riseTint: root.normalColor
      property int startEdge: 1
      property real progress: 0
      property real climb: 0

      readonly property real segment: 260
      readonly property real haloWidth: Math.max(6, root.coreWidth * 3.2)
      readonly property real perimeter: Geometry.ringLength(width, height,
        root.leftInset, root.topInset, root.rightInset, root.bottomInset, root.frameRadius)
      readonly property string ring: Geometry.outline(width, height,
        root.leftInset, root.topInset, root.rightInset, root.bottomInset, root.frameRadius, startEdge)
      readonly property real reach: climb * perimeter / 2
      readonly property string leftRoute: Geometry.rise(width, height,
        root.leftInset, root.topInset, root.rightInset, root.bottomInset, root.frameRadius, -1)
      readonly property string rightRoute: Geometry.rise(width, height,
        root.leftInset, root.topInset, root.rightInset, root.bottomInset, root.frameRadius, 1)

      function pattern(w) { return [segment / w, (perimeter + segment) / w] }
      function offset(w) { return (segment - progress * (perimeter + segment)) / w }

      visible: sweepAnim.running || riseAnim.running
      anchors { top: true; bottom: true; left: true; right: true }
      color: "transparent"
      WlrLayershell.namespace: "omarchy-glyph"
      WlrLayershell.layer: WlrLayer.Overlay
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}

      Shape {
        id: sweepShape
        anchors.fill: parent
        opacity: 0
        visible: opacity > 0
        preferredRendererType: Shape.GeometryRenderer
        layer.enabled: true
        layer.samples: 4

        ShapePath {
          fillColor: "transparent"
          strokeColor: Qt.rgba(win.tint.r, win.tint.g, win.tint.b, 0.22)
          strokeWidth: win.haloWidth
          strokeStyle: ShapePath.DashLine
          capStyle: ShapePath.RoundCap
          dashPattern: win.pattern(win.haloWidth)
          dashOffset: win.offset(win.haloWidth)
          PathSvg { path: win.ring }
        }

        ShapePath {
          fillColor: "transparent"
          strokeColor: win.tint
          strokeWidth: root.coreWidth
          strokeStyle: ShapePath.DashLine
          capStyle: ShapePath.RoundCap
          dashPattern: win.pattern(root.coreWidth)
          dashOffset: win.offset(root.coreWidth)
          PathSvg { path: win.ring }
        }
      }

      component Beam: ShapePath {
        property string route: ""
        property real reach: 0
        property real total: 1
        property color tint: Nihil.Palette.fg
        property real length: 0
        property real thick: 2.5
        property real alpha: 1

        readonly property real tail: length > 0 ? Math.max(0, reach - length) : 0

        fillColor: "transparent"
        strokeColor: Qt.rgba(tint.r, tint.g, tint.b, alpha)
        strokeWidth: thick
        strokeStyle: ShapePath.DashLine
        capStyle: length > 0 ? ShapePath.RoundCap : ShapePath.FlatCap
        dashPattern: [Math.max(0.01, reach - tail) / thick, (total + 100) / thick]
        dashOffset: -tail / thick

        PathSvg { path: route }
      }

      Shape {
        id: riseShape
        anchors.fill: parent
        opacity: 0
        visible: opacity > 0 && win.reach > 1
        preferredRendererType: Shape.GeometryRenderer
        layer.enabled: true
        layer.samples: 4

        Beam { route: win.leftRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: root.coreWidth; alpha: 0.14 }
        Beam { route: win.leftRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: root.coreWidth; length: 420; alpha: 0.26 }
        Beam { route: win.leftRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: win.haloWidth; length: 180; alpha: 0.22 }
        Beam { route: win.leftRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: root.coreWidth; length: 180 }

        Beam { route: win.rightRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: root.coreWidth; alpha: 0.14 }
        Beam { route: win.rightRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: root.coreWidth; length: 420; alpha: 0.26 }
        Beam { route: win.rightRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: win.haloWidth; length: 180; alpha: 0.22 }
        Beam { route: win.rightRoute; reach: win.reach; total: win.perimeter; tint: win.riseTint; thick: root.coreWidth; length: 180 }
      }

      SequentialAnimation {
        id: sweepAnim
        property int laps: 1
        PropertyAction { target: sweepShape; property: "opacity"; value: 1 }
        NumberAnimation {
          target: win
          property: "progress"
          from: 0
          to: 1
          duration: root.sweepDuration
          easing.type: Easing.InOutCubic
          loops: sweepAnim.laps
        }
        PropertyAction { target: sweepShape; property: "opacity"; value: 0 }
      }

      SequentialAnimation {
        id: riseAnim
        PropertyAction { target: win; property: "climb"; value: 0 }
        PropertyAction { target: riseShape; property: "opacity"; value: 1 }
        NumberAnimation {
          target: win
          property: "climb"
          from: 0
          to: 1
          duration: 1260
          easing.type: Easing.BezierSpline
          easing.bezierCurve: [0.2, 0, 0, 1, 1, 1]
        }
        NumberAnimation { target: riseShape; property: "opacity"; to: 0; duration: 540; easing.type: Easing.OutCubic }
        PropertyAction { target: win; property: "climb"; value: 0 }
      }

      Connections {
        target: root
        function onSweep(tint, laps, startEdge) {
          win.tint = tint
          win.startEdge = startEdge
          sweepAnim.stop()
          sweepAnim.laps = laps
          sweepAnim.start()
        }
        function onRise(tint) {
          win.riseTint = tint
          riseAnim.stop()
          riseAnim.start()
        }
      }
    }
  }
}
