import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class TenantDao extends DatabaseAccessor<AppDatabase> {
  TenantDao(super.db);
  AppDatabase get db => attachedDatabase;

  Future<List<Tenant>> getAllTenants() => select(db.tenants).get();

  Future<Tenant?> getTenantBySlug(String slug) =>
      (select(db.tenants)..where((t) => t.slug.equals(slug))).getSingleOrNull();

  Future<Tenant?> getTenantById(int id) =>
      (select(db.tenants)..where((t) => t.id.equals(id))).getSingleOrNull();

  Future<int> insertTenant(TenantsCompanion tenant) => into(db.tenants).insert(tenant);

  Future<bool> updateTenant(TenantsCompanion tenant) => update(db.tenants).replace(tenant);

  Future<int> deleteTenant(int id) => (delete(db.tenants)..where((t) => t.id.equals(id))).go();

  Future<List<Tenant>> getActiveTenants() =>
      (select(db.tenants)..where((t) => t.isActive.equals(true) & t.deletedAt.isNull())).get();

  Stream<List<Tenant>> watchActiveTenants() =>
      (select(db.tenants)..where((t) => t.isActive.equals(true) & t.deletedAt.isNull())).watch();

  Future<int> upsertTenant(TenantsCompanion tenant) {
    return transaction(() async {
      final existing = await getTenantBySlug(tenant.slug.value);
      if (existing != null) {
        return update(db.tenants).replace(TenantsCompanion(
          id: Value(existing.id),
          name: tenant.name,
          slug: tenant.slug,
          ownerId: tenant.ownerId,
          plan: tenant.plan,
          trialEndsAt: tenant.trialEndsAt,
          isActive: tenant.isActive,
          phone: tenant.phone,
          address: tenant.address,
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('synced'),
        ));
      } else {
        return into(db.tenants).insert(tenant);
      }
    });
  }
}

