import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mahel_pos_mobile/core/router/app_router.dart';

class MainScaffold extends ConsumerWidget {
  final Widget child;

  const MainScaffold({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final currentLocation = router.routerDelegate.currentConfiguration.uri.toString();

    int currentIndex = 0;
    if (currentLocation.startsWith('/pos')) currentIndex = 1;
    else if (currentLocation.startsWith('/inventory')) currentIndex = 2;
    else if (currentLocation.startsWith('/ledger')) currentIndex = 3;
    else if (currentLocation.startsWith('/maintenance')) currentIndex = 4;
    else if (currentLocation.startsWith('/expenses')) currentIndex = 5;
    else if (currentLocation.startsWith('/reports')) currentIndex = 6;
    else if (currentLocation.startsWith('/settings')) currentIndex = 7;
    else currentIndex = 0; // dashboard

    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) {
          switch (index) {
            case 0:
              router.go('/dashboard');
              break;
            case 1:
              router.go('/pos');
              break;
            case 2:
              router.go('/inventory');
              break;
            case 3:
              router.go('/ledger');
              break;
            case 4:
              router.go('/maintenance');
              break;
            case 5:
              router.go('/expenses');
              break;
            case 6:
              router.go('/reports');
              break;
            case 7:
              router.go('/settings');
              break;
          }
        },
        destinations: [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard_rounded),
            label: 'Ù„ÙˆØ­Ø© Ø§Ù„Ù‚ÙŠØ§Ø¯Ø©',
          ),
          NavigationDestination(
            icon: Icon(Icons.point_of_sale_outlined),
            selectedIcon: Icon(Icons.point_of_sale_rounded),
            label: 'POS',
          ),
          NavigationDestination(
            icon: Icon(Icons.inventory_2_outlined),
            selectedIcon: Icon(Icons.inventory_2_rounded),
            label: 'Ø§Ù„Ù…Ø®Ø²Ù†',
          ),
          NavigationDestination(
            icon: Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(Icons.menu_book_rounded),
            label: 'Ø§Ù„Ø¯ÙŠÙˆÙ†',
          ),
          NavigationDestination(
            icon: Icon(Icons.build_outlined),
            selectedIcon: Icon(Icons.build_rounded),
            label: 'Ø§Ù„ØµÙŠØ§Ù†Ø©',
          ),
          NavigationDestination(
            icon: Icon(Icons.payments_outlined),
            selectedIcon: Icon(Icons.payments_rounded),
            label: 'Ø§Ù„Ù…ØµØ±ÙˆÙØ§Øª',
          ),
          NavigationDestination(
            icon: Icon(Icons.analytics_outlined),
            selectedIcon: Icon(Icons.analytics_rounded),
            label: 'Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ±',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings_rounded),
            label: 'Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª',
          ),
        ],
      ),
    );
  }
}
