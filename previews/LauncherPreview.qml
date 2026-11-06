import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons

// Скин лаунчера вживую: настоящая вьюха из клона меню (kamradsmeshnyavy.menu/<View>.qml) на уменьшенном
// экране, с корнем меню из omarchy-menu.jsonc. Проводка — как у skinLoader в Menu.qml. Один скин за раз
// (в меню два живых скина роняли Quickshell на загрузке иконок); пока превью не видно — выгружен.
Item {
  id: lp
  property var t
  property string skin: ""              // пусто — текущий скин из menu-skin.json
  property real backdrop: -1            // < 0 — из menu-skin.json
  property string wallpaper: ""
  property real screenWidth: 1440
  property real screenHeight: 900

  readonly property string menuDir: Qt.resolvedUrl("../../kamradsmeshnyavy.menu/")
  readonly property var conf: confLoader.item
  readonly property string shownSkin: lp.skin || (lp.conf ? lp.conf.skin : "constellation")
  readonly property bool listSkin: lp.shownSkin === "list"
  readonly property bool failed: viewLoader.status === Loader.Error

  // Таблица скин → файл и variant — из самого меню (SkinConfig.qml), без копии здесь.
  Loader { id: confLoader; source: lp.menuDir + "SkinConfig.qml" }
  Loader { id: paletteLoader; source: lp.menuDir + "ThemePalette.qml" }

  // Корень меню: строки верхнего уровня (id без точки) из стокового JSONC.
  ListModel { id: rows }
  FileView {
    path: Quickshell.env("OMARCHY_PATH") + "/default/omarchy/omarchy-menu.jsonc"
    printErrors: false
    onLoaded: {
      rows.clear()
      var re = /^\s*"([a-z-]+)":\s*\{"icon":"([^"]*)","label":"([^"]*)"(.*)$/gm
      var m
      while ((m = re.exec(text())) !== null) {
        var action = /"action":/.test(m[4])
        rows.append({
          itemId: m[1], kind: action ? "action" : "menu", icon: m[2], iconFont: "", appIcon: "", appId: "",
          label: m[3], target: m[1], detail: "", path: "", childCount: action ? 0 : 6,
          action: "", provider: "", score: 0, section: ""
        })
      }
    }
  }

  // Курсор гуляет по строкам — видно, как скин подсвечивает выбор.
  property int cursor: 0
  Timer {
    interval: 1400
    repeat: true
    running: lp.visible && rows.count > 0
    onTriggered: lp.cursor = (lp.cursor + 1) % rows.count
  }

  ScreenMock {
    id: screen
    anchors.fill: parent
    t: lp.t
    screenWidth: lp.screenWidth
    screenHeight: lp.screenHeight
    wallpaper: lp.wallpaper

    Loader {
      id: viewLoader
      anchors.fill: parent
      active: lp.visible && !!lp.conf && !lp.listSkin && rows.count > 0
      source: active ? lp.menuDir + lp.conf.fileFor(lp.shownSkin) : ""
      onLoaded: {
        var view = viewLoader.item
        view.theme = paletteLoader.item
        view.variant = Qt.binding(function() { return lp.conf.variantFor(lp.shownSkin) })
        view.rowModel = rows
        view.iconResolver = function(icon) { return "" }
        view.selectedIndex = Qt.binding(function() { return lp.cursor })
        view.cursorActive = true
        view.burst = true
        view.title = "Omarchy"
        view.subtitle = ""
        view.query = ""
        view.backdrop = Qt.binding(function() { return lp.backdrop >= 0 ? lp.backdrop : lp.conf.backdrop })
        view.foreground = Qt.binding(function() { return Commons.Color.menu.text })
        view.accent = Qt.binding(function() { return Commons.Color.accent })
        view.background = Qt.binding(function() { return Commons.Color.background })
        view.revision = 1
        view.live = Qt.binding(function() { return lp.visible })
        if (typeof view.wake === "function") view.wake()
      }
    }

    // «list» — стоковая карточка: без вьюхи, простой список.
    Rectangle {
      visible: lp.listSkin
      anchors.centerIn: parent
      width: 640
      height: listCol.implicitHeight + 48
      radius: 16
      color: Commons.Color.menu.background
      border.width: 2
      border.color: Commons.Color.menu.border
      Column {
        id: listCol
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 24 }
        spacing: 4
        Repeater {
          model: rows
          delegate: Rectangle {
            required property int index
            required property string icon
            required property string label
            width: listCol.width
            height: 52
            radius: 10
            color: index === lp.cursor ? Util.alpha(Commons.Color.accent, 0.22) : "transparent"
            Row {
              anchors.verticalCenter: parent.verticalCenter
              x: 16
              spacing: 16
              Text { text: icon; color: Commons.Color.accent; font.family: Style.font.family; font.pixelSize: 26 }
              Text { text: label; color: Commons.Color.menu.text; font.family: Style.font.menuFamily; font.pixelSize: 24 }
            }
          }
        }
      }
    }
  }
}
