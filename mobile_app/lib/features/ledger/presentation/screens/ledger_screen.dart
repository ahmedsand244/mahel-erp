import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../shared/widgets/placeholder_screen.dart';

class LedgerScreen extends StatelessWidget {
  const LedgerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const PlaceholderScreen(
      title: 'الديون والشكك',
      icon: Icons.menu_book_rounded,
      color: Color(0xFFF59E0B),
    );
  }
}