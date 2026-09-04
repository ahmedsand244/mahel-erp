import 'package:drift/drift.dart';
import '../../app_database.dart';

class MaintenanceDao {
  final AppDatabase db;
  MaintenanceDao(this.db);

  Future<List<MaintenanceTicket>> getAllTickets({int? tenantId, String? status}) {
    final query = select(db.maintenanceTickets)..where((t) => t.deletedAt.isNull());
    if (tenantId != null) {
      query.where((t) => t.tenantId.equals(tenantId));
    }
    if (status != null && status.isNotEmpty) {
      query.where((t) => t.status.equals(status));
    }
    return query.orderBy([OrderingTerm.desc(db.maintenanceTickets.createdAt)]).get();
  }

  Future<MaintenanceTicket?> getTicketById(int id) =>
      (select(db.maintenanceTickets)..where((t) => t.id.equals(id) & t.deletedAt.isNull())).getSingleOrNull();

  Future<List<TicketPartConsumption>> getTicketParts(int ticketId) =>
      (select(db.ticketPartConsumptions)
            ..where((p) => p.ticketId.equals(ticketId) & p.deletedAt.isNull()))
          .get();

  Future<int> insertTicket(MaintenanceTicketsCompanion ticket) => into(db.maintenanceTickets).insert(ticket);

  Future<bool> updateTicket(MaintenanceTicketsCompanion ticket) => update(db.maintenanceTickets).replace(ticket);

  Future<int> updateTicketStatus(int ticketId, String status) {
    return (update(db.maintenanceTickets)
          ..where((t) => t.id.equals(ticketId)))
        .write(MaintenanceTicketsCompanion(
          status: Value(status),
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('pending'),
        ));
  }

  Future<int> addPartToTicket(TicketPartConsumptionsCompanion part) {
    return transaction(() async {
      final partId = await into(db.ticketPartConsumptions).insert(part);
      final partData = await (select(db.ticketPartConsumptions)..where((p) => p.id.equals(partId))).getSingle();
      final product = await (select(db.products)..where((p) => p.id.equals(partData.productId))).getSingleOrNull();
      
      if (product != null) {
        // Deduct stock
        await (update(db.products)
              ..where((p) => p.id.equals(product.id)))
            .write(ProductsCompanion(
              stockQuantity: Value((product.stockQuantity - partData.quantity).clamp(0, 999999)),
              lastModified: Value(DateTime.now()),
              syncStatus: const Value('pending'),
            ));

        // Update ticket totals
        await (update(db.maintenanceTickets)
              ..where((t) => t.id.equals(partData.ticketId)))
            .write(MaintenanceTicketsCompanion(
              partsCost: Value(partData.cost * partData.quantity),
              partsSell: Value(partData.priceCharged * partData.quantity),
              lastModified: Value(DateTime.now()),
              syncStatus: const Value('pending'),
            ));
      }
      return partId;
    });
  }

  Stream<List<MaintenanceTicket>> watchTicketsByStatus(String status, {int? tenantId}) {
    final query = select(db.maintenanceTickets)
      ..where((t) => t.deletedAt.isNull() & t.status.equals(status))
      ..orderBy([OrderingTerm.desc(db.maintenanceTickets.createdAt)]);
    if (tenantId != null) {
      query.where((t) => t.tenantId.equals(tenantId));
    }
    return query.watch();
  }
}