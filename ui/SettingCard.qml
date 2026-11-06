import QtQuick
import qs.Commons

// Карточка настройки (строка-твик из customizer.sh): имя и описание слева, контрол справа.
// Контрол выбирается по kind (поле 7 вывода list_tweaks): bool — переключатель, num — ползунок,
// enum — сегменты (или «‹ значение ›», если не влезают), color — образец цвета, font/text/file/dir —
// кнопка-значение, move/add — виджеты бара. Без kind — просто значение текстом.
// Сам ничего не применяет: отдаёт сигналы, Customizer.qml зовёт customizer.sh.
Rectangle {
  id: card
  property var t
  property int index: -1
  property string label: ""
  property string name: ""
  property string sub: ""
  property string note: ""
  property string kind: ""
  property string args: ""
  property string raw: ""
  property bool selected: false
  property bool focused: false
  property bool editing: false
  property string editInitial: ""
  property string editError: ""

  signal selectMe()
  signal step(int dir)
  signal setValue(string value)
  signal activateMe()
  signal reset()
  signal submit(string text)
  signal cancel()
  signal startEdit()
  signal edited()
  signal hoverAt(point p)

  readonly property bool changed: /^●/.test(label)
  readonly property bool inactive: /^○/.test(sub)
  readonly property string title: name !== "" ? name
    : String(label).replace(/^[●○]\s*/, "").split(":  ")[0]
  // Значение: сырое из поля 9, иначе — хвост подписи после «:  ».
  readonly property string valueText: {
    if (kind !== "" && raw !== "") return raw
    var parts = String(label).split(":  ")
    return parts.length > 1 ? parts[parts.length - 1].trim() : ""
  }
  // Подсказка из заметки (последний абзац: «h/l — …») — показывается у выбранной карточки.
  readonly property string hint: {
    var paras = String(note).split("\n\n")
    return paras.length > 1 ? paras[paras.length - 1] : ""
  }
  readonly property var enumOptions: kind === "enum" ? String(args).split(" ").filter(function(s) { return s !== "" }) : []
  readonly property var numArgs: kind === "num" ? String(args).split(" ").map(Number) : []
  // Сегменты, если влезают в половину карточки; иначе «‹ значение ›».
  readonly property bool segmentsFit: {
    if (enumOptions.length < 2 || enumOptions.length > 6) return false
    var w = 0
    for (var i = 0; i < enumOptions.length; i++) w += enumOptions[i].length * Style.font.body * 0.62 + Style.space(31)
    return w + Style.space(44) <= width * 0.5
  }

  implicitHeight: Math.max(Style.space(76), textCol.implicitHeight + Style.space(28))
  radius: t.rCard
  color: selected && focused ? t.surfaceSelected : (cardHover.containsMouse ? t.surfaceHi : t.surface)
  border.width: selected ? (focused ? Style.space(2) : 1) : (t.dot ? 1 : 0)
  border.color: selected ? Util.alpha(t.primary, focused ? 0.9 : 0.4) : t.outline
  Behavior on color { ColorAnimation { duration: card.t.ms(120) } }

  onEditingChanged: if (editing) Qt.callLater(function() {
    if (!card.editing) return
    editInput.text = card.editInitial
    editInput.selectAll()
    editInput.forceActiveFocus()
  })

  MouseArea {
    id: cardHover
    anchors.fill: parent
    hoverEnabled: true
    onClicked: card.selectMe()
    onPositionChanged: function(mouse) { card.hoverAt(mapToItem(null, mouse.x, mouse.y)) }
  }

  Column {
    id: textCol
    anchors.left: parent.left
    anchors.leftMargin: Style.space(20)
    anchors.right: control.left
    anchors.rightMargin: Style.space(20)
    anchors.verticalCenter: parent.verticalCenter
    spacing: Style.space(3)
    opacity: card.inactive ? 0.55 : 1

    Row {
      spacing: Style.space(8)
      width: parent.width
      Text {
        id: titleText
        width: Math.min(implicitWidth, parent.width - (dot.visible ? dot.width + parent.spacing : 0))
        text: card.title
        elide: Text.ElideRight
        textFormat: Text.PlainText
        color: card.t.foreground
        font.family: card.t.fontFamily
        font.pixelSize: Style.font.title
        font.bold: card.selected
      }
      // ● — значение отличается от умолчания.
      Rectangle {
        id: dot
        visible: card.changed
        anchors.verticalCenter: titleText.verticalCenter
        width: Style.space(7); height: width; radius: width / 2
        color: card.t.primary
      }
    }
    Text {
      width: parent.width
      visible: text !== ""
      text: card.sub
      wrapMode: Text.Wrap
      maximumLineCount: 2
      elide: Text.ElideRight
      textFormat: Text.PlainText
      color: card.t.muted
      font.family: card.t.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
    Text {
      width: parent.width
      visible: card.selected && card.focused && card.hint !== "" && !card.editing
      text: card.hint
      wrapMode: Text.Wrap
      textFormat: Text.PlainText
      color: Util.alpha(card.t.primary, 0.85)
      font.family: card.t.fontFamily
      font.pixelSize: Style.font.caption
    }

    // i — ручной ввод значения; Enter применяет, Esc отменяет (проверяет customizer.sh).
    Rectangle {
      visible: card.editing
      width: parent.width
      height: visible ? editInput.implicitHeight + Style.space(14) : 0
      radius: card.t.rSmall
      color: card.t.surfaceLow
      border.width: 1
      border.color: card.editError ? Color.urgent : card.t.primary
      TextInput {
        id: editInput
        anchors.fill: parent
        anchors.margins: Style.space(7)
        verticalAlignment: TextInput.AlignVCenter
        color: card.t.foreground
        selectionColor: Util.alpha(card.t.primary, 0.4)
        font.family: card.t.fontFamily
        font.pixelSize: Style.font.body
        selectByMouse: true
        clip: true
        onTextEdited: card.edited()
        Keys.onReturnPressed: card.submit(text)
        Keys.onEnterPressed: card.submit(text)
        Keys.onEscapePressed: card.cancel()
      }
    }
    Text {
      visible: card.editing
      width: parent.width
      wrapMode: Text.Wrap
      textFormat: Text.PlainText
      text: card.editError ? "⚠ " + card.editError : card.t.tr("Enter — apply · Esc — cancel")
      color: card.editError ? Color.urgent : card.t.muted
      font.family: card.t.fontFamily
      font.pixelSize: Style.font.caption
    }
  }

  // ── Контрол справа ──
  Row {
    id: control
    anchors.right: parent.right
    anchors.rightMargin: Style.space(18)
    anchors.verticalCenter: parent.verticalCenter
    spacing: Style.space(10)

    // ↺ — сбросить к умолчанию (x).
    Rectangle {
      visible: card.changed && card.kind !== "" && card.kind !== "move" && card.kind !== "add"
      anchors.verticalCenter: parent.verticalCenter
      width: Style.space(30); height: width
      radius: card.t.dot ? Style.space(3) : width / 2
      color: resetHover.containsMouse ? card.t.surfaceHi : "transparent"
      Text {
        anchors.centerIn: parent
        text: "󰑓"
        color: card.t.muted
        font.family: card.t.iconFont
        font.pixelSize: Style.font.body
      }
      MouseArea {
        id: resetHover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: card.reset()
      }
    }

    Loader {
      anchors.verticalCenter: parent.verticalCenter
      sourceComponent: card.kind === "bool" ? switchC
        : card.kind === "num" && card.numArgs.length >= 2 ? sliderC
        : card.kind === "enum" && card.segmentsFit ? segmentsC
        : card.kind === "enum" || card.kind === "font" || card.kind === "cycle" ? stepperC
        : card.kind === "color" ? colorC
        : card.kind === "text" || card.kind === "file" || card.kind === "dir" ? valueC
        : card.kind === "move" ? moveC
        : card.kind === "add" ? addC
        : plainC
    }
  }

  Component {
    id: switchC
    M3Switch {
      t: card.t
      checked: card.raw === "true"
      onToggled: card.activateMe()
    }
  }

  Component {
    id: sliderC
    Row {
      spacing: Style.space(14)
      Text {
        anchors.verticalCenter: parent.verticalCenter
        width: Style.space(48)
        horizontalAlignment: Text.AlignRight
        text: slider.format(slider.shown)
        color: card.t.foreground
        font.family: card.t.fontFamily
        font.pixelSize: Style.font.body
        font.features: { "tnum": 1 }
        MouseArea {
          anchors.fill: parent
          cursorShape: Qt.IBeamCursor
          onClicked: card.startEdit()
        }
      }
      M3Slider {
        id: slider
        anchors.verticalCenter: parent.verticalCenter
        width: Style.space(260)
        t: card.t
        from: card.numArgs[0]
        to: card.numArgs[1]
        stepSize: card.numArgs.length > 2 ? card.numArgs[2] : 0
        value: Number(card.raw)
        onMoved: card.selectMe()
        onCommitted: function(v) { card.setValue(slider.format(v)) }
      }
    }
  }

  Component {
    id: segmentsC
    Segmented {
      t: card.t
      options: card.enumOptions
      value: card.raw
      onPicked: function(v) { card.setValue(v) }
    }
  }

  Component {
    id: stepperC
    Stepper {
      t: card.t
      text: card.valueText || card.t.tr("system")
      onStepped: function(dir) { card.step(dir) }
      onClicked: card.step(1)
    }
  }

  Component {
    id: colorC
    Stepper {
      t: card.t
      text: card.valueText
      hasSwatch: true
      swatch: card.t.resolveColor(card.valueText)
      onStepped: function(dir) { card.step(dir) }
      onClicked: card.activateMe()
    }
  }

  Component {
    id: valueC
    Stepper {
      t: card.t
      arrows: card.kind === "dir"
      text: (card.kind === "text" ? "󰏫  " : "󰉋  ") + (card.valueText || "—")
      onStepped: function(dir) { card.step(dir) }
      onClicked: card.kind === "text" ? card.startEdit() : card.activateMe()
    }
  }

  // Виджет на баре: ‹ › двигают, ✕ убирает.
  Component {
    id: moveC
    Row {
      spacing: Style.space(6)
      Stepper {
        t: card.t
        text: card.t.tr("Move")
        onStepped: function(dir) { card.step(dir) }
      }
      Stepper {
        t: card.t
        arrows: false
        text: "󰅖  " + card.t.tr("Remove")
        onClicked: card.activateMe()
      }
    }
  }

  Component {
    id: addC
    Stepper {
      t: card.t
      arrows: false
      text: "󰐕  " + card.t.tr("Add to bar")
      onClicked: card.activateMe()
    }
  }

  Component {
    id: plainC
    Text {
      text: card.valueText
      color: card.t.foreground
      font.family: card.t.fontFamily
      font.pixelSize: Style.font.body
    }
  }
}
