import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class StoreAuditDao extends DatabaseAccessor<AppDatabase> {
  StoreAuditDao(super.db);
  AppDatabase get db => attachedDatabase;

  Future<List<StoreAudit>> getAllAudits({int? tenantId}) {
    final query = select(db.storeAudits)..where((a) => a.deletedAt.isNull());
    if (tenantId != null) {
      query.where((a) => a.tenantId.equals(tenantId));
    }
    return query.orderBy([OrderingTerm.desc(db.storeAudits.createdAt)]).get();
  }

  Future<StoreAudit?> getAuditById(int id) =>
      (select(db.storeAudits)..where((a) => a.id.equals(id) & a.deletedAt.isNull())).getSingleOrNull();

  Future<int> insertAudit(StoreAuditsCompanion audit) => into(db.storeAudits).insert(audit);

  Future<bool> updateAudit(StoreAuditsCompanion audit) => update(db.storeAudits).replace(audit);

  Future<int> deleteAudit(int id) =>
      (delete(db.storeAudits)..where((a) => a.id.equals(id))).go();
}

