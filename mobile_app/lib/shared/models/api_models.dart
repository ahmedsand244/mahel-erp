import 'package:freezed_annotation/freezed_annotation.dart';

part 'api_models.freezed.dart';
part 'api_models.g.dart';

@freezed
class LoginResponse with _$LoginResponse {
  const factory LoginResponse({
    required bool success,
    String? error,
    User? user,
    TenantInfo? tenant,
    String? access,
    String? refresh,
  }) = _LoginResponse;

  factory LoginResponse.fromJson(Map<String, dynamic> json) => _$LoginResponseFromJson(json);
}

@freezed
class User with _$User {
  const factory User({
    required int id,
    required String username,
    String? firstName,
    String? lastName,
    String? email,
  }) = _User;

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
}

@freezed
class TenantInfo with _$TenantInfo {
  const factory TenantInfo({
    required int id,
    required String name,
    required String slug,
    required String plan,
  }) = _TenantInfo;

  factory TenantInfo.fromJson(Map<String, dynamic> json) => _$TenantInfoFromJson(json);
}

@freezed
class ProductsResponse with _$ProductsResponse {
  const factory ProductsResponse({
    required bool success,
    String? error,
    int? count,
    @Default([]) List<ProductApi> products,
  }) = _ProductsResponse;

  factory ProductsResponse.fromJson(Map<String, dynamic> json) => _$ProductsResponseFromJson(json);
}

@freezed
class ProductApi with _$ProductApi {
  const factory ProductApi({
    required int id,
    required String name,
    String? sku,
    String? barcode,
    required double salePrice,
    required double costPrice,
    required int stockQuantity,
    String? unit,
    String? categoryName,
  }) = _ProductApi;

  factory ProductApi.fromJson(Map<String, dynamic> json) => _$ProductApiFromJson(json);
}

@freezed
class CustomersResponse with _$CustomersResponse {
  const factory CustomersResponse({
    required bool success,
    String? error,
    int? count,
    @Default([]) List<CustomerApi> customers,
  }) = _CustomersResponse;

  factory CustomersResponse.fromJson(Map<String, dynamic> json) => _$CustomersResponseFromJson(json);
}

@freezed
class CustomerApi with _$CustomerApi {
  const factory CustomerApi({
    required int id,
    required String name,
    String? phone,
    required double balance,
  }) = _CustomerApi;

  factory CustomerApi.fromJson(Map<String, dynamic> json) => _$CustomerApiFromJson(json);
}

@freezed
class SyncResponse with _$SyncResponse {
  const factory SyncResponse({
    required bool success,
    String? error,
    int? syncedCount,
    @Default([]) List<SyncedItem> synced,
    @Default([]) List<String> errors,
  }) = _SyncResponse;

  factory SyncResponse.fromJson(Map<String, dynamic> json) => _$SyncResponseFromJson(json);
}

@freezed
class SyncedItem with _$SyncedItem {
  const factory SyncedItem({
    String? clientId,
    String? serverOrderNumber,
    int? serverOrderId,
  }) = _SyncedItem;

  factory SyncedItem.fromJson(Map<String, dynamic> json) => _$SyncedItemFromJson(json);
}

@freezed
class FullSyncResponse with _$FullSyncResponse {
  const factory FullSyncResponse({
    required bool success,
    String? error,
    String? message,
    SyncStats? stats,
  }) = _FullSyncResponse;

  factory FullSyncResponse.fromJson(Map<String, dynamic> json) => _$FullSyncResponseFromJson(json);
}

@freezed
class SyncStats with _$SyncStats {
  const factory SyncStats({
    required int products,
    required int customers,
    required int suppliers,
    required int invoices,
    required int expenses,
  }) = _SyncStats;

  factory SyncStats.fromJson(Map<String, dynamic> json) => _$SyncStatsFromJson(json);
}

@freezed
class DashboardResponse with _$DashboardResponse {
  const factory DashboardResponse({
    required bool success,
    String? error,
    @Default(0.0) double todaySales,
    @Default(0) int todayOrdersCount,
    @Default(0) int lowStockCount,
    @Default(0) int totalProducts,
  }) = _DashboardResponse;

  factory DashboardResponse.fromJson(Map<String, dynamic> json) => _$DashboardResponseFromJson(json);
}