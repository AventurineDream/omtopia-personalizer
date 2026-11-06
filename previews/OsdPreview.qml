import QtQuick
import qs.Commons

// OSD: полоска громкости на мини-экране по настройкам osd.json — стиль (edge / dotmatrix / stock),
// край и положение вдоль него, размер, фон и прозрачность (или «как у бара»), скругление, процент.
// edge/dotmatrix — вертикальная панель у края (attached — вплотную, floating — с отступом);
// stock — горизонтальная плашка внизу по центру, как у стокового OSD Omarchy.
Item {
  id: op
  property var t
  property var v: ({})
  property string wallpaper: ""

  function str(key, def) { return v[key] !== undefined && v[key] !== "" ? String(v[key]) : def }
  function num(key, def) { var x = Number(v[key]); return v[key] === undefined || !isFinite(x) ? def : x }
  function on(key, def) { return v[key] === undefined ? def : String(v[key]) === "true" }

  readonly property string style: str("osdStyle", "edge")
  readonly property bool follow: on("osdFollowBar", true)
  readonly property bool attached: str("osdAttach", "auto") === "attached"
    || (str("osdAttach", "auto") === "auto" && style !== "stock")
  readonly property real sizeK: str("osdSize", "normal") === "compact" ? 0.75 : str("osdSize", "normal") === "large" ? 1.3 : 1
  readonly property color fill: follow ? Color.bar.background : t.resolveColor(str("osdBackground", "background"))
  readonly property real alpha: follow ? 0.94 : num("osdAlpha", 0.94)
  readonly property real level: 0.62

  MiniScreen {
    id: screen
    anchors.fill: parent
    t: op.t
    wallpaper: op.wallpaper

    // edge / dotmatrix: вертикальная панель у края
    Rectangle {
      visible: op.style !== "stock"
      readonly property real k: screen.k
      width: 46 * op.sizeK * k
      height: 240 * op.sizeK * k
      x: op.str("osdSide", "right") === "left" ? (op.attached ? 0 : 12 * k) : parent.width - width - (op.attached ? 0 : 12 * k)
      y: op.str("osdAlign", "center") === "top" ? screen.barHeight + 16 * k
        : op.str("osdAlign", "center") === "bottom" ? parent.height - height - 16 * k
        : (parent.height - height) / 2
      radius: Math.min(width / 2, op.num("osdRadius", 18) * k)
      color: Util.alpha(op.fill, op.alpha)
      border.width: op.style === "dotmatrix" ? 1 : 0
      border.color: op.t.outline

      Text {
        anchors.top: parent.top
        anchors.topMargin: 8 * parent.k
        anchors.horizontalCenter: parent.horizontalCenter
        text: "󰕾"
        color: op.t.foreground
        font.family: op.t.iconFont
        font.pixelSize: Math.max(8, 16 * parent.k * op.sizeK)
      }
      // Шкала: сплошная (edge) или из точек (dotmatrix).
      Item {
        id: track
        anchors { top: parent.top; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
        anchors.topMargin: 34 * parent.k * op.sizeK
        anchors.bottomMargin: (op.on("osdShowValue", true) ? 30 : 12) * parent.k * op.sizeK
        width: 8 * parent.k * op.sizeK
        Rectangle {
          visible: op.style !== "dotmatrix"
          anchors.fill: parent
          radius: width / 2
          color: Util.alpha(op.t.foreground, 0.18)
          Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: parent.height * op.level
            radius: width / 2
            color: op.t.primary
          }
        }
        Column {
          visible: op.style === "dotmatrix"
          anchors.fill: parent
          spacing: Math.max(1, 3 * screen.k)
          readonly property int n: Math.max(4, Math.floor(height / (width + spacing)))
          Repeater {
            model: parent.n
            Rectangle {
              required property int index
              width: track.width; height: width; radius: width / 2
              color: (parent.n - index) / parent.n <= op.level ? op.t.primary : Util.alpha(op.t.foreground, 0.15)
            }
          }
        }
      }
      Text {
        visible: op.on("osdShowValue", true)
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8 * parent.k
        anchors.horizontalCenter: parent.horizontalCenter
        text: Math.round(op.level * 100)
        color: op.t.foreground
        font.family: op.t.fontFamily
        font.pixelSize: Math.max(7, 12 * parent.k * op.sizeK)
      }
    }

    // stock: горизонтальная плашка внизу по центру
    Rectangle {
      visible: op.style === "stock"
      readonly property real k: screen.k
      width: 300 * op.sizeK * k
      height: 52 * op.sizeK * k
      x: (parent.width - width) / 2
      y: parent.height - height - 60 * k
      radius: Math.min(height / 2, op.num("osdRadius", 18) * k)
      color: Util.alpha(op.fill, op.alpha)
      Row {
        anchors.centerIn: parent
        spacing: 12 * parent.k
        Text { text: "󰕾"; color: op.t.foreground; font.family: op.t.iconFont; font.pixelSize: Math.max(8, 18 * screen.k * op.sizeK); anchors.verticalCenter: parent.verticalCenter }
        Rectangle {
          anchors.verticalCenter: parent.verticalCenter
          width: 170 * screen.k * op.sizeK; height: 6 * screen.k * op.sizeK; radius: height / 2
          color: Util.alpha(op.t.foreground, 0.18)
          Rectangle { width: parent.width * op.level; height: parent.height; radius: height / 2; color: op.t.primary }
        }
        Text { visible: op.on("osdShowValue", true); text: Math.round(op.level * 100); color: op.t.foreground; font.family: op.t.fontFamily; font.pixelSize: Math.max(7, 13 * screen.k * op.sizeK); anchors.verticalCenter: parent.verticalCenter }
      }
    }
  }
}
