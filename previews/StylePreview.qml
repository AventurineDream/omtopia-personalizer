import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import ".."

// Стиль / пресет: мини-стол, каким он станет — обои пресета (иначе текущие), бар в скине стиля
// (barSkinData или файл barSkin), окна с его hyprGeometry (скругление, отступы, рамка, тень) и чипы:
// тема(ы), блокировка, анимации, прозрачность, шрифты. data — JSON файла пресета/стиля ({} — сейчас).
Item {
  id: sp
  property var t
  property var doc: ({})
  property string currentWallpaper: ""          // file:// URL текущих обоев
  property var activeSkin: ({})
  property var activeBar: ({})
  property var palette: ({})
  property real screenWidth: 1440
  property real screenHeight: 900

  readonly property string home: Quickshell.env("HOME")
  readonly property string wallPath: {
    var w = String(sp.doc.wallpaper || "")
    return w.indexOf("~/") === 0 ? home + "/" + w.slice(2) : w
  }
  // Скин: свой из bar-skins, потом встроенный в плагине бара.
  readonly property string skinName: sp.doc.barSkin ? String(sp.doc.barSkin) : ""
  property var fileSkin: null
  property int skinTry: 0
  onSkinNameChanged: { sp.fileSkin = null; sp.skinTry = 0 }
  FileView {
    path: sp.skinName === "" ? "" : sp.skinTry === 0
      ? sp.home + "/.config/omarchy/bar-skins/" + sp.skinName + ".json"
      : sp.home + "/.config/omarchy/plugins/kamradsmeshnyavy.bar/skins/" + sp.skinName + ".json"
    printErrors: false
    onLoaded: { try { sp.fileSkin = JSON.parse(text()) } catch (e) { sp.fileSkin = null } }
    onLoadFailed: if (sp.skinTry === 0) sp.skinTry = 1
  }
  readonly property var skin: (sp.doc.barSkinData && typeof sp.doc.barSkinData === "object") ? sp.doc.barSkinData
    : sp.fileSkin ? sp.fileSkin : sp.activeSkin
  readonly property var bar: {
    var b = ({})
    for (var k in sp.activeBar) b[k] = sp.activeBar[k]
    var l = sp.doc.barLayoutData
    if (l && typeof l === "object") for (var k2 in l) b[k2] = l[k2]
    if (sp.doc.barTransparent !== undefined) b.transparent = sp.doc.barTransparent === true
    return b
  }
  readonly property var geo: (sp.doc.hyprGeometry && typeof sp.doc.hyprGeometry === "object") ? sp.doc.hyprGeometry : ({})
  function g(key, def) { var v = Number(sp.geo[key]); return sp.geo[key] === undefined || !isFinite(v) ? def : v }

  readonly property var chips: {
    var out = []
    var th = sp.doc.theme
    if (th && typeof th === "object") out.push("󰏘 " + (th.dark || "") + (th.light && th.light !== th.dark ? " / " + th.light : ""))
    else if (th) out.push("󰏘 " + th)
    if (sp.doc.lock && sp.doc.lock.design) out.push("󰌾 " + sp.doc.lock.design)
    if (sp.doc.anims) out.push("󰔡 " + sp.doc.anims)
    if (sp.doc.opacity) out.push("󰂵 " + sp.doc.opacity)
    if (sp.doc.blur) out.push("󰂷 " + sp.doc.blur)
    if (sp.doc.fonts) out.push("󰛖 " + sp.doc.fonts)
    return out
  }

  ScreenMock {
    id: screen
    anchors.fill: parent
    t: sp.t
    screenWidth: sp.screenWidth
    screenHeight: sp.screenHeight
    wallpaper: wallImg.status === Image.Error || !sp.wallPath ? sp.currentWallpaper : sp.t.fileUrl(sp.wallPath)

    Image { id: wallImg; visible: false; source: sp.wallPath ? sp.t.fileUrl(sp.wallPath) : ""; asynchronous: true; sourceSize.width: 8 }

    WindowsMock {
      anchors.fill: parent
      t: sp.t
      readonly property bool vert: mock.vertical
      topInset: vert ? 0 : (mock.position === "top" ? mock.barSize + mock.gap : 0)
      leftInset: vert && mock.position === "left" ? mock.barSize + mock.gap : 0
      gapsIn: sp.geo.noGaps === true ? 0 : sp.g("gapsIn", 4)
      gapsOut: sp.geo.noGaps === true ? 0 : sp.g("gapsOut", 8)
      border: sp.geo.noGaps === true ? 0 : sp.g("borderSize", 2)
      rounding: sp.geo.noGaps === true ? 0 : sp.g("rounding", 10)
      shadow: sp.geo.shadow !== false
    }

    BarMock {
      id: mock
      anchors.fill: parent
      skin: sp.skin || ({})
      bar: sp.bar
      palette: sp.palette
      screenWidth: sp.screenWidth
    }
  }

  // Чипы — поверх экрана, внизу.
  Flow {
    anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: Style.space(12) }
    spacing: Style.space(6)
    layoutDirection: Qt.LeftToRight
    Repeater {
      model: sp.chips
      Rectangle {
        required property string modelData
        height: Style.space(24)
        width: chipText.implicitWidth + Style.space(16)
        radius: sp.t.dot ? Style.space(3) : height / 2
        color: Util.alpha(sp.t.background, 0.82)
        Text {
          id: chipText
          anchors.centerIn: parent
          text: modelData
          color: sp.t.foreground
          font.family: sp.t.fontFamily
          font.pixelSize: Style.font.caption
        }
      }
    }
  }
}
