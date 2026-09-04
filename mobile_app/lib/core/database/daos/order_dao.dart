import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class OrderDao extends DatabaseAccessor<AppDatabase> {
  OrderDao(super.db);
  AppDatabase get db => attachedDatabase;

  Future<List<Order>> getAllOrders({int? tenantId, DateTime? startDate, DateTime? endDate}) {
    final query = select(db.orders)..where((o) => o.deletedAt.isNull());
    if (tenantId != null) {
      query.where((o) => o.tenantId.equals(tenantId));
    }
    if (startDate != null) {
      query.where((o) => o.createdAt.isBiggerOrEqualValue(startDate));
    }
    if (endDate != null) {
      query.where((o) => o.createdAt.isSmallerOrEqualValue(endDate));
    }
    query.orderBy([(o) => OrderingTerm.desc(o.createdAt)]);
    return query.get();
  }

  Future<Order?> getOrderById(int id) =>
      (select(db.orders)..where((o) => o.id.equals(id) & o.deletedAt.isNull())).getSingleOrNull();

  Future<Order?> getOrderByNumber(String orderNumber) =>
      (select(db.orders)..where((o) => o.orderNumber.equals(orderNumber) & o.deletedAt.isNull())).getSingleOrNull();

  Future<List<Order>> getOrdersByCustomer(int customerId) =>
      (select(db.orders)
            ..where((o) => o.customerId.equals(customerId) & o.deletedAt.isNull())
            ..orderBy([(o) => OrderingTerm.desc(o.createdAt)]))
          .get();

  Future<int> insertOrder(OrdersCompanion order) => into(db.orders).insert(order);

  Future<bool> updateOrder(OrdersCompanion order) => update(db.orders).replace(order);

  Future<int> insertOrderWithItems(OrdersCompanion order, List<OrderItemsCompanion> items) {
    return transaction(() async {
      final orderId = await into(db.orders).insert(order);
      for (final item in items) {
        await into(db.orderItems).insert(OrderItemsCompanion(
          orderId: Value(orderId),
          productId: item.productId,
          quantity: item.quantity,
          unitPrice: item.unitPrice,
          cost: item.cost,
        ));
      }
      return orderId;
    });
  }

  Future<List<OrderItem>> getOrderItems(int orderId) =>
      (select(db.orderItems)..where((i) => i.orderId.equals(orderId) & i.deletedAt.isNull())).get();

  Future<Map<String, dynamic>> getSalesSummary({
    int? tenantId,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final orders = await getAllOrders(tenantId: tenantId, startDate: startDate, endDate: endDate);
    double totalSales = 0;
    double totalCogs = 0;
    int cashCount = 0;
    int visaCount = 0;
    int deferredCount = 0;
    double cashSales = 0;
    double visaSales = 0;
    double deferredSales = 0;

    for (final o in orders) {
      totalSales += o.totalAmount;
      totalCogs += o.costOfGoodsSold;
      switch (o.paymentMethod) {
        case 'cash':
          cashCount++;
          cashSales += o.totalAmount;
          break;
        case 'visa':
          visaCount++;
          visaSales += o.totalAmount;
          break;
        case 'deferred':
          deferredCount++;
          deferredSales += o.totalAmount;
          break;
      }
    }

    return {
      'totalSales': totalSales,
      'totalCogs': totalCogs,
      'totalProfit': totalSales - totalCogs,
      'ordersCount': orders.length,
      'cashCount': cashCount,
      'visaCount': visaCount,
      'deferredCount': deferredCount,
      'cashSales': cashSales,
      'visaSales': visaSales,
      'deferredSales': deferredSales,
    };
  }

  Stream<List<Order>> watchRecentOrders({int? tenantId, int limit = 10}) {
    final query = select(db.orders)
      ..where((o) => o.deletedAt.isNull())
      ..orderBy([(o) => OrderingTerm.desc(o.createdAt)])
      ..limit(limit);
    if (tenantId != null) {
      query.where((o) => o.tenantId.equals(tenantId));
    }
    return query.watch();
  }
}

