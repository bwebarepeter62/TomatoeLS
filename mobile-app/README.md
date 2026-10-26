# Tomato Leaf Scan — Mobile Application (Flutter)

## Overview
This directory contains the original cross-platform mobile application prototype for **Tomato Leaf Scan**, built using **Flutter and Dart**. It provides on-device tomato leaf disease detection directly on Android and iOS smartphones without uploading photos to cloud servers.

- **Framework:** Flutter 3.x (Dart SDK `>=3.3.0 <4.0.0`)
- **Package Manifest:** `mobile-app/pubspec.yaml`
- **Model Asset:** `mobile-app/assets/models/best_int8.tflite`
- **Runtime:** Google AI Edge LiteRT (pinned to 1.4.2 via Gradle)

---

## Directory Structure

```text
mobile-app/
│
├── README.md                  # Mobile application documentation
├── pubspec.yaml               # Flutter dependencies and asset manifest
├── pubspec.lock               # Pinned package versions
├── analysis_options.yaml      # Dart analysis and linter rules
├── .metadata                  # Flutter project metadata
│
├── lib/                       # Dart Application Source Code
│   ├── main.dart              # Entry point, theme, and 4 screens (Home, Scan, Result, Assistant)
│   ├── models/
│   │   ├── detector.dart      # TomatoDetector: TFLite loader, tensor formatting, NMS
│   │   └── disease_info.dart  # DiseaseInfo model and 15-entry agronomic knowledge base
│   ├── services/
│   │   └── chat.dart          # DeepSeek chat client with offline rule-based fallback
│   └── widgets/
│       └── detection_image.dart # Bounding-box overlay painter widget
│
├── assets/                    # Bundled Mobile Assets
│   ├── models/                # On-device model (best_int8.tflite)
│   ├── google_fonts/          # Offline TTF fonts (DM Sans & Bricolage Grotesque)
│   ├── icon/                  # App launcher icon sources
│   └── favicon/               # Web favicons
│
├── test/                      # Unit Tests
│   └── leafscan_test.dart     # 11 Dart unit tests for label mapping & knowledge base
│
└── android/ · ios/ · macos/ … # Platform-specific native host projects
```

---

## The Four Mobile Screens (in `lib/main.dart`)
1. **Home:** Branding and 3-step diagnostic overview.
2. **Scan:** Camera and photo gallery picker with scan trigger.
3. **Result:** Diagnosis card, confidence score ring, bounding boxes drawn on photo, and treatment guidance.
4. **Assistant:** AI follow-up chat (DeepSeek online with deterministic offline rule-based fallback).

---

## Setup & Running Locally

### Prerequisites
- Flutter SDK (Dart `>=3.3.0`)
- Android Studio / Android SDK (for Android builds) or Xcode (for iOS on macOS)
- A physical smartphone or emulator

### Commands
1. Navigate to the mobile app folder:
   ```bash
   cd mobile-app
   ```
2. Fetch dependencies:
   ```bash
   flutter pub get
   ```
3. Run unit tests:
   ```bash
   flutter test
   ```
4. Run in debug mode on a connected device:
   ```bash
   flutter run
   ```
5. Build a release Android APK:
   ```bash
   flutter build apk --release
   ```

---

## Relationship with the Web Application
- **Shared AI Weights:** The mobile app uses the same `best_int8.tflite` model and 15-class disease taxonomy as the Flask web application.
- **Storage Model Distinction:** The mobile application is stateless (results reside in RAM during the session), while the web application provides persistent SQLite multi-farm management, inspection history, and visual dashboards.
