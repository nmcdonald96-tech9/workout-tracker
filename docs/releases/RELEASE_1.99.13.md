# IronCycle 1.99.13

## Display-mode rebuild stabilization

- Retains the 1.99.12 portrait title, fixed actions lane, main View control, unified mode selector, and scrollable Profile Settings.
- Closes the active selector before requesting workout-tree replacement.
- Routes every Standard/Focus/Detailed change through the existing post-callback structural-refresh coordinator.
- Coalesces repeated mode requests and performs one deferred navigation/canvas rebuild.
- Removes inline display rebuilds and duplicate Profile Settings mode persistence.
- Adds privacy-safe lifecycle markers for mode request, dialog close, scheduling/coalescing, rebuild start, and rebuild finish.
- Leaves weight-derived calculations and direct reps repaint logic unchanged. Schema remains 20.
