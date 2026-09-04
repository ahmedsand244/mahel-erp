import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class StockAlertDao {
  final AppDatabase db;
  StockAlertDao(this.db);

  Future<List<StockAlert>> getUnresolvedAlerts({int? tenantId}) {
    final query = select(db.stockAlerts)..where((a) => a.isResolved.equals(false) & a.deletedAt.isNull());
    // Note: tenant filtering would require joining with products table
    return query.orderBy([OrderingTerm.desc(db.stockAlerts.createdAt)]).get();
  }

  Future<int> createAlert(StockAlertsCompanion alert) => into(db.stockAlerts).insert(alert);

  Future<int> resolveAlert(int alertId) {
    return (update(db.stockAlerts)
          ..where((a) => a.id.equals(alertId)))
        .write(StockAlertsCompanion(
          isResolved: const Value(true),
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('pending'),
        ));
  }

  Future<int> resolveAlertsForProduct(int productId) {
    return (update(db.stockAlerts)
          ..where((a) => a.productId.equals(productId) & a.isResolved.equals(false)))
        .write(StockAlertsCompanion(
          isResolved: const Value(true),
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('pending'),
        ));
  }
}
