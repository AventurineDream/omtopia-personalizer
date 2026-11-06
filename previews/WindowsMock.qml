import QtQuick
import QtQuick.Effects
import qs.Commons

// Три окна (master + два справа) в координатах настоящего экрана: отступы, рамка, скругление, тень,
// затемнение неактивных — как у Hyprland. top — место под бар сверху (или слева, если leftInset).
Item {
  id: wm
  property var t
  property real gapsIn: 2
  property real gapsOut: 4
  property real border: 2
  property real rounding: 10
  property bool shadow: true
  property bool dim: true
  property real dimStrength: 0.1
  property real topInset: 0
  property real leftInset: 0
  property real windowAlpha: 1
  readonly property real gi: gapsIn
  readonly property real go: gapsOut

  Item {
    id: area
    x: wm.leftInset + wm.go
    y: wm.topInset + wm.go
    width: wm.width - wm.leftInset - 2 * wm.go
    height: wm.height - wm.topInset - 2 * wm.go
    Repeater {
      model: 3
      Rectangle {
        required property int index
        readonly property bool active: index === 0
        readonly property real g: wm.gi / 2
        x: index === 0 ? 0 : area.width * 0.55 + g
        y: index === 2 ? area.height / 2 + g : 0
        width: index === 0 ? area.width * 0.55 - g : area.width * 0.45 - g
        height: index === 0 ? area.height : area.height / 2 - g
        radius: wm.rounding
        color: Qt.tint(Util.alpha(Color.background, wm.windowAlpha), Qt.rgba(0, 0, 0, !active && wm.dim ? wm.dimStrength : 0))
        border.width: wm.border
        border.color: active ? wm.t.primary : Util.alpha(wm.t.foreground, 0.25)
        layer.enabled: wm.shadow
        layer.effect: MultiEffect { shadowEnabled: true; shadowColor: "#000000"; shadowOpacity: 0.5; shadowBlur: 0.8; shadowVerticalOffset: 6 }
        Column {
          x: 24; y: 22; spacing: 12
          Repeater {
            model: 6
            Rectangle { required property int index; width: 120 + (index * 67) % 220; height: 10; radius: 5; color: Util.alpha(wm.t.foreground, 0.28) }
          }
        }
      }
    }
  }
}
