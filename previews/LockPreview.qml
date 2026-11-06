import QtQuick
import Quickshell.Widgets
import qs.Commons

// Lock Tweaks: снимок текущего дизайна экрана блокировки (кэш ~/.cache/omarchy-customizer/lock)
// и чипы с тем, что меняют твики. Сам снимок снят до правки — точный вид даёт p (показать вживую).
Item {
  id: lp
  property var t
  property var v: ({})
  property string image: ""          // file:// URL снимка дизайна
  property string design: ""

  function num(key, def) { var x = Number(v[key]); return v[key] === undefined || !isFinite(x) ? def : x }
  function on(key, def) { return v[key] === undefined ? def : String(v[key]) === "true" }
  readonly property string clock: {
    var d = new Date()
    var fmt = lp.on("clock24", true) ? "HH:mm" : "h:mm AP"
    if (lp.on("showSeconds", false)) fmt = fmt.replace("mm", "mm:ss")
    return Qt.formatTime(d, fmt)
  }

  ClippingRectangle {
    id: shot
    anchors.centerIn: parent
    width: Math.min(parent.width, parent.height * 1.6)
    height: width / 1.6
    radius: lp.t.innerRadius
    color: lp.t.surfaceLow
    Image {
      id: img
      anchors.fill: parent
      source: lp.image
      fillMode: Image.PreserveAspectCrop
      asynchronous: true
      sourceSize.width: 900
    }
    Text {
      anchors.centerIn: parent
      width: parent.width * 0.8
      visible: img.status !== Image.Ready
      horizontalAlignment: Text.AlignHCenter
      wrapMode: Text.Wrap
      text: lp.t.tr("No preview yet — T captures the missing ones, p shows the design live.")
      color: lp.t.muted
      font.family: lp.t.fontFamily
      font.pixelSize: Style.font.body
    }
  }

  // Что задают твики — чипами под снимком.
  Flow {
    anchors { left: shot.left; right: shot.right; bottom: shot.bottom; margins: Style.space(10) }
    spacing: Style.space(6)
    Repeater {
      model: [
        "󰥔 " + lp.clock,
        (lp.on("showDate", true) ? "󰃭 " : "󰃮 ") + lp.t.tr("Date"),
        "󰂵 " + lp.t.tr("blur") + " " + lp.num("wallpaperBlur", 1),
        "󰖨 " + lp.t.tr("dim") + " " + lp.num("wallpaperDim", 0),
        lp.on("reduceMotion", false) ? "󰒲 " + lp.t.tr("Reduce motion") : "",
        "p — " + lp.t.tr("show live")
      ].filter(function(s) { return s !== "" })
      Rectangle {
        required property string modelData
        height: Style.space(24)
        width: chip.implicitWidth + Style.space(16)
        radius: lp.t.dot ? Style.space(3) : height / 2
        color: Util.alpha(lp.t.background, 0.82)
        Text {
          id: chip
          anchors.centerIn: parent
          text: modelData
          color: lp.t.foreground
          font.family: lp.t.fontFamily
          font.pixelSize: Style.font.caption
        }
      }
    }
  }
}
