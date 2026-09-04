import 'package:dio/dio.dart';
import '../../core/network/api_service.dart';
import '../../core/storage/secure_storage_service.dart';
import '../domain/auth_state.dart';

class AuthRepository {
  final ApiService _api;
  final SecureStorageService _storage;

  AuthRepository(this._api, this._storage);

  Future<AuthState> login({
    required String username,
    required String password,
    required String tenantSlug,
  }) async {
    final response = await _api.login(
      username: username,
      password: password,
      tenantSlug: tenantSlug,
    );

    if (response.success && response.access != null) {
      return AuthState.authenticated(
        accessToken: response.access!,
        refreshToken: response.refresh ?? '',
        tenantSlug: response.tenant?.slug ?? tenantSlug,
        tenantName: response.tenant?.name ?? '',
        username: response.user?.username ?? username,
        userId: response.user?.id.toString() ?? '',
      );
    } else {
      return AuthState.error(response.error ?? 'فشل تسجيل الدخول');
    }
  }

  Future<void> logout() async {
    await _api.logout();
  }

  Future<AuthState?> tryAutoLogin() async {
    await _api.initialize();
    if (_api.isAuthenticated) {
      final tenantSlug = await _storage.readSecure('tenant_slug');
      final username = await _storage.readSecure('username');
      if (tenantSlug != null && username != null) {
        return AuthState.authenticated(
          accessToken: _api.accessToken!,
          refreshToken: _api.refreshToken ?? '',
          tenantSlug: tenantSlug,
          tenantName: '',
          username: username,
          userId: '',
        );
      }
    }
    return null;
  }

  Future<void> updateTenant(String tenantSlug, String tenantName) async {
    await _storage.writeSecure('tenant_slug', tenantSlug);
    _api._tenantSlug = tenantSlug;
  }
}