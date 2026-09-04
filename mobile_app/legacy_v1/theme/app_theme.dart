import 'package:flutter/material.dart';

class AppColors {
  static const Color background = Color(0xFF0D1117);
  static const Color surface = Color(0xFF161B22);
  static const Color surfaceElevated = Color(0xFF21262D);
  static const Color border = Color(0xFF30363D);

  static const Color primary = Color(0xFF2F81F7);
  static const Color primarySubtle = Color(0x1A2F81F7);

  static const Color success = Color(0xFF10B981);
  static const Color successSubtle = Color(0x1A10B981);

  static const Color danger = Color(0xFFEF4444);
  static const Color dangerSubtle = Color(0x1AEF4444);

  static const Color warning = Color(0xFFF59E0B);
  static const Color warningSubtle = Color(0x1AF59E0B);

  static const Color textPrimary = Color(0xFFF0F6FC);
  static const Color textSecondary = Color(0xFF8B949E);
}

class AppStyles {
  static BoxDecoration glassCard({Color? border, Color? color}) {
    return BoxDecoration(
      color: color ?? AppColors.surface,
      borderRadius: BorderRadius.circular(20),
      border: Border.all(
        color: border ?? AppColors.border,
        width: 1,
      ),
      boxShadow: const [
        BoxShadow(
          color: Colors.black26,
          blurRadius: 10,
          offset: Offset(0, 4),
        ),
      ],
    );
  }

  static BoxDecoration primaryGradientCard() {
    return BoxDecoration(
      gradient: const LinearGradient(
        colors: [Color(0xFF2F81F7), Color(0xFF1F6FEB)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      borderRadius: BorderRadius.circular(20),
      boxShadow: [
        BoxShadow(
          color: const Color(0xFF2F81F7).withOpacity(0.35),
          blurRadius: 15,
          offset: const Offset(0, 6),
        ),
      ],
    );
  }
}
