import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../shared/models/api_models.dart';

class ApiService {
  final Dio _dio;
  final FlutterSecureStorage _storage;
  String _baseUrl;
  String? _accessToken;
  String? _refreshToken;
  String? _tenantSlug;

  ApiService({
    required String baseUrl,
    required FlutterSecureStorage storage,
  })  : _baseUrl = baseUrl,
        _storage = storage,
        _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 30),
          headers: {'Content-Type': 'application/json'},
        )) {
    _setupInterceptors();
  }

  String get baseUrl => _baseUrl;
  String? get accessToken => _accessToken;
  String? get tenantSlug => _tenantSlug;
  bool get isAuthenticated => _accessToken != null;

  void _setupInterceptors() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (_accessToken != null) {
          options.headers['Authorization'] = 'Bearer $_accessToken';
        }
        if (_tenantSlug != null) {
          options.headers['X-Tenant-Slug'] = _tenantSlug;
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401 && _refreshToken != null) {
          final refreshed = await _refreshAccessToken();
          if (refreshed) {
            return handler.resolve(await _retryRequest(error.requestOptions));
          }
        }
        return handler.next(error);
      },
    ));
  }

  Future<bool> _refreshAccessToken() async {
    try {
      final response = await _dio.post('/api/v1/token/refresh/', data: {
        'refresh': _refreshToken,
      });
      _accessToken = response.data['access'];
      await _storage.write(key: 'access_token', value: _accessToken);
      return true;
    } catch (e) {
      await logout();
      return false;
    }
  }

  Future<Response> _retryRequest(RequestOptions options) async {
    options.headers['Authorization'] = 'Bearer $_accessToken';
    return _dio.fetch(options);
  }

  Future<void> initialize() async {
    _accessToken = await _storage.read(key: 'access_token');
    _refreshToken = await _storage.read(key: 'refresh_token');
    _tenantSlug = await _storage.read(key: 'tenant_slug');
    _baseUrl = await _storage.read(key: 'base_url') ?? _baseUrl;
  }

  Future<LoginResponse> login({
    required String username,
    required String password,
    required String tenantSlug,
  }) async {
    try {
      final response = await _dio.post('/api/v1/login/', data: {
        'username': username,
        'password': password,
        'tenant_slug': tenantSlug,
      });

      final loginResponse = LoginResponse.fromJson(response.data);

      if (loginResponse.success && loginResponse.access != null) {
        _accessToken = loginResponse.access!;
        _refreshToken = loginResponse.refresh;
        _tenantSlug = loginResponse.tenant?.slug ?? tenantSlug;

        await _storage.write(key: 'access_token', value: _accessToken);
        if (_refreshToken != null) {
          await _storage.write(key: 'refresh_token', value: _refreshToken!);
        }
        await _storage.write(key: 'tenant_slug', value: _tenantSlug);
        await _storage.write(key: 'username', value: username);
        await _storage.write(key: 'base_url', value: _baseUrl);
      }

      return loginResponse;
    } on DioException catch (e) {
      return LoginResponse(
        success: false,
        error: e.response?.data?['error'] ?? 'فشل الاتصال بالخادم: ${e.message}',
      );
    }
  }

  Future<ProductsResponse> fetchProducts({String? tenantSlug}) async {
    try {
      final response = await _dio.get('/api/v1/products/', queryParameters: {
        'tenant_slug': tenantSlug ?? _tenantSlug,
      });
      return ProductsResponse.fromJson(response.data);
    } on DioException catch (e) {
      return ProductsResponse(success: false, error: e.message);
    }
  }

  Future<CustomersResponse> fetchCustomers({String? tenantSlug}) async {
    try {
      final response = await _dio.get('/api/v1/customers/', queryParameters: {
        'tenant_slug': tenantSlug ?? _tenantSlug,
      });
      return CustomersResponse.fromJson(response.data);
    } on DioException catch (e) {
      return CustomersResponse(success: false, error: e.message);
    }
  }

  Future<SyncResponse> syncInvoices({
    required String tenantSlug,
    required List<Map<String, dynamic>> invoices,
  }) async {
    try {
      final response = await _dio.post('/api/v1/invoices/sync/', data: {
        'tenant_slug': tenantSlug,
        'invoices': invoices,
      });
      return SyncResponse.fromJson(response.data);
    } on DioException catch (e) {
      return SyncResponse(success: false, error: e.message);
    }
  }

  Future<FullSyncResponse> fullSync({
    required String tenantSlug,
    required List<Map<String, dynamic>> customers,
    required List<Map<String, dynamic>> suppliers,
    required List<Map<String, dynamic>> products,
    required List<Map<String, dynamic>> invoices,
    required List<Map<String, dynamic>> expenses,
  }) async {
    try {
      final response = await _dio.post('/api/v1/sync/full/', data: {
        'tenant_slug': tenantSlug,
        'customers': customers,
        'suppliers': suppliers,
        'products': products,
        'invoices': invoices,
        'expenses': expenses,
      });
      return FullSyncResponse.fromJson(response.data);
    } on DioException catch (e) {
      return FullSyncResponse(success: false, error: e.message);
    }
  }

  Future<DashboardResponse> fetchDashboardSummary({String? tenantSlug}) async {
    try {
      final response = await _dio.get('/api/v1/dashboard/', queryParameters: {
        'tenant_slug': tenantSlug ?? _tenantSlug,
      });
      return DashboardResponse.fromJson(response.data);
    } on DioException catch (e) {
      return DashboardResponse(success: false, error: e.message);
    }
  }

  Future<void> logout() async {
    _accessToken = null;
    _refreshToken = null;
    _tenantSlug = null;
    await _storage.deleteAll();
  }

  void updateBaseUrl(String url) {
    _baseUrl = url;
    _dio.options.baseUrl = url;
    _storage.write(key: 'base_url', value: url);
  }
}