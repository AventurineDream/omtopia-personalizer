import QtQuick
import qs.Commons

// Звуки: карточка пакета (имя и описание), громкость шкалой, состояние звуков и событий окон,
// кнопки ▶ — послушать событие выбранным пакетом (customizer.sh sound-preview, окно не закрывается).
Item {
  id: sp
  property var t
  property var v: ({})
  property string pack: ""           // пакет под курсором (pack:<имя>) или выбранный в настройках
  property string packNote: ""
  signal play(string pack, string event)

  function num(key, def) { var x = Number(v[key]); return v[key] === undefined || !isFinite(x) ? def : x }
  function on(key, def) { return v[key] === undefined ? def : String(v[key]) === "true" }
  readonly property real volume: num("soundVolume", 0.6)
  readonly property bool soundsOn: on("sounds", true)

  Rectangle {
    anchors.fill: parent
    radius: sp.t.rCard
    color: sp.t.surface

    Column {
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      anchors.margins: Style.space(24)
      spacing: Style.space(14)

      Row {
        spacing: Style.space(14)
        Rectangle {
          width: Style.space(56); height: width
          radius: sp.t.dot ? Style.space(4) : width / 2
          color: sp.soundsOn ? sp.t.primary : sp.t.surfaceHi
          Text { anchors.centerIn: parent; text: sp.soundsOn ? "󰕾" : "󰖁"; color: sp.soundsOn ? sp.t.inkOnPrimary : sp.t.muted; font.family: sp.t.iconFont; font.pixelSize: Style.font.display }
        }
        Column {
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(4)
          Text { text: sp.pack; color: sp.t.foreground; font.family: sp.t.headFont; font.pixelSize: Style.font.heading; font.bold: true }
          Text {
            width: Math.min(implicitWidth, Style.space(520))
            text: sp.packNote
            elide: Text.ElideRight
            color: sp.t.muted
            font.family: sp.t.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
        }
      }

      // Громкость — столбики, как у эквалайзера.
      Row {
        spacing: Style.space(4)
        Repeater {
          model: 10
          Rectangle {
            required property int index
            anchors.bottom: parent.bottom
            width: Style.space(10)
            height: Style.space(8) + index * Style.space(3)
            radius: sp.t.dot ? 1 : Style.space(3)
            color: (index + 1) / 10 <= sp.volume + 0.001 && sp.soundsOn ? sp.t.primary : sp.t.unlit
          }
        }
        Text {
          anchors.bottom: parent.bottom
          leftPadding: Style.space(10)
          text: Math.round(sp.volume * 100) + " %   ·   " + sp.t.tr("window events") + ": " + (sp.on("windowSounds", false) ? sp.t.tr("on") : sp.t.tr("off"))
          color: sp.t.foreground
          font.family: sp.t.fontFamily
          font.pixelSize: Style.font.bodySmall
        }
      }

      Flow {
        width: parent.width
        spacing: Style.space(8)
        Repeater {
          model: ["notify", "volume", "switch", "open", "close", "critical", "lock"]
          Rectangle {
            required property string modelData
            height: Style.space(34)
            width: playRow.implicitWidth + Style.space(22)
            radius: sp.t.dot ? Style.space(3) : height / 2
            color: playHover.containsMouse ? sp.t.secondaryContainer : sp.t.surfaceLow
            Row {
              id: playRow
              anchors.centerIn: parent
              spacing: Style.space(6)
              Text { text: "󰐊"; color: sp.t.primary; font.family: sp.t.iconFont; font.pixelSize: Style.font.body; anchors.verticalCenter: parent.verticalCenter }
              Text { text: modelData; color: sp.t.foreground; font.family: sp.t.fontFamily; font.pixelSize: Style.font.bodySmall; anchors.verticalCenter: parent.verticalCenter }
            }
            MouseArea { id: playHover; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: sp.play(sp.pack, modelData) }
          }
        }
      }
    }
  }
}
