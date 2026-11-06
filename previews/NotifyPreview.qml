import QtQuick
import qs.Commons

// Уведомления: тосты на мини-экране по notify-style.json — стиль (drawer — одна панель у бара/края,
// stock — отдельные карточки), угол, ширина, фон и прозрачность (или «как у бара»), скругление,
// вид карточек (flat / bordered / dotmatrix), сколько видно сразу.
Item {
  id: np
  property var t
  property var v: ({})
  property string wallpaper: ""

  function str(key, def) { return v[key] !== undefined && v[key] !== "" ? String(v[key]) : def }
  function num(key, def) { var x = Number(v[key]); return v[key] === undefined || !isFinite(x) ? def : x }
  function on(key, def) { return v[key] === undefined ? def : String(v[key]) === "true" }

  readonly property bool drawer: str("notifyStyle", "drawer") === "drawer"
  readonly property bool follow: on("notifyFollowBar", true)
  readonly property bool attached: str("notifyAttach", "auto") === "attached" || (str("notifyAttach", "auto") === "auto" && drawer)
  readonly property string corner: str("notifyCorner", "top-right")
  readonly property string cards: str("notifyCards", "flat")
  readonly property color fill: follow ? Color.bar.background : t.resolveColor(str("notifyBackground", "background"))
  readonly property real alpha: follow ? 0.94 : num("notifyAlpha", 0.94)
  readonly property int count: { var m = num("notifyMax", 0); return m > 0 ? Math.min(m, 3) : 3 }
  readonly property var samples: [
    { icon: "󰍡", title: "Telegram", body: t.tr("New message") },
    { icon: "󰂄", title: t.tr("Battery"), body: "82 %" },
    { icon: "󰈹", title: "Firefox", body: t.tr("Download finished") }
  ]

  MiniScreen {
    id: screen
    anchors.fill: parent
    t: np.t
    wallpaper: np.wallpaper

    Rectangle {
      id: panel
      readonly property real k: screen.k
      readonly property real gap: np.attached ? 0 : 12 * k
      width: np.num("notifyWidth", 380) * k
      height: col.implicitHeight + (np.drawer ? 20 * k : 0)
      x: np.corner === "top-left" ? gap : np.corner === "top-center" ? (parent.width - width) / 2 : parent.width - width - gap
      y: screen.barHeight + (np.attached ? 0 : 10 * k)
      radius: np.num("notifyRadius", 18) * k
      color: np.drawer ? Util.alpha(np.fill, np.alpha) : "transparent"

      Column {
        id: col
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: np.drawer ? 10 * panel.k : 0 }
        spacing: 8 * panel.k
        Repeater {
          model: np.count
          Rectangle {
            required property int index
            readonly property var s: np.samples[index]
            width: col.width
            height: 62 * panel.k
            radius: Math.max(2, (np.num("notifyRadius", 18) - (np.drawer ? 6 : 0)) * panel.k)
            color: np.drawer ? (np.cards === "flat" ? Util.alpha(np.t.foreground, 0.06) : "transparent") : Util.alpha(np.fill, np.alpha)
            border.width: np.cards === "flat" ? 0 : 1
            border.color: np.cards === "dotmatrix" ? np.t.primary : Util.alpha(np.t.foreground, 0.25)
            Row {
              anchors.left: parent.left
              anchors.leftMargin: 12 * panel.k
              anchors.verticalCenter: parent.verticalCenter
              spacing: 10 * panel.k
              Text { text: s.icon; color: np.t.primary; font.family: np.t.iconFont; font.pixelSize: Math.max(8, 20 * panel.k); anchors.verticalCenter: parent.verticalCenter }
              Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2 * panel.k
                Text { text: s.title; color: np.t.foreground; font.family: np.cards === "dotmatrix" ? np.t.headFont : np.t.fontFamily; font.pixelSize: Math.max(7, 13 * panel.k); font.bold: true }
                Text { text: s.body; color: np.t.muted; font.family: np.t.fontFamily; font.pixelSize: Math.max(6, 11 * panel.k) }
              }
            }
          }
        }
      }
    }
  }
}
