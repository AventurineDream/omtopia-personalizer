import QtQuick
import Quickshell.Widgets
import qs.Commons

// Мини-экран для превью: обои текущей темы, полоска бара сверху, пропорции 16:10, по центру
// родителя. k — масштаб «логический пиксель экрана 1440 px → пиксель превью»: сцены задают
// размеры в логических пикселях и умножают на k. Дети кладутся поверх обоев.
Item {
  id: mini
  property var t
  property string wallpaper: ""       // file:// URL
  property bool bar: true
  property real dim: 0                // затемнить обои (0…1) — например, для Glyph
  default property alias content: layer.data
  readonly property real k: screen.width / 1440
  readonly property real barHeight: bar ? Math.max(6, screen.height * 0.045) : 0

  ClippingRectangle {
    id: screen
    anchors.centerIn: parent
    width: Math.min(parent.width, parent.height * 1.6)
    height: width / 1.6
    radius: mini.t.innerRadius
    color: mini.t.surfaceLow

    Image {
      anchors.fill: parent
      source: mini.wallpaper
      fillMode: Image.PreserveAspectCrop
      asynchronous: true
      sourceSize.width: 720
    }
    Rectangle { anchors.fill: parent; color: "#000000"; opacity: mini.dim; visible: mini.dim > 0 }
    Rectangle {
      visible: mini.bar
      width: parent.width
      height: mini.barHeight
      color: Color.bar.background
    }
    Item {
      id: layer
      anchors.fill: parent
    }
  }
}
