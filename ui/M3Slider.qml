import QtQuick
import qs.Commons

// Ползунок Material 3: толстая активная часть, зазор, вертикальная ручка, тонкая
// неактивная часть с точкой на конце. В DOT-MATRIX — ряд «лампочек».
// Пока тянут мышью, значение живёт локально (moved), на отпускании — committed():
// customizer.sh пишет его один раз, а не на каждый пиксель.
Item {
  id: sl
  property var t
  property real from: 0
  property real to: 1
  property real stepSize: 0
  property real value: 0
  property bool enabled: true
  signal moved(real v)
  signal committed(real v)

  property bool dragging: false
  property real dragValue: 0
  // После отпускания показываем новое значение, пока список не перечитается с ним
  // (иначе ручка на миг прыгает назад). Не пришло за 3 с (ошибка записи) — сдаёмся.
  property bool holding: false
  onValueChanged: holding = false
  Timer { id: holdTimer; interval: 3000; onTriggered: sl.holding = false }
  readonly property real shown: dragging || holding ? dragValue : value
  readonly property real ratio: to > from ? Math.max(0, Math.min(1, (shown - from) / (to - from))) : 0
  readonly property int decimals: {
    var s = String(stepSize)
    var dot = s.indexOf(".")
    return dot < 0 ? 0 : s.length - dot - 1
  }
  function format(v) { return Number(v).toFixed(decimals) }

  implicitWidth: Style.space(240)
  implicitHeight: Style.space(36)
  opacity: enabled ? 1 : 0.45

  function snap(v) {
    v = Math.max(from, Math.min(to, v))
    if (stepSize > 0) v = from + Math.round((v - from) / stepSize) * stepSize
    return Number(v.toFixed(decimals))
  }
  function valueAt(x) { return snap(from + (to - from) * Math.max(0, Math.min(1, x / Math.max(1, width)))) }

  // ── M3 ──
  Item {
    anchors.fill: parent
    visible: !sl.t.dot
    readonly property real gap: Style.space(6)
    readonly property real handleX: sl.ratio * (width - handle.width)

    Rectangle {
      anchors.verticalCenter: parent.verticalCenter
      x: 0
      width: Math.max(0, parent.handleX - parent.gap)
      height: Style.space(14)
      radius: sl.t.rSmall
      color: sl.t.primary
      visible: width > 1
    }
    Rectangle {
      anchors.verticalCenter: parent.verticalCenter
      x: parent.handleX + handle.width + parent.gap
      width: Math.max(0, parent.width - x)
      height: Style.space(14)
      radius: sl.t.rSmall
      color: sl.t.secondaryContainer
      visible: width > 1
      Rectangle {
        anchors.right: parent.right
        anchors.rightMargin: Style.space(5)
        anchors.verticalCenter: parent.verticalCenter
        width: Style.space(4); height: width; radius: width / 2
        color: sl.t.primary
      }
    }
    Rectangle {
      id: handle
      x: parent.handleX
      anchors.verticalCenter: parent.verticalCenter
      width: Style.space(4)
      height: sl.dragging ? parent.height : parent.height - Style.space(6)
      radius: width / 2
      color: sl.t.primary
      Behavior on height { NumberAnimation { duration: sl.t.ms(120) } }
    }
  }

  // ── DOT-MATRIX ──
  Row {
    anchors.verticalCenter: parent.verticalCenter
    visible: sl.t.dot
    spacing: Style.space(3)
    readonly property int count: Math.max(8, Math.floor((sl.width + spacing) / (Style.space(8) + spacing)))
    Repeater {
      model: parent.count
      delegate: Rectangle {
        required property int index
        readonly property bool lit: index < Math.round(sl.ratio * parent.count)
        width: Style.space(8); height: width
        radius: width / 2
        color: lit ? sl.t.primary : sl.t.unlit
      }
    }
  }

  MouseArea {
    anchors.fill: parent
    anchors.topMargin: -Style.space(6)
    anchors.bottomMargin: -Style.space(6)
    enabled: sl.enabled
    preventStealing: true
    cursorShape: Qt.PointingHandCursor
    onPressed: function(mouse) {
      sl.dragValue = sl.valueAt(mouse.x)
      sl.dragging = true
      sl.moved(sl.dragValue)
    }
    onPositionChanged: function(mouse) {
      if (!sl.dragging) return
      var v = sl.valueAt(mouse.x)
      if (v !== sl.dragValue) { sl.dragValue = v; sl.moved(v) }
    }
    onReleased: {
      if (!sl.dragging) return
      var v = sl.dragValue
      sl.dragging = false
      if (v !== sl.value) { sl.holding = true; holdTimer.restart(); sl.committed(v) }
    }
    onCanceled: sl.dragging = false
  }
}
