import QtQuick
import qs.Commons

// Вкладки под заголовком (категории группы): подпись, под активной скользит полоска.
// items — [{ icon, title }], picked(index) — индекс в items.
Item {
  id: strip
  property var t
  property var items: []
  property int currentIndex: 0
  signal picked(int index)

  implicitHeight: Style.space(44)

  Rectangle {
    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
    height: 1
    color: strip.t.outline
  }

  Flickable {
    id: flick
    anchors.fill: parent
    contentWidth: row.implicitWidth
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.HorizontalFlick
    clip: true

    Row {
      id: row
      height: parent.height
      spacing: Style.space(4)
      Repeater {
        id: rep
        model: strip.items
        delegate: Item {
          id: tab
          required property int index
          required property var modelData
          readonly property bool active: index === strip.currentIndex
          width: label.implicitWidth + Style.space(28)
          height: row.height
          onActiveChanged: if (active) Qt.callLater(function() {
            // Вкладку могли уже удалить (смена группы) — тогда id недоступны.
            if (typeof flick === "undefined" || !flick || !tab) return
            if (tab.x < flick.contentX) flick.contentX = tab.x
            else if (tab.x + tab.width > flick.contentX + flick.width) flick.contentX = tab.x + tab.width - flick.width
          })

          Rectangle {
            anchors.fill: parent
            anchors.bottomMargin: Style.space(4)
            radius: strip.t.rSmall
            color: hover.containsMouse && !tab.active ? strip.t.surfaceHi : "transparent"
          }
          Row {
            id: label
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -Style.space(2)
            spacing: Style.space(7)
            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: tab.modelData.icon
              color: tab.active ? strip.t.primary : strip.t.muted
              font.family: strip.t.iconFont
              font.pixelSize: Style.font.body
            }
            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: tab.modelData.title
              color: tab.active ? strip.t.primary : strip.t.foreground
              font.family: strip.t.headFont
              font.pixelSize: Style.font.body
              font.bold: tab.active
            }
          }
          MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: strip.picked(tab.index)
          }
        }
      }

      // Полоска под активной вкладкой.
    }
    Rectangle {
      readonly property Item target: rep.count > 0 && strip.currentIndex >= 0 ? rep.itemAt(strip.currentIndex) : null
      visible: target !== null
      x: target ? target.x + Style.space(10) : 0
      width: target ? target.width - Style.space(20) : 0
      y: flick.height - height
      height: Style.space(3)
      radius: strip.t.dot ? 0 : height / 2
      color: strip.t.primary
      Behavior on x { NumberAnimation { duration: strip.t.ms(220); easing.type: Easing.OutCubic } }
      Behavior on width { NumberAnimation { duration: strip.t.ms(220); easing.type: Easing.OutCubic } }
    }
  }
}
