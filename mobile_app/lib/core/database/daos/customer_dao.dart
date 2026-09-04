import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class CustomerDao extends DatabaseAccessor<AppDatabase> {
  CustomerDao(super.db);
  AppDatabase get db => attachedDatabase;

  Future<List<Customer>> getAllCustomers({int? tenantId}) {
    final query = select(db.customers)..where((c) => c.deletedAt.isNull());
    if (tenantId != null) {
      query.where((c) => c.tenantId.equals(tenantId));
    }
    return query.get();
  }

  Future<Customer?> getCustomerById(int id) =>
      (select(db.customers)..where((c) => c.id.equals(id) & c.deletedAt.isNull())).getSingleOrNull();

  Future<Customer?> getCustomerByPhone(String phone) =>
      (select(db.customers)..where((c) => c.phone.equals(phone) & c.deletedAt.isNull())).getSingleOrNull();

  Future<List<Customer>> searchCustomers(String query, {int? tenantId}) {
    final q = '%${query.toLowerCase()}%';
    final queryBuilder = select(db.customers)
      ..where((c) =>
          c.deletedAt.isNull() &
          (c.name.lower().like(q) | c.phone.like(q) | c.workplace.lower().like(q) | c.address.lower().like(q)));
    if (tenantId != null) {
      queryBuilder.where((c) => c.tenantId.equals(tenantId));
    }
    return queryBuilder.get();
  }

  Future<List<Customer>> getCustomersWithDebt({int? tenantId}) {
    final query = select(db.customers)
      ..where((c) => c.deletedAt.isNull() & c.balance.isBiggerThanValue(0));
    if (tenantId != null) {
      query.where((c) => c.tenantId.equals(tenantId));
    }
    return query.get();
  }

  Future<int> insertCustomer(CustomersCompanion customer) => into(db.customers).insert(customer);

  Future<bool> updateCustomer(CustomersCompanion customer) => update(db.customers).replace(customer);

  Future<int> updateBalance(int customerId, double newBalance) {
    return (update(db.customers)
          ..where((c) => c.id.equals(customerId)))
        .write(CustomersCompanion(
          balance: Value(newBalance),
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('pending'),
        ));
  }

  Future<int> adjustBalance(int customerId, double delta) {
    return transaction(() async {
      final customer = await getCustomerById(customerId);
      if (customer == null) return 0;
      final newBalance = customer.balance + delta;
      return updateBalance(customerId, newBalance);
    });
  }

  Future<int> upsertCustomer(CustomersCompanion customer) {
    return transaction(() async {
      Customer? existing;
      if (customer.phone.value != null && customer.phone.value!.isNotEmpty) {
        existing = await getCustomerByPhone(customer.phone.value!);
      }
      if (existing == null && customer.name.value.isNotEmpty) {
        existing = await (select(db.customers)
              ..where((c) => c.name.equals(customer.name.value) & c.deletedAt.isNull()))
            .getSingleOrNull();
      }

      if (existing != null) {
        return update(db.customers).replace(CustomersCompanion(
          id: Value(existing.id),
          name: customer.name,
          phone: customer.phone,
          workplace: customer.workplace,
          address: customer.address,
          avatarPath: customer.avatarPath,
          notes: customer.notes,
          balance: customer.balance,
          dueDate: customer.dueDate,
          tenantId: customer.tenantId,
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('synced'),
        ));
      } else {
        return into(db.customers).insert(customer);
      }
    });
  }

  Future<int> deleteCustomer(int id) =>
      (delete(db.customers)..where((c) => c.id.equals(id))).go();

  Stream<List<Customer>> watchCustomers({int? tenantId}) {
    final query = select(db.customers)..where((c) => c.deletedAt.isNull());
    if (tenantId != null) {
      query.where((c) => c.tenantId.equals(tenantId));
    }
    return query.watch();
  }
}

