import QtQuick
import Quickshell.Widgets
import qs.Commons

// Плитка галереи (темы, обои, Recolor, Dotify, экраны блокировки): миниатюра из кэша
// (thumbs, md5 пути) с откатом на сам файл, подпись, галочка у текущей, точки палитры у тем.
Rectangle {
  id: tile
  property var t
  property int index: -1
  property string label: ""
  property string preview: ""
  property string note: ""
  property bool current: false
  property bool selected: false
  property bool focused: false
  property var palette: []
  property string icon: "󰋩"
  signal activated()
  signal hoverAt(point p)

  radius: t.rCard
  color: selected && focused ? t.surfaceSelected : (hover.containsMouse ? t.surfaceHi : t.surface)
  border.width: selected ? (focused ? Style.space(2) : 1) : (current ? 1 : (t.dot ? 1 : 0))
  border.color: selected ? Util.alpha(t.primary, focused ? 0.9 : 0.4) : (current ? Util.alpha(t.primary, 0.5) : t.outline)
  Behavior on color { ColorAnimation { duration: tile.t.ms(120) } }
  scale: selected && focused ? 1.0 : (hover.containsMouse ? 0.985 : 0.97)
  Behavior on scale { NumberAnimation { duration: tile.t.ms(160); easing.type: Easing.OutCubic } }

  ClippingRectangle {
    id: thumb
    anchors { top: parent.top; left: parent.left; right: parent.right; margins: Style.space(6) }
    height: parent.height - caption.height - Style.space(12)
    radius: Math.max(2, tile.t.rCard - Style.space(4))
    color: tile.t.surfaceLow

    Image {
      id: img
      property bool fallback: false
      anchors.fill: parent
      source: !tile.preview ? "" : fallback ? tile.t.fileUrl(tile.preview) : tile.t.thumbUrl(tile.preview)
      onStatusChanged: if (status === Image.Error && !fallback) fallback = true
      Connections {
        target: tile.t
        function onThumbVersionChanged() { img.fallback = false }
      }
      sourceSize.width: Math.max(1, thumb.width * 1.5)
      sourceSize.height: Math.max(1, thumb.height * 1.5)
      fillMode: Image.PreserveAspectCrop
      asynchronous: true
      opacity: status === Image.Ready ? 1 : 0
      Behavior on opacity { NumberAnimation { duration: tile.t.ms(180) } }
    }
    Text {
      anchors.centerIn: parent
      visible: !tile.preview
      text: tile.icon
      color: tile.t.primary
      font.family: tile.t.iconFont
      font.pixelSize: Style.font.displayLarge
    }

    // Палитра темы полоской по нижнему краю.
    Row {
      visible: tile.palette.length > 0
      anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
      height: Style.space(8)
      Repeater {
        model: tile.palette
        delegate: Rectangle {
          required property string modelData
          width: thumb.width / Math.max(1, tile.palette.length)
          height: parent.height
          color: modelData
        }
      }
    }

    Rectangle {
      visible: tile.current
      anchors { top: parent.top; right: parent.right; margins: Style.space(6) }
      width: Style.space(24); height: width
      radius: tile.t.dot ? Style.space(3) : width / 2
      color: tile.t.primary
      Text {
        anchors.centerIn: parent
        text: "󰄬"
        color: tile.t.inkOnPrimary
        font.family: tile.t.iconFont
        font.pixelSize: Style.font.body
      }
    }
  }

  Text {
    id: caption
    anchors { bottom: parent.bottom; left: parent.left; right: parent.right; margins: Style.space(6) }
    leftPadding: Style.space(4)
    rightPadding: Style.space(4)
    height: Style.font.bodySmall + Style.space(10)
    verticalAlignment: Text.AlignVCenter
    horizontalAlignment: Text.AlignHCenter
    text: tile.label
    elide: Text.ElideMiddle
    textFormat: Text.PlainText
    color: tile.current ? tile.t.primary : tile.t.foreground
    font.family: tile.t.fontFamily
    font.pixelSize: Style.font.bodySmall
    font.bold: tile.current || tile.selected
  }

  MouseArea {
    id: hover
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: tile.activated()
    onPositionChanged: function(mouse) { tile.hoverAt(mapToItem(null, mouse.x, mouse.y)) }
  }
}
