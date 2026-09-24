# IronCycle 1.90.1

## Scope
- Preserve raw set-to-set rest durations.
- Apply a 60-second minimum effective duration only in analytics, preventing forgotten sets saved back-to-back from depressing rest metrics.
- Expose whether an analytics sample was adjusted and why.
- Apply the guard to week comparison, weekly summaries, mesocycle analytics, and rest trends.
- Leave the live rest timer, persistence, backup format, and schema unchanged.
- Keep the compact portrait `RPE` label and existing 1.0-10.0 validation in 0.5 steps.
