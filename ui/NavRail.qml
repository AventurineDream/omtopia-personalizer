import QtQuick
import qs.Commons

// Рейл навигации Material 3: логотип сверху, под ним пункты «иконка в пилюле + подпись».
// items — [{ icon, title }], 0 — Домой, дальше группы. focused — фокус клавиатуры на рейле.
Item {
  id: rail
  property var t
  property var items: []
  property int currentIndex: 0
  property bool focused: false
  signal picked(int index)

  implicitWidth: Style.space(92)

  Rectangle {
    id: logo
    anchors.horizontalCenter: parent.horizontalCenter
    y: Style.space(4)
    width: Style.space(52); height: width
    radius: rail.t.dot ? Style.space(4) : width / 2
    gradient: Gradient {
      orientation: Gradient.Vertical
      GradientStop { position: 0; color: Util.alpha(rail.t.primary, 0.95) }
      GradientStop { position: 1; color: Util.alpha(rail.t.primary, 0.55) }
    }
    Text {
      anchors.centerIn: parent
      text: "󰸌"
      color: rail.t.inkOnPrimary
      font.family: rail.t.iconFont
      font.pixelSize: Math.round(parent.height * 0.5)
    }
  }

  Flickable {
    anchors { top: logo.bottom; topMargin: Style.space(18); bottom: parent.bottom; left: parent.left; right: parent.right }
    contentHeight: col.implicitHeight
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    Column {
      id: col
      width: parent.width
      spacing: Style.space(6)

      Repeater {
        model: rail.items
        delegate: Item {
          id: item
          required property int index
          required property var modelData
          readonly property bool active: index === rail.currentIndex
          width: col.width
          height: Style.space(58)

          Rectangle {
            id: indicator
            anchors.horizontalCenter: parent.horizontalCenter
            y: Style.space(2)
            height: Style.space(32)
            width: item.active || hover.containsMouse ? Style.space(56) : Style.space(32)
            radius: rail.t.dot ? Style.space(3) : height / 2
            color: item.active ? rail.t.secondaryContainer : (hover.containsMouse ? rail.t.surfaceHi : "transparent")
            border.width: item.active && rail.focused ? Style.space(2) : 0
            border.color: rail.t.primary
            Behavior on width { NumberAnimation { duration: rail.t.ms(200); easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: rail.t.ms(140) } }
            Text {
              anchors.centerIn: parent
              text: item.modelData.icon
              color: item.active ? rail.t.inkOnContainer : rail.t.muted
              font.family: rail.t.iconFont
              font.pixelSize: Style.font.iconLarge
            }
          }
          Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: indicator.bottom
            anchors.topMargin: Style.space(4)
            width: parent.width - Style.space(6)
            horizontalAlignment: Text.AlignHCenter
            text: item.modelData.title
            elide: Text.ElideRight
            color: item.active ? rail.t.foreground : rail.t.muted
            font.family: rail.t.headFont
            font.pixelSize: Style.font.caption
            font.bold: item.active
          }
          MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: rail.picked(item.index)
          }
        }
      }
    }
  }
}
