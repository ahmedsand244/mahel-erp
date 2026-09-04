import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/auth_repository.dart';
import '../../domain/auth_state.dart';
import 'package:mahel_pos_mobile/core/network/api_service.dart';
import 'package:mahel_pos_mobile/core/storage/secure_storage_service.dart';
import 'package:mahel_pos_mobile/core/database/database_service.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    ref.watch(apiServiceProvider),
    ref.watch(secureStorageProvider),
  );
});

final authStateProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(authRepositoryProvider));
});

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _repository;

  AuthNotifier(this._repository) : super(const AuthState.unauthenticated()) {
    _tryAutoLogin();
  }

  Future<void> _tryAutoLogin() async {
    state = const AuthState.loading();
    final savedState = await _repository.tryAutoLogin();
    if (savedState != null) {
      state = savedState;
    } else {
      state = const AuthState.unauthenticated();
    }
  }

  Future<void> login({
    required String username,
    required String password,
    required String tenantSlug,
  }) async {
    state = const AuthState.loading();
    final result = await _repository.login(
      username: username,
      password: password,
      tenantSlug: tenantSlug,
    );
    state = result;
  }

  Future<void> logout() async {
    await _repository.logout();
    state = const AuthState.unauthenticated();
  }

  Future<void> switchTenant(String tenantSlug, String tenantName) async {
    await _repository.updateTenant(tenantSlug, tenantName);
    if (state is _Authenticated) {
      final current = state as _Authenticated;
      state = AuthState.authenticated(
        accessToken: current.accessToken,
        refreshToken: current.refreshToken,
        tenantSlug: tenantSlug,
        tenantName: tenantName,
        username: current.username,
        userId: current.userId,
      );
    }
  }
}

final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService(
    baseUrl: 'https://webservises.pythonanywhere.com',
    storage: SecureStorageService.secureStorage,
  );
});

final secureStorageProvider = Provider<SecureStorageService>((ref) {
  return SecureStorageService();
});

final databaseServiceProvider = Provider<DatabaseService>((ref) {
  return DatabaseService(AppDatabase());
});
