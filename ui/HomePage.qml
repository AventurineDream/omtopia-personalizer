import QtQuick
import Quickshell.Widgets
import qs.Commons

// Домашняя страница: приветствие на текущих обоях, карточки «что сейчас стоит»
// (клик / ⏎ — открыть категорию) и быстрые действия. Выделение общее с клавиатурой:
// selectedIndex идёт по карточкам, потом по действиям; columns нужен для j/k.
Flickable {
  id: home
  property var t
  property var cards: []      // [{ key, icon, title, value, category }]
  property var actions: []    // [{ id, icon, title, hint }]
  property string wallpaper: ""
  property var palette: []
  property int selectedIndex: 0
  property bool focused: false
  signal openCard(int index)

  readonly property int columns: Math.max(2, Math.floor((width + Style.space(12)) / (Style.space(250) + Style.space(12))))
  readonly property real cellWidth: (width - (columns - 1) * Style.space(12)) / columns

  contentHeight: col.implicitHeight + Style.space(12)
  boundsBehavior: Flickable.StopAtBounds
  clip: true

  function ensureVisible(item) {
    if (!item) return
    var p = item.mapToItem(col, 0, 0)
    if (p.y < contentY) contentY = Math.max(0, p.y - Style.space(8))
    else if (p.y + item.height > contentY + height) contentY = p.y + item.height - height + Style.space(8)
  }
  onSelectedIndexChanged: Qt.callLater(function() {
    var n = home.cards.length
    home.ensureVisible(home.selectedIndex < n ? cardRep.itemAt(home.selectedIndex) : actionRep.itemAt(home.selectedIndex - n))
  })

  Column {
    id: col
    width: home.width
    spacing: Style.space(18)

    // ── Приветствие на обоях ──
    ClippingRectangle {
      width: parent.width
      height: Style.space(170)
      radius: home.t.rCard
      color: home.t.surface
      Image {
        anchors.fill: parent
        source: home.wallpaper
        sourceSize.width: Math.max(1, width)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
      }
      Rectangle {
        anchors.fill: parent
        gradient: Gradient {
          orientation: Gradient.Horizontal
          GradientStop { position: 0; color: Util.alpha(home.t.background, 0.88) }
          GradientStop { position: 0.6; color: Util.alpha(home.t.background, 0.35) }
          GradientStop { position: 1; color: "transparent" }
        }
      }
      Column {
        anchors.left: parent.left
        anchors.leftMargin: Style.space(26)
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(6)
        Text {
          text: home.t.greeting()
          color: home.t.foreground
          font.family: home.t.headFont
          font.pixelSize: Style.font.display
          font.bold: true
        }
        Text {
          text: Qt.formatDate(new Date(), "dddd, d MMMM")
          color: home.t.muted
          font.family: home.t.fontFamily
          font.pixelSize: Style.font.body
        }
        Row {
          visible: home.palette.length > 0
          topPadding: Style.space(6)
          spacing: Style.space(5)
          Repeater {
            model: home.palette
            delegate: Rectangle {
              required property string modelData
              width: Style.space(16); height: width
              radius: home.t.dot ? Style.space(2) : width / 2
              color: modelData
              border.width: 1
              border.color: Util.alpha(home.t.foreground, 0.25)
            }
          }
        }
      }
    }

    Text {
      text: home.t.tr("In use now")
      color: home.t.foreground
      font.family: home.t.headFont
      font.pixelSize: Style.font.heading
      font.bold: true
    }

    Grid {
      columns: home.columns
      columnSpacing: Style.space(12)
      rowSpacing: Style.space(12)
      Repeater {
        id: cardRep
        model: home.cards
        delegate: Rectangle {
          id: card
          required property int index
          required property var modelData
          readonly property bool selected: index === home.selectedIndex
          width: home.cellWidth
          height: Style.space(72)
          radius: home.t.rCard
          color: selected && home.focused ? home.t.surfaceSelected : (hover.containsMouse ? home.t.surfaceHi : home.t.surface)
          border.width: selected ? (home.focused ? Style.space(2) : 1) : (home.t.dot ? 1 : 0)
          border.color: selected ? Util.alpha(home.t.primary, home.focused ? 0.9 : 0.4) : home.t.outline
          Behavior on color { ColorAnimation { duration: home.t.ms(120) } }

          Rectangle {
            id: badge
            anchors.left: parent.left
            anchors.leftMargin: Style.space(14)
            anchors.verticalCenter: parent.verticalCenter
            width: Style.space(40); height: width
            radius: home.t.dot ? Style.space(3) : width / 2
            color: home.t.secondaryContainer
            Text {
              anchors.centerIn: parent
              text: card.modelData.icon
              color: home.t.inkOnContainer
              font.family: home.t.iconFont
              font.pixelSize: Style.font.title
            }
          }
          Column {
            anchors.left: badge.right
            anchors.leftMargin: Style.space(12)
            anchors.right: parent.right
            anchors.rightMargin: Style.space(12)
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(2)
            Text {
              width: parent.width
              text: card.modelData.title
              elide: Text.ElideRight
              color: home.t.muted
              font.family: home.t.fontFamily
              font.pixelSize: Style.font.caption
            }
            Text {
              width: parent.width
              text: card.modelData.value
              elide: Text.ElideRight
              textFormat: Text.PlainText
              color: home.t.foreground
              font.family: home.t.fontFamily
              font.pixelSize: Style.font.title
              font.bold: true
            }
          }
          MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: home.openCard(card.index)
          }
        }
      }
    }

    Text {
      visible: home.actions.length > 0
      text: home.t.tr("Quick actions")
      color: home.t.foreground
      font.family: home.t.headFont
      font.pixelSize: Style.font.heading
      font.bold: true
    }

    Grid {
      columns: home.columns
      columnSpacing: Style.space(12)
      rowSpacing: Style.space(12)
      Repeater {
        id: actionRep
        model: home.actions
        delegate: Rectangle {
          id: act
          required property int index
          required property var modelData
          readonly property int flat: home.cards.length + index
          readonly property bool selected: flat === home.selectedIndex
          width: home.cellWidth
          height: Style.space(56)
          radius: home.t.dot ? Style.space(3) : height / 2
          color: selected && home.focused ? home.t.primary : (actHover.containsMouse ? home.t.secondaryContainer : home.t.surfaceLow)
          border.width: home.t.dot ? 1 : 0
          border.color: home.t.outline
          Behavior on color { ColorAnimation { duration: home.t.ms(120) } }
          Row {
            anchors.centerIn: parent
            spacing: Style.space(10)
            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: act.modelData.icon
              color: act.selected && home.focused ? home.t.inkOnPrimary : home.t.primary
              font.family: home.t.iconFont
              font.pixelSize: Style.font.title
            }
            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: act.modelData.title
              color: act.selected && home.focused ? home.t.inkOnPrimary : home.t.foreground
              font.family: home.t.fontFamily
              font.pixelSize: Style.font.body
              font.bold: true
            }
          }
          MouseArea {
            id: actHover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: home.openCard(act.flat)
          }
        }
      }
    }
  }
}
