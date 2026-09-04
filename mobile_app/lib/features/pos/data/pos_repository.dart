import 'package:decimal/decimal.dart';
import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/database_service.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';
import 'package:mahel_pos_mobile/features/pos/domain/pos_models.dart';

class PosRepository {
  final DatabaseService _db;

  PosRepository(this._db);

  Future<int> createOrder({
    required String orderNumber,
    required String paymentMethod,
    int? customerId,
    required List<CartItem> items,
    required Decimal totalAmount,
    required Decimal costOfGoodsSold,
    int? tenantId,
  }) {
    return _db.database.transaction(() async {
      final orderId = await _db.orders.insertOrder(OrdersCompanion(
        orderNumber: Value(orderNumber),
        customerId: customerId != null ? Value(customerId) : const Value.absent(),
        paymentMethod: Value(paymentMethod),
        totalAmount: Value(totalAmount.toDouble()),
        costOfGoodsSold: Value(costOfGoodsSold.toDouble()),
        tenantId: tenantId != null ? Value(tenantId) : const Value.absent(),
        syncStatus: const Value('pending'),
        lastModified: Value(DateTime.now()),
      ));

      for (final item in items) {
        await _db.database.into(_db.database.orderItems).insert(OrderItemsCompanion(
          orderId: Value(orderId),
          productId: Value(item.productId),
          quantity: Value(item.quantity),
          unitPrice: Value(item.price.toDouble()),
          cost: const Value(0.0), // Will be calculated from product
          syncStatus: const Value('pending'),
          lastModified: Value(DateTime.now()),
        ));

        // Deduct stock
        final product = await _db.products.getProductById(item.productId);
        if (product != null) {
          await _db.products.updateStock(item.productId, (product.stockQuantity - item.quantity).clamp(0, 999999));
        }
      }

      // Update customer balance if deferred
      if (paymentMethod == 'deferred' && customerId != null) {
        final customer = await _db.customers.getCustomerById(customerId);
        if (customer != null) {
          await _db.customers.updateBalance(customerId, customer.balance + totalAmount.toDouble());
          await _db.transactions.insertTransaction(TransactionsCompanion(
            customerId: Value(customerId),
            amount: Value(totalAmount.toDouble()),
            transactionType: const Value('sale_credit'),
            tenantId: tenantId != null ? Value(tenantId) : const Value.absent(),
            syncStatus: const Value('pending'),
            lastModified: Value(DateTime.now()),
          ));
        }
      }

      return orderId;
    });
  }

  Future<void> saveOfflineInvoice(OfflineInvoice invoice) async {
    // Save to local storage for sync later
    // This would use shared_preferences or a local table
  }

  Future<List<OfflineInvoice>> getPendingInvoices() async {
    // Retrieve from local storage
    return [];
  }

  Future<void> markInvoiceSynced(String clientId) async {
    // Mark as synced in local storage
  }
}
