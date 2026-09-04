import '../../core/database/app_database.dart';
import '../../core/database/daos.dart';

class DatabaseService {
  final AppDatabase _db;

  DatabaseService(this._db);

  late final TenantDao tenants = TenantDao(_db);
  late final ProductDao products = ProductDao(_db);
  late final CustomerDao customers = CustomerDao(_db);
  late final SupplierDao suppliers = SupplierDao(_db);
  late final OrderDao orders = OrderDao(_db);
  late final PurchaseOrderDao purchaseOrders = PurchaseOrderDao(_db);
  late final MaintenanceDao maintenance = MaintenanceDao(_db);
  late final ExpenseDao expenses = ExpenseDao(_db);
  late final TransactionDao transactions = TransactionDao(_db);
  late final StockAlertDao stockAlerts = StockAlertDao(_db);
  late final StoreAuditDao storeAudits = StoreAuditDao(_db);
  late final SyncQueueDao syncQueue = SyncQueueDao(_db);

  AppDatabase get database => _db;

  Future<void> close() => _db.close();
}