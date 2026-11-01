# MusePilot HUD — Cross-Platform Flutter App

Meta-style HUD for the MusePilot agent. One codebase runs on
**Android, iOS, web, macOS, Windows, and Linux**, talking to the
Starlette API server (`musepilot/server/`) over REST (`/api/*`) and
WebSocket (`/ws/runs`).

## Prerequisites

- Flutter stable (verified with 3.47.9 / Dart 3.13.7): `flutter doctor`
- The API server running (from the repo root): `make server`
  (listens on `http://localhost:8501` by default)

## Run

```bash
cd app

# Web (Chrome/Edge)
flutter run -d chrome

# macOS desktop
flutter run -d macos

# Android emulator / iOS simulator (with toolchains installed)
flutter run -d emulator-5554
flutter run -d "iPhone 17"
```

### Pointing at a remote API server

Phones and remote browsers cannot reach your laptop's `localhost`.
Either pass the LAN address at launch:

```bash
flutter run -d chrome \
  --dart-define=MUSEPILOT_API_BASE=http://192.168.1.10:8501
```

or type it into the **Server connection** bar inside the app and press
**Apply**. (Android emulators can also use `http://10.0.2.2:8501` to
reach the host.)

## Quality gates

```bash
flutter analyze   # flutter_lints, zero issues required
flutter test      # golden-trace contract + client + widget tests
```

## Web deployment bundle

`make app-web` (repo root) builds a release bundle into
`musepilot/server/static/web/`, which the API server then serves at `/`
alongside the API. Rebuild after HUD changes; the directory is a
git-ignored build artifact.

## Conventions

- Every Dart file carries the Apache-2.0 header.
- Models in `lib/models/` mirror `musepilot/contracts/schemas.py`
  field-for-field; update both sides together.
- The client never synthesizes coordinates — pixel values are
  display-only copies of server-issued receipts.
- No secrets in the app: the API base URL is the only configuration,
  supplied via `--dart-define` or the in-app connection bar.
