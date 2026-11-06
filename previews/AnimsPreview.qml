import QtQuick
import qs.Commons

// Анимации: мини-сцена с кривыми и скоростями пресета (hl.curve / hl.animation из .lua) — окно
// открывается (windowsIn), стоит, закрывается (windowsOut), затем переключение стола (workspaces).
// Длительность = speed × 100 мс (как у Hyprland), кривая — BezierSpline. Цикл крутится, только
// пока сцена видна (running: visible) — в фоне ничего не тратит.
Item {
  id: ap
  property var t
  property string lua: ""
  property string wallpaper: ""
  property real screenWidth: 1440
  property real screenHeight: 900

  readonly property var spec: parse(lua)

  function parse(text) {
    var curves = { "default": [0, 0.75, 0.15, 1], "linear": [0, 0, 1, 1] }
    var anims = ({})
    var src = String(text || "")
    var reC = /hl\.curve\(\s*"([^"]+)"[^)]*?points\s*=\s*\{\s*\{\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\}\s*,\s*\{\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\}/g
    var m
    while ((m = reC.exec(src)) !== null) curves[m[1]] = [Number(m[2]), Number(m[3]), Number(m[4]), Number(m[5])]
    var reA = /hl\.animation\(\s*\{([^}]*)\}\s*\)/g
    while ((m = reA.exec(src)) !== null) {
      var body = m[1], a = ({})
      var f = /(\w+)\s*=\s*("([^"]*)"|[-\w.]+)/g, p
      while ((p = f.exec(body)) !== null) a[p[1]] = p[3] !== undefined ? p[3] : p[2]
      if (a.leaf) anims[a.leaf] = a
    }
    var globalOff = /animations\s*=\s*\{\s*enabled\s*=\s*false/.test(src)
    function pick(names) {
      for (var i = 0; i < names.length; i++) if (anims[names[i]]) return anims[names[i]]
      return ({})
    }
    function mk(a, defStyle) {
      var on = !globalOff && a.enabled !== "false"
      var speed = Number(a.speed)
      var c = curves[a.bezier] || curves["default"]
      return { ms: on ? Math.max(1, Math.round((isFinite(speed) ? speed : 5) * 100)) : 1, curve: [c[0], c[1], c[2], c[3], 1, 1],
               style: String(a.style || defStyle) }
    }
    return { win: mk(pick(["windowsIn", "windows", "global"]), "popin 80%"),
             out: mk(pick(["windowsOut", "windows", "global"]), "popin 80%"),
             ws: mk(pick(["workspaces", "global"]), "slide"), empty: src === "" }
  }
  // popin 80% → 0.8; иначе null.
  function popin(style) { var m = /popin\s+(\d+)%?/.exec(style); return /popin/.test(style) ? (m ? Number(m[1]) / 100 : 0.8) : null }

  ScreenMock {
    id: screen
    anchors.fill: parent
    t: ap.t
    screenWidth: ap.screenWidth
    screenHeight: ap.screenHeight
    wallpaper: ap.wallpaper

    // Стол, который уезжает при переключении (workspaces), и пустой следующий.
    Item {
      id: desk
      width: parent.width
      height: parent.height
      Rectangle {   // уже открытое окно слева
        x: 24; y: 24; width: parent.width * 0.5 - 36; height: parent.height - 48
        radius: 12; color: Util.alpha(Color.background, 0.92)
        border.width: 2; border.color: Util.alpha(ap.t.foreground, 0.25)
      }
      Rectangle {   // окно, которое открывается и закрывается
        id: win
        readonly property real homeX: parent.width * 0.5 + 12
        x: homeX; y: 24; width: parent.width * 0.5 - 36; height: parent.height - 48
        radius: 12; color: Util.alpha(Color.background, 0.95)
        border.width: 2; border.color: ap.t.primary
        transformOrigin: Item.Center
        opacity: 0
        Column {
          x: 28; y: 26; spacing: 14
          Repeater { model: 7; Rectangle { required property int index; width: 160 + (index * 71) % 260; height: 12; radius: 6; color: Util.alpha(ap.t.foreground, 0.3) } }
        }
      }
    }

    Text {
      anchors.centerIn: parent
      visible: ap.spec.empty
      text: ap.t.tr("Hyprland's own animations")
      color: ap.t.foreground
      font.family: ap.t.headFont
      font.pixelSize: 48
    }
  }

  // Цикл: открыть → пауза → закрыть → пауза → переключить стол → вернуть.
  SequentialAnimation {
    id: loop
    running: ap.visible && !ap.spec.empty
    loops: Animation.Infinite
    onRunningChanged: if (!running) { win.opacity = 0; desk.x = 0; desk.y = 0 }

    ScriptAction {
      script: {
        var s = ap.spec.win.style, p = ap.popin(s)
        win.scale = p !== null ? p : (/gnomed/.test(s) ? 0.05 : 1)
        win.x = /slide/.test(s) && !/slidevert/.test(s) ? screen.screenWidth : win.homeX
        win.y = /slidevert/.test(s) ? screen.screenHeight : 24
        win.opacity = /slide/.test(s) ? 1 : 0
      }
    }
    ParallelAnimation {
      NumberAnimation { target: win; property: "x"; to: win.homeX; duration: ap.spec.win.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.win.curve }
      NumberAnimation { target: win; property: "y"; to: 24; duration: ap.spec.win.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.win.curve }
      NumberAnimation { target: win; property: "scale"; to: 1; duration: ap.spec.win.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.win.curve }
      NumberAnimation { target: win; property: "opacity"; to: 1; duration: ap.spec.win.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.win.curve }
    }
    PauseAnimation { duration: 800 }
    ParallelAnimation {
      readonly property string st: ap.spec.out.style
      NumberAnimation { target: win; property: "x"; to: /slide/.test(ap.spec.out.style) && !/slidevert/.test(ap.spec.out.style) ? screen.screenWidth : win.homeX; duration: ap.spec.out.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.out.curve }
      NumberAnimation { target: win; property: "y"; to: /slidevert/.test(ap.spec.out.style) ? screen.screenHeight : 24; duration: ap.spec.out.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.out.curve }
      NumberAnimation { target: win; property: "scale"; to: ap.popin(ap.spec.out.style) !== null ? ap.popin(ap.spec.out.style) : (/gnomed/.test(ap.spec.out.style) ? 0.05 : 1); duration: ap.spec.out.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.out.curve }
      NumberAnimation { target: win; property: "opacity"; to: /slide/.test(ap.spec.out.style) ? 1 : 0; duration: ap.spec.out.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.out.curve }
    }
    ScriptAction { script: win.opacity = 0 }
    PauseAnimation { duration: 400 }
    // Переключение стола: slide — вбок, slidevert — вверх, fade — растворение.
    ParallelAnimation {
      NumberAnimation { target: desk; property: "x"; to: /slidevert|fade/.test(ap.spec.ws.style) ? 0 : -screen.screenWidth; duration: ap.spec.ws.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.ws.curve }
      NumberAnimation { target: desk; property: "y"; to: /slidevert/.test(ap.spec.ws.style) ? -screen.screenHeight : 0; duration: ap.spec.ws.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.ws.curve }
      NumberAnimation { target: desk; property: "opacity"; to: /fade/.test(ap.spec.ws.style) ? 0 : 1; duration: ap.spec.ws.ms; easing.type: Easing.BezierSpline; easing.bezierCurve: ap.spec.ws.curve }
    }
    PauseAnimation { duration: 500 }
    ScriptAction { script: { desk.x = 0; desk.y = 0; desk.opacity = 1 } }
    PauseAnimation { duration: 700 }
  }
  onSpecChanged: if (loop.running) loop.restart()
}
