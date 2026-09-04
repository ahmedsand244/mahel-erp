import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mahel_pos_mobile/features/auth/presentation/screens/login_screen.dart';
import 'package:mahel_pos_mobile/features/auth/presentation/providers/auth_providers.dart';
import 'package:mahel_pos_mobile/features/auth/presentation/screens/tenant_selection_screen.dart';
import 'package:mahel_pos_mobile/features/auth/presentation/screens/pin_lock_screen.dart';
import 'package:mahel_pos_mobile/features/pos/presentation/screens/pos_screen.dart';
import 'package:mahel_pos_mobile/features/dashboard/presentation/screens/dashboard_screen.dart';
import 'package:mahel_pos_mobile/features/inventory/presentation/screens/inventory_screen.dart';
import 'package:mahel_pos_mobile/features/ledger/presentation/screens/ledger_screen.dart';
import 'package:mahel_pos_mobile/features/maintenance/presentation/screens/maintenance_screen.dart';
import 'package:mahel_pos_mobile/features/expenses/presentation/screens/expenses_screen.dart';
import 'package:mahel_pos_mobile/features/reports/presentation/screens/reports_screen.dart';
import 'package:mahel_pos_mobile/features/settings/presentation/screens/settings_screen.dart';
import 'package:mahel_pos_mobile/shared/widgets/main_scaffold.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);
  
  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) {
      final isLoggedIn = authState.isAuthenticated;
      final isLoginRoute = state.matchedLocation == '/login';
      final isTenantRoute = state.matchedLocation == '/tenant-selection';
      final isPinRoute = state.matchedLocation == '/pin-lock';
      
      if (!isLoggedIn && !isLoginRoute && !isTenantRoute) {
        return '/login';
      }
      
      if (isLoggedIn && isLoginRoute) {
        return '/tenant-selection';
      }
      
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/tenant-selection',
        builder: (context, state) => const TenantSelectionScreen(),
      ),
      GoRoute(
        path: '/pin-lock',
        builder: (context, state) => const PinLockScreen(),
      ),
      ShellRoute(
        builder: (context, state, child) => MainScaffold(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            builder: (context, state) => const DashboardScreen(),
          ),
          GoRoute(
            path: '/pos',
            builder: (context, state) => const PosScreen(),
          ),
          GoRoute(
            path: '/inventory',
            builder: (context, state) => const InventoryScreen(),
          ),
          GoRoute(
            path: '/ledger',
            builder: (context, state) => const LedgerScreen(),
          ),
          GoRoute(
            path: '/maintenance',
            builder: (context, state) => const MaintenanceScreen(),
          ),
          GoRoute(
            path: '/expenses',
            builder: (context, state) => const ExpensesScreen(),
          ),
          GoRoute(
            path: '/reports',
            builder: (context, state) => const ReportsScreen(),
          ),
          GoRoute(
            path: '/settings',
            builder: (context, state) => const SettingsScreen(),
          ),
        ],
      ),
    ],
  );
});
