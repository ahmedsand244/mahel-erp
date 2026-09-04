import 'package:drift/drift.dart';
import '../../app_database.dart';

class PurchaseOrderDao {
  final AppDatabase db;
  PurchaseOrderDao(this.db);

  Future<List<PurchaseOrder>> getAllPurchaseOrders({int? tenantId, String? status}) {
    final query = select(db.purchaseOrders)..where((p) => p.deletedAt.isNull());
    if (tenantId != null) {
      query.where((p) => p.tenantId.equals(tenantId));
    }
    if (status != null && status.isNotEmpty) {
      query.where((p) => p.status.equals(status));
    }
    return query.orderBy([OrderingTerm.desc(db.purchaseOrders.createdAt)]).get();
  }

  Future<PurchaseOrder?> getPurchaseOrderById(int id) =>
      (select(db.purchaseOrders)..where((p) => p.id.equals(id) & p.deletedAt.isNull())).getSingleOrNull();

  Future<List<PurchaseOrderItem>> getPurchaseOrderItems(int orderId) =>
      (select(db.purchaseOrderItems)
            ..where((i) => i.purchaseOrderId.equals(orderId) & i.deletedAt.isNull()))
          .get();

  Future<int> insertPurchaseOrder(PurchaseOrdersCompanion order) => into(db.purchaseOrders).insert(order);

  Future<bool> updatePurchaseOrder(PurchaseOrdersCompanion order) => update(db.purchaseOrders).replace(order);

  Future<int> insertPurchaseOrderWithItems(PurchaseOrdersCompanion order, List<PurchaseOrderItemsCompanion> items) {
    return transaction(() async {
      final orderId = await into(db.purchaseOrders).insert(order);
      for (final item in items) {
        await into(db.purchaseOrderItems).insert(PurchaseOrderItemsCompanion(
          purchaseOrderId: Value(orderId),
          productId: item.productId,
          customItemName: item.customItemName,
          supplierId: item.supplierId,
          quantityRequested: item.quantityRequested,
          unitCost: item.unitCost,
        ));
      }
      return orderId;
    });
  }

  Future<int> receivePurchaseOrder(int orderId) {
    return transaction(() async {
      final order = await getPurchaseOrderById(orderId);
      if (order == null || order.status == 'received') return 0;

      final items = await getPurchaseOrderItems(orderId);
      for (final item in items) {
        if (item.productId != null && !item.isReceived) {
          await (update(db.products)
                ..where((p) => p.id.equals(item.productId!)))
              .write(ProductsCompanion(
                stockQuantity: Value((item.productId != null
                        ? (await (select(db.products)..where((p) => p.id.equals(item.productId!))).getSingle()).stockQuantity
                        : 0) +
                    item.quantityRequested),
                lastModified: Value(DateTime.now()),
                syncStatus: const Value('pending'),
              ));

          await (update(db.purchaseOrderItems)
                ..where((i) => i.id.equals(item.id)))
              .write(PurchaseOrderItemsCompanion(
                isReceived: const Value(true),
                lastModified: Value(DateTime.now()),
                syncStatus: const Value('pending'),
              ));
        }
      }

      await (update(db.purchaseOrders)
            ..where((p) => p.id.equals(orderId)))
        .write(PurchaseOrdersCompanion(
          status: const Value('received'),
          receivedAt: Value(DateTime.now()),
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('pending'),
        ));

      return items.where((i) => i.productId != null && !i.isReceived).length;
    });
  }
}