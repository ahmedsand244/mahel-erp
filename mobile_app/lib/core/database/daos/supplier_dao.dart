import 'package:drift/drift.dart';
import '../../app_database.dart';

class SupplierDao {
  final AppDatabase db;
  SupplierDao(this.db);

  Future<List<Supplier>> getAllSuppliers({int? tenantId}) {
    final query = select(db.suppliers)..where((s) => s.deletedAt.isNull());
    if (tenantId != null) {
      query.where((s) => s.tenantId.equals(tenantId));
    }
    return query.get();
  }

  Future<Supplier?> getSupplierById(int id) =>
      (select(db.suppliers)..where((s) => s.id.equals(id) & s.deletedAt.isNull())).getSingleOrNull();

  Future<Supplier?> getSupplierByPhone(String phone) =>
      (select(db.suppliers)..where((s) => s.phone.equals(phone) & s.deletedAt.isNull())).getSingleOrNull();

  Future<List<Supplier>> searchSuppliers(String query, {int? tenantId}) {
    final q = '%${query.toLowerCase()}%';
    final queryBuilder = select(db.suppliers)
      ..where((s) =>
          s.deletedAt.isNull() &
          (s.name.lower().like(q) | s.phone.like(q) | s.company.lower().like(q) | s.address.lower().like(q)));
    if (tenantId != null) {
      queryBuilder.where((s) => s.tenantId.equals(tenantId));
    }
    return queryBuilder.get();
  }

  Future<List<Supplier>> getSuppliersWithDebt({int? tenantId}) {
    final query = select(db.suppliers)
      ..where((s) => s.deletedAt.isNull() & s.balance.isBiggerThanValue(0));
    if (tenantId != null) {
      query.where((s) => s.tenantId.equals(tenantId));
    }
    return query.get();
  }

  Future<int> insertSupplier(SuppliersCompanion supplier) => into(db.suppliers).insert(supplier);

  Future<bool> updateSupplier(SuppliersCompanion supplier) => update(db.suppliers).replace(supplier);

  Future<int> updateBalance(int supplierId, double newBalance) {
    return (update(db.suppliers)
          ..where((s) => s.id.equals(supplierId)))
        .write(SuppliersCompanion(
          balance: Value(newBalance),
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('pending'),
        ));
  }

  Future<int> adjustBalance(int supplierId, double delta) {
    return transaction(() async {
      final supplier = await getSupplierById(supplierId);
      if (supplier == null) return 0;
      final newBalance = supplier.balance + delta;
      return updateBalance(supplierId, newBalance);
    });
  }

  Future<int> upsertSupplier(SuppliersCompanion supplier) {
    return transaction(() async {
      Supplier? existing;
      if (supplier.phone.value != null && supplier.phone.value!.isNotEmpty) {
        existing = await getSupplierByPhone(supplier.phone.value!);
      }
      if (existing == null && supplier.name.value.isNotEmpty) {
        existing = await (select(db.suppliers)
              ..where((s) => s.name.equals(supplier.name.value) & s.deletedAt.isNull()))
            .getSingleOrNull();
      }

      if (existing != null) {
        return update(db.suppliers).replace(SuppliersCompanion(
          id: Value(existing.id),
          name: supplier.name,
          company: supplier.company,
          phone: supplier.phone,
          address: supplier.address,
          avatarPath: supplier.avatarPath,
          notes: supplier.notes,
          balance: supplier.balance,
          dueDate: supplier.dueDate,
          tenantId: supplier.tenantId,
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('synced'),
        ));
      } else {
        return into(db.suppliers).insert(supplier);
      }
    });
  }

  Future<int> deleteSupplier(int id) =>
      (delete(db.suppliers)..where((s) => s.id.equals(id))).go();

  Stream<List<Supplier>> watchSuppliers({int? tenantId}) {
    final query = select(db.suppliers)..where((s) => s.deletedAt.isNull());
    if (tenantId != null) {
      query.where((s) => s.tenantId.equals(tenantId));
    }
    return query.watch();
  }
}