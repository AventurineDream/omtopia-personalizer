import QtQuick
import qs.Commons

// Шейдер экрана: мини-стол (обои + окна) через Qt-вариант шейдера из previews/shaders/screen
// (их делает scripts/build-preview-shaders.py). time крутится только у шейдеров, где он есть,
// и только пока сцена видна. off / нет шейдера — стол как есть.
Item {
  id: shp
  property var t
  property string shader: ""          // имя файла без .frag; "" или off — без шейдера
  property string wallpaper: ""
  property real screenWidth: 1440
  property real screenHeight: 900
  readonly property bool active: shader !== "" && shader !== "off"
  readonly property bool animated: shader === "crt-animated"

  ScreenMock {
    id: screen
    anchors.fill: parent
    t: shp.t
    screenWidth: shp.screenWidth
    screenHeight: shp.screenHeight
    wallpaper: shp.wallpaper

    WindowsMock {
      anchors.fill: parent
      t: shp.t
      gapsIn: 10; gapsOut: 20; border: 2; rounding: 12
    }
  }

  // Шейдер — на всю «сцену» экрана: layer.effect получает её картинку в sampler tex.
  Binding { target: screen.scene; property: "layer.enabled"; value: shp.active }
  Binding { target: screen.scene; property: "layer.samplerName"; value: "tex" }
  Binding {
    target: screen.scene
    property: "layer.effect"
    value: shp.active ? effect : null
  }
  Component {
    id: effect
    ShaderEffect {
      property size fullSize: Qt.size(shp.screenWidth * 2, shp.screenHeight * 2)
      property real time: 0
      fragmentShader: Qt.resolvedUrl("shaders/screen/" + shp.shader + ".frag.qsb")
      NumberAnimation on time {
        running: shp.animated && shp.visible
        from: 0; to: 600; duration: 600000; loops: Animation.Infinite
      }
    }
  }
}
