import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class StockAlertDao extends DatabaseAccessor<AppDatabase> {
  StockAlertDao(super.db);
  AppDatabase get db => attachedDatabase;

  Future<List<StockAlert>> getUnresolvedAlerts({int? tenantId}) {
    final query = select(db.stockAlerts)..where((a) => a.isResolved.equals(false) & a.deletedAt.isNull());
    query.orderBy([(a) => OrderingTerm.desc(a.createdAt)]);
    return query.get();
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

