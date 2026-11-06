import QtQuick
import qs.Commons

// Переключатель в духе Material 3: дорожка-пилюля, бегунок растёт во включённом
// состоянии и несёт галочку. В стиле DOT-MATRIX — квадратная рамка и «лампочка».
// t — токены оформления (Customizer.qml), клик отдаёт toggled().
Item {
  id: sw
  property var t
  property bool checked: false
  property bool enabled: true
  signal toggled()

  implicitWidth: Style.space(52)
  implicitHeight: Style.space(32)
  opacity: enabled ? 1 : 0.45

  Rectangle {
    id: track
    anchors.fill: parent
    radius: sw.t.dot ? Style.space(3) : height / 2
    color: sw.checked ? sw.t.primary : sw.t.surfaceHi
    border.width: sw.checked ? 0 : Style.space(2)
    border.color: sw.t.outlineStrong
    Behavior on color { ColorAnimation { duration: sw.t.ms(160) } }
  }

  Rectangle {
    id: thumb
    readonly property real size: sw.checked ? sw.height - Style.space(8) : sw.height - Style.space(16)
    width: size
    height: size
    radius: sw.t.dot ? Style.space(2) : size / 2
    anchors.verticalCenter: parent.verticalCenter
    x: sw.checked ? sw.width - size - Style.space(4) : Style.space(8)
    color: sw.checked ? sw.t.inkOnPrimary : sw.t.outlineStrong
    Behavior on x { NumberAnimation { duration: sw.t.ms(200); easing.type: Easing.OutBack; easing.overshoot: 1.4 } }
    Behavior on width { NumberAnimation { duration: sw.t.ms(160) } }
    Behavior on height { NumberAnimation { duration: sw.t.ms(160) } }

    Text {
      anchors.centerIn: parent
      visible: sw.checked && !sw.t.dot
      text: "󰄬"
      color: sw.t.primary
      font.family: sw.t.iconFont
      font.pixelSize: Math.round(parent.height * 0.62)
    }
  }

  MouseArea {
    anchors.fill: parent
    enabled: sw.enabled
    cursorShape: Qt.PointingHandCursor
    onClicked: sw.toggled()
  }
}
