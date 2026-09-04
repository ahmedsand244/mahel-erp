import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../shared/widgets/placeholder_screen.dart';

class InventoryScreen extends StatelessWidget {
  const InventoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const PlaceholderScreen(
      title: 'إدارة المخزن',
      icon: Icons.inventory_2_rounded,
      color: Color(0xFF10B981),
    );
  }
}