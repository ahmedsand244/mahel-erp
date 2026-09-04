import 'package:freezed_annotation/freezed_annotation.dart';

part 'auth_state.freezed.dart';

@freezed
class AuthState with _$AuthState {
  const AuthState._();

  const factory AuthState.authenticated({
    required String accessToken,
    required String refreshToken,
    required String tenantSlug,
    required String tenantName,
    required String username,
    required String userId,
  }) = _Authenticated;

  const factory AuthState.unauthenticated() = _Unauthenticated;

  const factory AuthState.loading() = _Loading;

  const factory AuthState.error(String message) = _Error;

  bool get isAuthenticated => this is _Authenticated;
  
  String? get tenantSlug => when(
    authenticated: (_, __, slug, ___, ____, _____) => slug,
    unauthenticated: () => null,
    loading: () => null,
    error: (_) => null,
  );
}