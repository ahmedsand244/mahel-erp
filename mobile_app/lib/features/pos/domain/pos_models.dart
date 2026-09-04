import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:decimal/decimal.dart';

part 'pos_models.freezed.dart';
part 'pos_models.g.dart';

@freezed
class CartItem with _$CartItem {
  const CartItem._();

  const factory CartItem({
    required int productId,
    required String name,
    required Decimal price,
    required int quantity,
    int? customerId,
  }) = _CartItem;

  factory CartItem.fromJson(Map<String, dynamic> json) => _$CartItemFromJson(json);

  Decimal get totalPrice => price * Decimal.fromInt(quantity);
}

@freezed
class PaymentMethod with _$PaymentMethod {
  const PaymentMethod._();

  const factory PaymentMethod.cash() = _Cash;
  const factory PaymentMethod.visa() = _Visa;
  const factory PaymentMethod.deferred() = _Deferred;

  String get displayName => when(
    cash: () => 'نقداً',
    visa: () => 'بطاقة / شبكة',
    deferred: () => 'آجل / شكك',
  );

  String get icon => when(
    cash: () => 'payments',
    visa: () => 'credit_card',
    deferred: () => 'history_edu',
  );
}

@freezed
class OfflineInvoice with _$OfflineInvoice {
  const factory OfflineInvoice({
    required String clientId,
    required String orderNumber,
    required String paymentMethod,
    int? customerId,
    required List<CartItem> items,
    required Decimal totalAmount,
    required DateTime createdAt,
    bool isSynced,
  }) = _OfflineInvoice;

  factory OfflineInvoice.fromJson(Map<String, dynamic> json) => _$OfflineInvoiceFromJson(json);
}