import QtQuick
import qs.Commons

// Дашборд: панель под баром на мини-экране по ключам dash* в widgets.json — стиль (default /
// dotmatrix), фон и прозрачность (или «как у бара»), скругление, рамка, включённые блоки
// (плеер, календарь, погода, графики), единицы погоды.
Item {
  id: dp
  property var t
  property var v: ({})
  property string wallpaper: ""

  function str(key, def) { return v[key] !== undefined && v[key] !== "" ? String(v[key]) : def }
  function num(key, def) { var x = Number(v[key]); return v[key] === undefined || !isFinite(x) ? def : x }
  function on(key, def) { return v[key] === undefined ? def : String(v[key]) === "true" }

  readonly property bool dots: str("dashStyle", "default") === "dotmatrix"
  readonly property bool follow: on("dashFollowBar", true)
  readonly property bool attached: str("dashAttach", "auto") !== "floating"
  readonly property color fill: follow ? Color.bar.background : t.resolveColor(str("dashBackground", "background"))
  readonly property real alpha: follow ? 0.94 : num("dashAlpha", 0.94)
  readonly property var blocks: {
    var b = []
    if (on("dashMedia", true)) b.push({ icon: "󰎆", title: t.tr("Player"), body: "Nightcall — Kavinsky" })
    if (on("dashCalendar", true)) b.push({ icon: "󰃭", title: t.tr("Calendar"), body: Qt.formatDate(new Date(), "d MMMM") })
    if (on("dashWeather", true)) b.push({ icon: "󰖐", title: t.tr("Weather"), body: str("weatherUnits", "celsius") === "fahrenheit" ? "57 °F" : "14 °C" })
    if (on("dashStats", true)) b.push({ icon: "󰍛", title: "CPU · RAM", body: "12 % · 41 %", graph: true })
    return b
  }

  MiniScreen {
    id: screen
    anchors.fill: parent
    t: dp.t
    wallpaper: dp.wallpaper

    Rectangle {
      readonly property real k: screen.k
      width: 760 * k
      height: grid.implicitHeight + 28 * k
      x: (parent.width - width) / 2
      y: screen.barHeight + (dp.attached ? 0 : 10 * k)
      radius: dp.num("dashRadius", 22) * k
      color: Util.alpha(dp.fill, dp.alpha)
      border.width: dp.on("dashBorder", false) ? 1 : 0
      border.color: Util.alpha(dp.t.foreground, 0.3)

      Text {
        visible: dp.blocks.length === 0
        anchors.centerIn: parent
        text: dp.t.tr("All blocks are off")
        color: dp.t.muted
        font.family: dp.t.fontFamily
        font.pixelSize: Math.max(7, 13 * parent.k)
      }

      Grid {
        id: grid
        anchors.centerIn: parent
        columns: 2
        spacing: 10 * parent.k
        Repeater {
          model: dp.blocks
          Rectangle {
            required property var modelData
            width: 360 * screen.k
            height: 92 * screen.k
            radius: Math.max(2, (dp.num("dashRadius", 22) - 8) * screen.k)
            color: Util.alpha(dp.t.foreground, 0.06)
            border.width: dp.dots ? 1 : 0
            border.color: Util.alpha(dp.t.primary, 0.6)
            Row {
              anchors.left: parent.left
              anchors.leftMargin: 14 * screen.k
              anchors.verticalCenter: parent.verticalCenter
              spacing: 12 * screen.k
              Text { text: modelData.icon; color: dp.t.primary; font.family: dp.t.iconFont; font.pixelSize: Math.max(8, 26 * screen.k); anchors.verticalCenter: parent.verticalCenter }
              Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 3 * screen.k
                Text { text: modelData.title; color: dp.t.muted; font.family: dp.dots ? dp.t.headFont : dp.t.fontFamily; font.pixelSize: Math.max(6, 11 * screen.k) }
                Text { text: modelData.body; color: dp.t.foreground; font.family: dp.dots ? dp.t.headFont : dp.t.fontFamily; font.pixelSize: Math.max(7, 15 * screen.k); font.bold: true }
              }
            }
          }
        }
      }
    }
  }
}
