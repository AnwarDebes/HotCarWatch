# Changelog

All notable changes to HotCarWatch are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-12

First public release.

### Added

- Cabin thermal model: first-order rise above ambient driven by solar
  load, with 7 vehicle archetypes (NIA/ASHRAE thermal time constants).
- Occupant hyperthermia model for 7 occupant archetypes (infant,
  toddler, child, small/medium/brachycephalic dog, cat) with time to
  40°C and 42°C core temperature milestones.
- Ranked interventions, with the only guaranteed-safe option (never
  leave them in the car) clearly marked.
- Validation against 16 published cases (McLaren, Null & Quinn 2005;
  Vanos 2018 sun-vs-shade delta).
- Static browser frontend: 27 KB raw, 8.8 KB gzipped, no build step,
  no network calls, profile stored in `localStorage` only.
- Validation, scenario, and intervention experiments with JSON outputs.
- LaTeX paper with figures.
- 15 unit tests.

[0.1.0]: https://github.com/AnwarDebes/HotCarWatch/releases/tag/v0.1.0
