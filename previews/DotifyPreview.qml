import QtQuick
import Quickshell.Widgets
import qs.Commons

// Dotify: LED-матрица с текущими настройками (шаг, гамма, уровень выключенных диодов, цвета),
// посчитанная шейдером previews/shaders/dotify.frag — тот же рисунок, что scripts/dotify.py.
// Масштаб 1:1 (логические пиксели экрана): видно настоящий размер точек; показан центр картинки.
// Рисуется один раз и перерисовывается только при смене параметра или картинки.
Item {
  id: dp
  property var t
  property var v: ({})               // значения настроек категории (key -> raw)
  property string source: ""         // file:// URL картинки
  property real screenWidth: 1440
  property real screenHeight: 900

  function num(key, def) { var x = Number(v[key]); return v[key] === undefined || !isFinite(x) ? def : x }

  ClippingRectangle {
    anchors.fill: parent
    radius: dp.t.rCard
    color: shader.background

    // Картинка в размер экрана (как cover() в dotify.py), центр — в середине превью.
    Image {
      id: img
      width: dp.screenWidth
      height: dp.screenHeight
      x: (parent.width - width) / 2
      y: (parent.height - height) / 2
      source: dp.source
      fillMode: Image.PreserveAspectCrop
      sourceSize.width: dp.screenWidth
      asynchronous: true
      visible: false
    }

    ShaderEffect {
      id: shader
      x: img.x
      y: img.y
      width: img.width
      height: img.height
      visible: img.status === Image.Ready
      property variant source: img
      property size size: Qt.size(width, height)
      property real pitch: Math.max(3, dp.num("dotPitch", 9))
      property real gamma: Math.max(0.1, dp.num("dotGamma", 1.25))
      property real offLevel: dp.num("dotOff", 0.07)
      property color tint: dp.t.resolveColor(dp.v.dotTint || "foreground")
      property color background: dp.t.resolveColor(dp.v.dotBackground || "background")
      fragmentShader: Qt.resolvedUrl("shaders/dotify.frag.qsb")
    }

    Text {
      anchors.centerIn: parent
      visible: !dp.source || img.status === Image.Error
      text: dp.t.tr("No picture to preview")
      color: dp.t.muted
      font.family: dp.t.fontFamily
      font.pixelSize: Style.font.body
    }

    Rectangle {
      anchors { left: parent.left; bottom: parent.bottom; margins: Style.space(10) }
      height: Style.space(24)
      width: scaleText.implicitWidth + Style.space(16)
      radius: dp.t.dot ? Style.space(3) : height / 2
      color: Util.alpha(dp.t.background, 0.8)
      Text {
        id: scaleText
        anchors.centerIn: parent
        text: "1:1 · " + dp.t.tr("pitch") + " " + shader.pitch + " px"
        color: dp.t.foreground
        font.family: dp.t.fontFamily
        font.pixelSize: Style.font.caption
      }
    }
  }
}
