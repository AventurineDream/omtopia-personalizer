# Omtopia Personalizer implementation plan

## Goal

Keep randomized choices confined to actual Wallpaper FX transitions, preserve the Customizer's selected language in its Home date, and make both behaviors regression-testable. The fork retains the upstream plugin ID so existing Omarchy bindings and settings continue to work.

## Findings and initial scope

1. **High impact — random pick can run an unrelated operation.** `r` filters list rows with an incomplete action-value blacklist. With Wallpaper FX filtered to `cut`, `outline-install` can become the only candidate and launch the cut-out-model installer. The initial fix uses fail-closed transition eligibility for the Wallpaper FX category; the regression test covers both eligible transitions and one-off actions. Never run the installer on the workstation as a test.
2. **Lower impact — Home date ignores Customizer language.** The Home page uses the process locale even though the plugin can select Russian independently through `customizer.json`. The initial fix passes the effective UI language into date formatting.

## Sequence

| Order | GitHub issue | Work | Reasoning | Dependency / tandem |
|---|---|---|---|---|
| 1 | [#1 — Prevent random pick from invoking one-off Wallpaper FX actions](https://github.com/AventurineDream/omtopia-personalizer/issues/1) | Fail closed to known transition values and add deterministic regression coverage. | **Heavy** — action boundaries and filtered selection semantics; protect the installer path. | Release blocker. Keep isolated from branding/docs work. |
| 2 | [#2 — Format the Home date with the selected Customizer language](https://github.com/AventurineDream/omtopia-personalizer/issues/2) | Match English/Russian date output to Customizer language rather than host locale. | **Light** — localized formatting and a narrow UI surface. | Independent of #1; can be implemented/tested in tandem. |
| 3 | [#3 — Share Wallpaper FX transition eligibility metadata](https://github.com/AventurineDream/omtopia-personalizer/issues/3) | Remove duplicated transition lists so adding a transition cannot silently make it unavailable to random selection. | **Heavy** — choose a stable metadata contract across Python list generation and QML. | Depends on #1's behavior contract; can be developed in tandem with #4. |
| 4 | [#4 — Add a safe end-to-end test for filtered random picks](https://github.com/AventurineDream/omtopia-personalizer/issues/4) | Add a repeatable end-to-end test of `/` → filtered Wallpaper FX rows → `r`, with all apply/installer effects intercepted. | **Medium** — isolate Quickshell and backend process behavior without touching user state. | Depends on #1; can be developed in tandem with #3. |

## Verification gates

- Run the QML regression test for eligible transitions, current/selected rows, and one-off actions.
- Run the repository's existing focused backend command tests that cover action dispatch.
- Visually exercise the fork's Home page and Wallpaper FX filtered list with computer use. For the `r` action, use only the safe test environment; do not invoke `outline-install` on the host.
- Run QML lint on touched QML/JavaScript and the repo's relevant Python tests once after the change set is complete.
- Obtain an independent **sol6.1** review before the first merge. Merge only after that review and the verification gates pass.

## Compatibility and safety

- Keep plugin ID `kamradsmeshnyavy.customizer` for Omarchy shell bindings and existing state paths.
- Do not install the optional cut-out model or launch its installer during testing.
- No user wallpaper, style, theme, or shell settings are part of the regression test fixture.
