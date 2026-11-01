// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Meta design language: Meta blue accents on dark or light surfaces.
library;

import 'package:flutter/material.dart';

/// Meta palette and light/dark theme builders for the console.
class MetaTheme {
  // Brand Primaries
  static const Color metaBlue = Color(0xFF1877F2);
  static const Color metaBlueDark = Color(0xFF2D88FF);

  // Status & Verification
  static const Color emeraldVerified = Color(0xFF00E676);
  static const Color coralAlert = Color(0xFFFF3B5C);
  static const Color amberWarning = Color(0xFFFFB300);

  // Deep Obsidian Dark Surfaces
  static const Color obsidianBg = Color(0xFF0B0E14);
  static const Color surfaceCard = Color(0xFF121824);
  static const Color surfaceCardElevated = Color(0xFF1A2334);
  static const Color surfaceCardBorder = Color(0xFF1E293B);
  static const Color surfaceCardBorderActive = Color(0xFF2E3E5B);

  // Typography Inks (Dark)
  static const Color inkPrimary = Color(0xFFF1F5F9);
  static const Color inkSecondary = Color(0xFF94A3B8);
  static const Color inkMuted = Color(0xFF64748B);

  // Light Palette (for theme completeness)
  static const Color lightBg = Color(0xFFF8FAFC);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color borderLight = Color(0xFFE2E8F0);
  static const Color inkLightPrimary = Color(0xFF0F172A);
  static const Color inkLightSecondary = Color(0xFF475569);

  // Aliases for backward compatibility
  static const Color blue = metaBlue;
  static const Color blueDark = metaBlueDark;
  static const Color gray100 = lightBg;
  static const Color ink900 = inkLightPrimary;
  static const Color ink500 = inkLightSecondary;
  static const Color darkBg = obsidianBg;
  static const Color darkSurface = surfaceCard;
  static const Color darkInk = inkPrimary;
  static const Color darkInkSecondary = inkSecondary;
  static const Color green = emeraldVerified;
  static const Color red = coralAlert;
  static const Color amber = amberWarning;

  /// Build the dark Meta console theme.
  static ThemeData dark() {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: metaBlue,
          brightness: Brightness.dark,
        ).copyWith(
          primary: metaBlue,
          secondary: metaBlueDark,
          surface: surfaceCard,
        );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: obsidianBg,
      cardTheme: CardThemeData(
        color: surfaceCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: surfaceCardBorder, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceCardElevated,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 12,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: surfaceCardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: surfaceCardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: metaBlue, width: 1.5),
        ),
        labelStyle: const TextStyle(color: inkSecondary, fontSize: 13),
        hintStyle: const TextStyle(color: inkMuted, fontSize: 13),
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.5,
          color: inkPrimary,
        ),
        headlineSmall: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
          color: inkPrimary,
        ),
        titleLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
          color: inkPrimary,
        ),
        titleMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: inkPrimary,
        ),
        bodyLarge: TextStyle(fontSize: 14, color: inkPrimary),
        bodyMedium: TextStyle(fontSize: 13, color: inkSecondary),
        bodySmall: TextStyle(fontSize: 12, color: inkMuted),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
          color: inkPrimary,
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: surfaceCardBorder,
        thickness: 1,
        space: 1,
      ),
    );
  }

  /// Build the light Meta console theme.
  static ThemeData light() {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: metaBlue,
          brightness: Brightness.light,
        ).copyWith(
          primary: metaBlue,
          secondary: metaBlueDark,
          surface: surfaceLight,
        );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: scheme,
      scaffoldBackgroundColor: lightBg,
      cardTheme: CardThemeData(
        color: surfaceLight,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: borderLight, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceLight,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 12,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: borderLight),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: borderLight),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: metaBlue, width: 1.5),
        ),
        labelStyle: const TextStyle(color: inkLightSecondary, fontSize: 13),
        hintStyle: const TextStyle(color: inkLightSecondary, fontSize: 13),
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.5,
          color: inkLightPrimary,
        ),
        headlineSmall: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
          color: inkLightPrimary,
        ),
        titleLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
          color: inkLightPrimary,
        ),
        titleMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: inkLightPrimary,
        ),
        bodyLarge: TextStyle(fontSize: 14, color: inkLightPrimary),
        bodyMedium: TextStyle(fontSize: 13, color: inkLightSecondary),
        bodySmall: TextStyle(fontSize: 12, color: inkLightSecondary),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
          color: inkLightPrimary,
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: borderLight,
        thickness: 1,
        space: 1,
      ),
    );
  }
}
