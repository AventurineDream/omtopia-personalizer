import QtQuick
import qs.Commons

// Обычная строка категории (анимации, шрифты, звуки, скины, действия «Сохранить…»)
// карточкой: иконка, подпись, вторая строка, точки палитры, отметка «используется».
Rectangle {
  id: row
  property var t
  property int index: -1
  property string label: ""
  property string sub: ""
  property bool current: false
  property bool selected: false
  property bool focused: false
  property string icon: ""
  property var palette: []
  signal activated()
  signal hoverAt(point p)
  // Save rows (💾) in Customizer.qml: while editing, ⏎ on the row opens a name field in it, like SettingCard's
  // i editor. Enter calls submit, Esc calls cancel, typing calls edited (clears the error); focusSeq hands the
  // keyboard back to the field after a footer confirm.
  property bool editing: false
  property string editInitial: ""
  property string editError: ""
  property int focusSeq: 0
  signal submit(string text)
  signal cancel()
  signal edited()

  implicitHeight: Math.max(Style.space(58), textCol.implicitHeight + Style.space(22))
  radius: t.rCard
  color: selected && focused ? t.surfaceSelected : (hover.containsMouse ? t.surfaceHi : t.surface)
  border.width: selected ? (focused ? Style.space(2) : 1) : (t.dot ? 1 : 0)
  border.color: selected ? Util.alpha(t.primary, focused ? 0.9 : 0.4) : t.outline
  Behavior on color { ColorAnimation { duration: row.t.ms(120) } }
  // The field takes the text and the keyboard when the row opens for editing (as SettingCard does).
  onEditingChanged: if (editing) Qt.callLater(function() {
    if (!row.editing) return
    nameInput.text = row.editInitial
    nameInput.selectAll()
    nameInput.forceActiveFocus()
  })
  onFocusSeqChanged: if (editing) nameInput.forceActiveFocus()

  Rectangle {
    id: badge
    anchors.left: parent.left
    anchors.leftMargin: Style.space(12)
    anchors.verticalCenter: parent.verticalCenter
    width: Style.space(36); height: width
    radius: row.t.dot ? Style.space(3) : width / 2
    color: row.current ? row.t.primary : row.t.secondaryContainer
    Text {
      anchors.centerIn: parent
      text: row.current ? "󰄬" : row.icon
      color: row.current ? row.t.inkOnPrimary : row.t.inkOnContainer
      font.family: row.t.iconFont
      font.pixelSize: Style.font.title
    }
  }

  Column {
    id: textCol
    anchors.left: badge.right
    anchors.leftMargin: Style.space(14)
    anchors.right: pill.visible ? pill.left : parent.right
    anchors.rightMargin: Style.space(14)
    anchors.verticalCenter: parent.verticalCenter
    spacing: Style.space(3)
    Text {
      width: parent.width
      text: row.label
      wrapMode: Text.Wrap
      maximumLineCount: 2
      elide: Text.ElideRight
      textFormat: Text.PlainText
      color: row.current ? row.t.primary : row.t.foreground
      font.family: row.t.fontFamily
      font.pixelSize: Style.font.title
      font.bold: row.current || row.selected
    }
    Text {
      width: parent.width
      visible: row.sub !== ""
      text: row.sub
      wrapMode: Text.Wrap
      maximumLineCount: 2
      elide: Text.ElideRight
      textFormat: Text.PlainText
      color: row.t.muted
      font.family: row.t.fontFamily
      font.pixelSize: Style.font.bodySmall
    }

    // Name field of a save row: Enter saves, Esc cancels; the error (or the hint) stays under it.
    Rectangle {
      visible: row.editing
      width: parent.width
      height: visible ? nameInput.implicitHeight + Style.space(14) : 0
      radius: row.t.rSmall
      color: row.t.surfaceLow
      border.width: 1
      border.color: row.editError ? Color.urgent : row.t.primary
      TextInput {
        id: nameInput
        anchors.fill: parent
        anchors.margins: Style.space(7)
        verticalAlignment: TextInput.AlignVCenter
        color: row.t.foreground
        selectionColor: Util.alpha(row.t.primary, 0.4)
        font.family: row.t.fontFamily
        font.pixelSize: Style.font.body
        selectByMouse: true
        clip: true
        onTextEdited: row.edited()
        Keys.onReturnPressed: row.submit(text)
        Keys.onEnterPressed: row.submit(text)
        Keys.onEscapePressed: row.cancel()
      }
    }
    Text {
      visible: row.editing
      width: parent.width
      wrapMode: Text.Wrap
      textFormat: Text.PlainText
      text: row.editError ? "⚠ " + row.editError : row.t.tr("Enter — save · Esc — cancel")
      color: row.editError ? Color.urgent : row.t.muted
      font.family: row.t.fontFamily
      font.pixelSize: Style.font.caption
    }
    Row {
      visible: row.palette.length > 0
      spacing: Style.space(3)
      Repeater {
        model: row.palette
        delegate: Rectangle {
          required property string modelData
          width: Style.space(12); height: width; radius: row.t.dot ? 1 : width / 2
          color: modelData
          border.width: 1
          border.color: row.t.outline
        }
      }
    }
  }

  Rectangle {
    id: pill
    visible: row.current
    anchors.right: parent.right
    anchors.rightMargin: Style.space(16)
    anchors.verticalCenter: parent.verticalCenter
    height: Style.space(26)
    width: pillText.implicitWidth + Style.space(22)
    radius: row.t.dot ? Style.space(3) : height / 2
    color: row.t.secondaryContainer
    Text {
      id: pillText
      anchors.centerIn: parent
      text: row.t.tr("In use")
      color: row.t.inkOnContainer
      font.family: row.t.fontFamily
      font.pixelSize: Style.font.caption
      font.bold: true
    }
  }

  MouseArea {
    id: hover
    anchors.fill: parent
    // Below the labels and the name field, so they take clicks first; the row itself still gets the rest.
    z: -1
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: if (!row.editing) row.activated()
    onPositionChanged: function(mouse) { row.hoverAt(mapToItem(null, mouse.x, mouse.y)) }
  }
}
