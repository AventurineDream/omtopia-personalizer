/** @file Covers fail-closed keyboard random-pick eligibility for action rows. */
import QtQuick
import QtTest
import "../ui/RandomCandidates.js" as RandomCandidates

TestCase {
  name: "RandomCandidates"

  function test_wallpaper_fx_transitions_are_eligible() {
    verify(RandomCandidates.isCandidate("wallpaper-fx", "outline", false, false));
    verify(RandomCandidates.isCandidate("wallpaper-fx", "outline-cut", false, false));
    verify(RandomCandidates.isCandidate("wallpaper-fx", "fade", false, false));
  }

  function test_wallpaper_fx_one_off_actions_are_never_eligible() {
    verify(!RandomCandidates.isCandidate("wallpaper-fx", "outline-install", false, false));
    verify(!RandomCandidates.isCandidate("wallpaper-fx", "outline-warm", false, false));
    verify(!RandomCandidates.isCandidate("wallpaper-fx", "owe-toggle", false, false));
    verify(!RandomCandidates.isCandidate("wallpaper-fx", "enable-plugin", false, false));
  }

  function test_current_selected_and_action_rows_are_excluded() {
    verify(!RandomCandidates.isCandidate("themes", "dark", true, false));
    verify(!RandomCandidates.isCandidate("themes", "light", false, true));
    verify(!RandomCandidates.isCandidate("themes", "toggle", false, false));
    verify(RandomCandidates.isCandidate("themes", "catppuccin", false, false));
  }
}
