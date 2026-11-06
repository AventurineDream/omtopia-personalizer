import QtQuick
import Quickshell.Widgets
import qs.Commons

// Экран в настоящем логическом размере (как у монитора), вписанный в карточку целиком и по центру.
// Содержимое кладётся в координатах настоящего экрана — бар, окна, шейдер выглядят как на столе,
// только уменьшенные. frame — сам экран (для layer.effect шейдера и т. п.).
Item {
  id: sm
  property var t
  property real screenWidth: 1440
  property real screenHeight: 900
  property string wallpaper: ""                 // file:// URL
  property int wallpaperAlign: Image.AlignHCenter
  default property alias content: inner.data
  property alias frame: frame
  property alias scene: scene
  readonly property real k: Math.max(0.01, Math.min(width / screenWidth, height / screenHeight))

  Item {
    id: frame
    width: sm.screenWidth
    height: sm.screenHeight
    scale: sm.k
    transformOrigin: Item.TopLeft
    x: Math.round((sm.width - width * sm.k) / 2)
    y: Math.round((sm.height - height * sm.k) / 2)

    ClippingRectangle {
      anchors.fill: parent
      radius: sm.t.innerRadius / sm.k
      color: sm.t.surfaceLow

      // scene — то, что видно на экране; шейдер вешается сюда (layer.effect).
      Item {
        id: scene
        anchors.fill: parent
        Image {
          anchors.fill: parent
          source: sm.wallpaper
          fillMode: Image.PreserveAspectCrop
          horizontalAlignment: sm.wallpaperAlign
          sourceSize.width: Math.max(1, Math.round(sm.screenWidth * sm.k * 2))
          asynchronous: true
        }
        Item {
          id: inner
          anchors.fill: parent
        }
      }
    }
  }
}
