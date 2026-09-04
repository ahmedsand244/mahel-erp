import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  static const Color primaryBlue = Color(0xFF2F81F7);
  static const Color primaryGreen = Color(0xFF10B981);
  static const Color primaryAmber = Color(0xFFF59E0B);
  static const Color primaryRed = Color(0xFFEF4444);
  static const Color primaryPurple = Color(0xFF8B5CF6);

  static const Color darkBg = Color(0xFF0D1117);
  static const Color darkSurface = Color(0xFF161B22);
  static const Color darkSurfaceSubtle = Color(0xFF21262D);
  static const Color darkSurfaceElevated = Color(0xFF30363D);
  static const Color darkBorder = Color(0xFF30363D);

  static const Color lightBg = Color(0xFFF8FAFC);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightSurfaceSubtle = Color(0xFFF1F5F9);
  static const Color lightSurfaceElevated = Color(0xFFFFFFFF);
  static const Color lightBorder = Color(0xFFE2E8F0);

  static ThemeData get darkTheme => ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        fontFamily: GoogleFonts.cairo().fontFamily,
        scaffoldBackgroundColor: darkBg,
        primaryColor: primaryBlue,
        colorScheme: const ColorScheme.dark(
          primary: primaryBlue,
          secondary: primaryGreen,
          surface: darkSurface,
          surfaceContainerHighest: darkSurfaceElevated,
          outline: darkBorder,
          error: primaryRed,
        ),
        cardTheme: CardTheme(
          color: darkSurface,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          margin: EdgeInsets.zero,
        ),
        appBarTheme: AppBarTheme(
          backgroundColor: darkSurface,
          foregroundColor: Colors.white,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: GoogleFonts.cairo(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
          iconTheme: const IconThemeData(color: Colors.white),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryBlue,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            textStyle: GoogleFonts.cairo(fontSize: 16, fontWeight: FontWeight.bold),
            elevation: 2,
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: primaryBlue,
            side: const BorderSide(color: primaryBlue, width: 1.5),
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            textStyle: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: darkSurface,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: darkBorder),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: darkBorder),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: primaryBlue, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: primaryRed),
          ),
          labelStyle: GoogleFonts.cairo(color: Colors.grey.shade400, fontSize: 14),
          hintStyle: GoogleFonts.cairo(color: Colors.grey.shade500, fontSize: 14),
        ),
        dialogTheme: DialogTheme(
          backgroundColor: darkSurface,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          titleTextStyle: GoogleFonts.cairo(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          contentTextStyle: GoogleFonts.cairo(fontSize: 14, color: Colors.grey.shade300),
        ),
        bottomSheetTheme: BottomSheetThemeData(
          backgroundColor: darkSurface,
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
        ),
        dividerTheme: DividerThemeData(
          color: darkBorder,
          thickness: 1,
        ),
        chipTheme: ChipThemeData(
          backgroundColor: darkSurfaceSubtle,
          selectedColor: primaryBlue.withOpacity(0.2),
          labelStyle: GoogleFonts.cairo(color: Colors.white, fontSize: 12),
          secondaryLabelStyle: GoogleFonts.cairo(color: primaryBlue, fontSize: 12, fontWeight: FontWeight.bold),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          side: const BorderSide(color: darkBorder),
        ),
        floatingActionButtonTheme: FloatingActionButtonThemeData(
          backgroundColor: primaryBlue,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: darkSurface,
          indicatorColor: primaryBlue.withOpacity(0.15),
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return GoogleFonts.cairo(fontSize: 12, fontWeight: FontWeight.bold, color: primaryBlue);
            }
            return GoogleFonts.cairo(fontSize: 12, color: Colors.grey.shade400);
          }),
        ),
        tabBarTheme: TabBarTheme(
          labelColor: primaryBlue,
          unselectedLabelColor: Colors.grey.shade400,
          indicator: BoxDecoration(
            border: Border(bottom: BorderSide(color: primaryBlue, width: 3)),
          ),
          labelStyle: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.bold),
          unselectedLabelStyle: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.w500),
        ),
        textTheme: TextTheme(
          displayLarge: GoogleFonts.cairo(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white),
          displayMedium: GoogleFonts.cairo(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
          displaySmall: GoogleFonts.cairo(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
          headlineLarge: GoogleFonts.cairo(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
          headlineMedium: GoogleFonts.cairo(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
          headlineSmall: GoogleFonts.cairo(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          titleLarge: GoogleFonts.cairo(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
          titleMedium: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
          titleSmall: GoogleFonts.cairo(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white70),
          bodyLarge: GoogleFonts.cairo(fontSize: 16, color: Colors.white),
          bodyMedium: GoogleFonts.cairo(fontSize: 14, color: Colors.white70),
          bodySmall: GoogleFonts.cairo(fontSize: 12, color: Colors.grey.shade400),
          labelLarge: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
          labelMedium: GoogleFonts.cairo(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white70),
          labelSmall: GoogleFonts.cairo(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.grey.shade400),
        ),
      );

  static ThemeData get lightTheme => ThemeData(
        brightness: Brightness.light,
        useMaterial3: true,
        fontFamily: GoogleFonts.cairo().fontFamily,
        scaffoldBackgroundColor: lightBg,
        primaryColor: primaryBlue,
        colorScheme: const ColorScheme.light(
          primary: primaryBlue,
          secondary: primaryGreen,
          surface: lightSurface,
          surfaceContainerHighest: lightSurfaceElevated,
          outline: lightBorder,
          error: primaryRed,
        ),
        cardTheme: CardTheme(
          color: lightSurface,
          elevation: 1,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          margin: EdgeInsets.zero,
        ),
        appBarTheme: AppBarTheme(
          backgroundColor: lightSurface,
          foregroundColor: Colors.black87,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: GoogleFonts.cairo(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: Colors.black87,
          ),
          iconTheme: const IconThemeData(color: Colors.black87),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryBlue,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            textStyle: GoogleFonts.cairo(fontSize: 16, fontWeight: FontWeight.bold),
            elevation: 2,
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: primaryBlue,
            side: const BorderSide(color: primaryBlue, width: 1.5),
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            textStyle: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: lightSurface,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: lightBorder),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: lightBorder),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: primaryBlue, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: primaryRed),
          ),
          labelStyle: GoogleFonts.cairo(color: Colors.grey.shade600, fontSize: 14),
          hintStyle: GoogleFonts.cairo(color: Colors.grey.shade400, fontSize: 14),
        ),
        dialogTheme: DialogTheme(
          backgroundColor: lightSurface,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
          titleTextStyle: GoogleFonts.cairo(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
          contentTextStyle: GoogleFonts.cairo(fontSize: 14, color: Colors.grey.shade600),
        ),
        bottomSheetTheme: BottomSheetThemeData(
          backgroundColor: lightSurface,
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
        ),
        dividerTheme: DividerThemeData(
          color: lightBorder,
          thickness: 1,
        ),
        chipTheme: ChipThemeData(
          backgroundColor: lightSurfaceSubtle,
          selectedColor: primaryBlue.withOpacity(0.15),
          labelStyle: GoogleFonts.cairo(color: Colors.black87, fontSize: 12),
          secondaryLabelStyle: GoogleFonts.cairo(color: primaryBlue, fontSize: 12, fontWeight: FontWeight.bold),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          side: const BorderSide(color: lightBorder),
        ),
        floatingActionButtonTheme: FloatingActionButtonThemeData(
          backgroundColor: primaryBlue,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: lightSurface,
          indicatorColor: primaryBlue.withOpacity(0.1),
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return GoogleFonts.cairo(fontSize: 12, fontWeight: FontWeight.bold, color: primaryBlue);
            }
            return GoogleFonts.cairo(fontSize: 12, color: Colors.grey.shade600);
          }),
        ),
        tabBarTheme: TabBarTheme(
          labelColor: primaryBlue,
          unselectedLabelColor: Colors.grey.shade600,
          indicator: BoxDecoration(
            border: Border(bottom: BorderSide(color: primaryBlue, width: 3)),
          ),
          labelStyle: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.bold),
          unselectedLabelStyle: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.w500),
        ),
        textTheme: TextTheme(
          displayLarge: GoogleFonts.cairo(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.black87),
          displayMedium: GoogleFonts.cairo(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.black87),
          displaySmall: GoogleFonts.cairo(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.black87),
          headlineLarge: GoogleFonts.cairo(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.black87),
          headlineMedium: GoogleFonts.cairo(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.black87),
          headlineSmall: GoogleFonts.cairo(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
          titleLarge: GoogleFonts.cairo(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.black87),
          titleMedium: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.black87),
          titleSmall: GoogleFonts.cairo(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey.shade600),
          bodyLarge: GoogleFonts.cairo(fontSize: 16, color: Colors.black87),
          bodyMedium: GoogleFonts.cairo(fontSize: 14, color: Colors.grey.shade700),
          bodySmall: GoogleFonts.cairo(fontSize: 12, color: Colors.grey.shade500),
          labelLarge: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black87),
          labelMedium: GoogleFonts.cairo(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey.shade700),
          labelSmall: GoogleFonts.cairo(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.grey.shade500),
        ),
      );
}
