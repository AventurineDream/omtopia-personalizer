import QtQuick
import qs.Commons

// Glyph: подсветка по периметру мини-экрана по glyph.json — цвет, толщина, путь (рамка бара или
// край экрана), а внизу — цвет критического сигнала. Статичная картинка (без анимации — не тратит
// энергию); живой проход — p.
Item {
  id: gp
  property var t
  property var v: ({})
  property string wallpaper: ""

  function str(key, def) { return v[key] !== undefined && v[key] !== "" ? String(v[key]) : def }
  function num(key, def) { var x = Number(v[key]); return v[key] === undefined || !isFinite(x) ? def : x }
  function on(key, def) { return v[key] === undefined ? def : String(v[key]) === "true" }

  readonly property bool enabled: on("glyphEnabled", false)
  readonly property color glow: t.resolveColor(str("glyphColor", "foreground"))
  readonly property color critical: t.resolveColor(str("glyphCriticalColor", "urgent"))
  readonly property bool frame: str("glyphInsetMode", "auto") === "frame"

  MiniScreen {
    id: screen
    anchors.fill: parent
    t: gp.t
    wallpaper: gp.wallpaper
    dim: 0.45

    // Свечение: несколько рамок с убывающей прозрачностью — мягкий ореол без шейдера.
    Repeater {
      model: 4
      Rectangle {
        required property int index
        readonly property real inset: (gp.frame ? screen.barHeight : 0) + index * gp.num("glyphThickness", 2.5) * screen.k
        x: gp.frame ? 6 * screen.k : 0
        y: inset
        width: parent.width - 2 * x
        height: parent.height - inset - (gp.frame ? 6 * screen.k : 0)
        color: "transparent"
        radius: gp.t.innerRadius
        border.width: Math.max(1, gp.num("glyphThickness", 2.5) * screen.k * (index === 0 ? 1 : 1.6))
        border.color: Util.alpha(gp.glow, index === 0 ? 1 : 0.35 / index)
        opacity: gp.enabled ? 1 : 0.25
      }
    }

    Column {
      anchors.centerIn: parent
      spacing: 8 * screen.k
      Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: gp.enabled ? gp.t.tr("Perimeter lighting is on") : gp.t.tr("Perimeter lighting is off")
        color: gp.t.foreground
        font.family: gp.t.headFont
        font.pixelSize: Math.max(11, 26 * screen.k)
      }
      Row {
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 8 * screen.k
        visible: gp.on("glyphCriticalRed", true)
        Rectangle { width: 18 * screen.k; height: width; radius: width / 2; color: gp.critical; anchors.verticalCenter: parent.verticalCenter }
        Text { text: gp.t.tr("critical alert"); color: gp.t.muted; font.family: gp.t.fontFamily; font.pixelSize: Math.max(10, 18 * screen.k) }
      }
      Text {
        anchors.horizontalCenter: parent.horizontalCenter
        text: gp.num("glyphDuration", 1100) + " ms · p — " + gp.t.tr("test")
        color: gp.t.muted
        font.family: gp.t.fontFamily
        font.pixelSize: Math.max(10, 16 * screen.k)
      }
    }
  }
}
