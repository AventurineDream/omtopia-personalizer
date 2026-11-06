import QtQuick
import qs.Commons

// Сегменты Material 3 (connected button group): отдельные пилюли, выбранная — залита
// secondaryContainer и несёт галочку. picked(value) — выбор мышью.
Row {
  id: seg
  property var t
  property var options: []
  property string value: ""
  property bool enabled: true
  signal picked(string value)

  spacing: Style.space(3)
  opacity: enabled ? 1 : 0.45

  Repeater {
    model: seg.options
    delegate: Rectangle {
      id: chip
      required property int index
      required property string modelData
      readonly property bool on: modelData === seg.value
      readonly property bool first: index === 0
      readonly property bool last: index === seg.options.length - 1
      height: Style.space(36)
      width: label.implicitWidth + (on && !seg.t.dot ? Style.space(44) : Style.space(28))
      // Края группы круглые, внутренние углы — маленькие (как у M3 connected buttons).
      radius: seg.t.dot ? Style.space(3) : (on ? height / 2 : Style.space(8))
      color: on ? seg.t.secondaryContainer : (hover.containsMouse ? seg.t.surfaceHi : seg.t.surfaceLow)
      border.width: seg.t.dot ? 1 : 0
      border.color: on ? seg.t.primary : seg.t.outline
      Behavior on color { ColorAnimation { duration: seg.t.ms(140) } }
      Behavior on width { NumberAnimation { duration: seg.t.ms(160); easing.type: Easing.OutCubic } }
      Behavior on radius { NumberAnimation { duration: seg.t.ms(160) } }

      Row {
        anchors.centerIn: parent
        spacing: Style.space(6)
        Text {
          anchors.verticalCenter: parent.verticalCenter
          visible: chip.on && !seg.t.dot
          text: "󰄬"
          color: seg.t.inkOnContainer
          font.family: seg.t.iconFont
          font.pixelSize: Style.font.body
        }
        Text {
          id: label
          anchors.verticalCenter: parent.verticalCenter
          text: chip.modelData
          color: chip.on ? seg.t.inkOnContainer : seg.t.foreground
          font.family: seg.t.fontFamily
          font.pixelSize: Style.font.body
          font.bold: chip.on
        }
      }

      MouseArea {
        id: hover
        anchors.fill: parent
        enabled: seg.enabled
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (!chip.on) seg.picked(chip.modelData)
      }
    }
  }
}
