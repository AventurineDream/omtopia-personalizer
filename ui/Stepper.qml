import QtQuick
import qs.Commons

// «‹ значение ›»: для длинных списков (enum, роли цвета, шрифты), которые не влезают
// в сегменты. Стрелки отдают stepped(-1 | 1), клик по значению — clicked().
// swatch — кружок цвета перед значением (строки-цвета).
Rectangle {
  id: st
  property var t
  property string text: ""
  property bool enabled: true
  property bool arrows: true
  property color swatch: "transparent"
  property bool hasSwatch: false
  signal stepped(int dir)
  signal clicked()

  height: Style.space(36)
  width: row.implicitWidth + Style.space(8)
  radius: t.dot ? Style.space(3) : height / 2
  color: t.surfaceLow
  border.width: t.dot ? 1 : 0
  border.color: t.outline
  opacity: enabled ? 1 : 0.45

  // Inline component не видит id файла — хозяина передаём явно (host: st).
  component Arrow: Rectangle {
    id: arrow
    property var host
    property string glyph: ""
    property int dir: 1
    width: Style.space(28); height: width
    radius: arrow.host.t.dot ? Style.space(2) : width / 2
    color: arrowHover.containsMouse ? arrow.host.t.secondaryContainer : "transparent"
    anchors.verticalCenter: parent.verticalCenter
    Text {
      anchors.centerIn: parent
      text: arrow.glyph
      color: arrow.host.t.foreground
      font.family: arrow.host.t.iconFont
      font.pixelSize: Style.font.title
    }
    MouseArea {
      id: arrowHover
      anchors.fill: parent
      enabled: arrow.host.enabled
      hoverEnabled: true
      cursorShape: Qt.PointingHandCursor
      onClicked: arrow.host.stepped(arrow.dir)
    }
  }

  Row {
    id: row
    anchors.centerIn: parent
    spacing: Style.space(4)
    Arrow { host: st; visible: st.arrows; glyph: "󰅁"; dir: -1 }
    Item {
      width: valueRow.implicitWidth + Style.space(12)
      height: st.height
      Row {
        id: valueRow
        anchors.centerIn: parent
        spacing: Style.space(8)
        Rectangle {
          visible: st.hasSwatch
          anchors.verticalCenter: parent.verticalCenter
          width: Style.space(18); height: width
          radius: st.t.dot ? Style.space(2) : width / 2
          color: st.swatch
          border.width: 1
          border.color: st.t.outlineStrong
        }
        Text {
          anchors.verticalCenter: parent.verticalCenter
          text: st.text
          width: Math.min(implicitWidth, Style.space(220))
          elide: Text.ElideMiddle
          color: st.t.foreground
          font.family: st.t.fontFamily
          font.pixelSize: Style.font.body
        }
      }
      MouseArea {
        anchors.fill: parent
        enabled: st.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: st.clicked()
      }
    }
    Arrow { host: st; visible: st.arrows; glyph: "󰅂"; dir: 1 }
  }
}
