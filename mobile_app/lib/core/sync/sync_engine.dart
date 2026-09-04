import 'dart:async';
import 'package:drift/drift.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../../core/database/app_database.dart';
import '../../core/database/daos.dart';
import '../../core/network/api_service.dart';
import '../../core/storage/secure_storage_service.dart';
import '../../shared/models/api_models.dart';

class SyncEngine {
  final AppDatabase _db;
  final ApiService _api;
  final SecureStorageService _storage;
  final Connectivity _connectivity;

  SyncEngine(this._db, this._api, this._storage, this._connectivity);

  final _syncController = StreamController<SyncStatus>.broadcast();
  Stream<SyncStatus> get syncStatusStream => _syncController.stream;

  bool _isSyncing = false;
  bool get isSyncing => _isSyncing;

  Timer? _periodicSyncTimer;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;

  Future<void> initialize() async {
    await _storage.init();
    _startPeriodicSync();
    _listenToConnectivity();
  }

  void _startPeriodicSync() {
    _periodicSyncTimer = Timer.periodic(const Duration(minutes: 15), (_) {
      if (!_isSyncing) {
        _performFullSync();
      }
    });
  }

  void _listenToConnectivity() {
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen((results) {
      final hasInternet = results.any((r) => r != ConnectivityResult.none);
      if (hasInternet && !_isSyncing) {
        _performFullSync();
      }
    });
  }

  Future<void> _performFullSync() async {
    if (_isSyncing) return;
    _isSyncing = true;
    _syncController.add(SyncStatus.inProgress());

    try {
      final tenantSlug = await _storage.readSecure('tenant_slug') ?? 'mahel';
      
      // Pull latest data from server
      await _pullFromServer(tenantSlug);
      
      // Push local changes to server
      await _pushToServer(tenantSlug);
      
      await _storage.setLastSync(DateTime.now());
      _syncController.add(SyncStatus.completed(DateTime.now()));
    } catch (e) {
      _syncController.add(SyncStatus.failed(e.toString()));
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _pullFromServer(String tenantSlug) async {
    // This would call a delta sync endpoint: GET /api/v1/sync/pull?since=last_sync
    // For now, we'll do a full pull of critical data
    
    // Pull products
    final productsResponse = await _api.fetchProducts(tenantSlug: tenantSlug);
    if (productsResponse.success && productsResponse.products != null) {
      final productDao = ProductDao(_db);
      final companions = productsResponse.products!.map((p) => ProductsCompanion(
        id: Value(p.id),
        name: Value(p.name),
        sku: Value(p.sku ?? ''),
        barcode: Value(p.barcode),
        category: Value(p.categoryName ?? 'عام / متنوع'),
        purchasePrice: Value(p.costPrice),
        sellingPrice: Value(p.salePrice),
        stockQuantity: Value(p.stockQuantity),
        minStockThreshold: const Value(5),
        tenantId: const Value(1),
        serverId: Value(p.id),
        syncStatus: const Value('synced'),
        lastModified: Value(DateTime.now()),
      )).toList();
      await productDao.bulkUpsertProducts(companions);
    }

    // Pull customers
    final customersResponse = await _api.fetchCustomers(tenantSlug: tenantSlug);
    if (customersResponse.success && customersResponse.customers != null) {
      final customerDao = CustomerDao(_db);
      for (final c in customersResponse.customers!) {
        await customerDao.upsertCustomer(CustomersCompanion(
          id: Value(c.id),
          name: Value(c.name),
          phone: Value(c.phone ?? ''),
          balance: Value(c.balance),
          tenantId: const Value(1),
          serverId: Value(c.id),
          syncStatus: const Value('synced'),
          lastModified: Value(DateTime.now()),
        ));
      }
    }
  }

  Future<void> _pushToServer(String tenantSlug) async {
    // Get pending operations from sync queue
    final syncQueueDao = SyncQueueDao(_db);
    final pendingOps = await syncQueueDao.getPendingOperations();
    
    for (final op in pendingOps) {
      await syncQueueDao.markProcessing(op.id);
      try {
        // Process based on operation type
        await _processOperation(op, tenantSlug);
        await syncQueueDao.markCompleted(op.id);
      } catch (e) {
        await syncQueueDao.markFailed(op.id, e.toString());
      }
    }
  }

  Future<void> _processOperation(SyncQueue operation, String tenantSlug) async {
    switch (operation.operationType) {
      case 'create_invoice':
        final invoices = [operation.payloadJson]; // Parse JSON
        await _api.syncInvoices(tenantSlug: tenantSlug, invoices: invoices);
        break;
      case 'create_customer':
        // Would need API endpoint
        break;
      case 'create_supplier':
        // Would need API endpoint
        break;
      case 'create_product':
        // Would need API endpoint
        break;
      case 'update_product':
        // Would need API endpoint
        break;
      default:
        throw Exception('Unknown operation type: ${operation.operationType}');
    }
  }

  // Public methods for manual sync
  Future<void> manualSync() async {
    if (!_isSyncing) {
      await _performFullSync();
    }
  }

  Future<void> enqueueInvoice(Map<String, dynamic> invoice) async {
    final syncQueueDao = SyncQueueDao(_db);
    await syncQueueDao.enqueueOperation(SyncQueueCompanion(
      operationType: const Value('create_invoice'),
      payloadJson: Value(invoice.toString()),
      status: const Value('pending'),
    ));
  }

  Future<void> enqueueProduct(ProductsCompanion product) async {
    final syncQueueDao = SyncQueueDao(_db);
    await syncQueueDao.enqueueOperation(SyncQueueCompanion(
      operationType: const Value('create_product'),
      payloadJson: Value(product.toString()),
      status: const Value('pending'),
    ));
  }

  Future<void> enqueueCustomer(CustomersCompanion customer) async {
    final syncQueueDao = SyncQueueDao(_db);
    await syncQueueDao.enqueueOperation(SyncQueueCompanion(
      operationType: const Value('create_customer'),
      payloadJson: Value(customer.toString()),
      status: const Value('pending'),
    ));
  }

  void dispose() {
    _periodicSyncTimer?.cancel();
    _connectivitySubscription?.cancel();
    _syncController.close();
  }
}

enum SyncState { idle, inProgress, completed, failed }

class SyncStatus {
  final SyncState state;
  final DateTime? lastSync;
  final String? error;

  const SyncStatus._(this.state, this.lastSync, this.error);

  factory SyncStatus.idle() => SyncStatus._(SyncState.idle, null, null);
  factory SyncStatus.inProgress() => SyncStatus._(SyncState.inProgress, null, null);
  factory SyncStatus.completed(DateTime time) => SyncStatus._(SyncState.completed, time, null);
  factory SyncStatus.failed(String error) => SyncStatus._(SyncState.failed, null, error);

  bool get isIdle => state == SyncState.idle;
  bool get isInProgress => state == SyncState.inProgress;
  bool get isCompleted => state == SyncState.completed;
  bool get isFailed => state == SyncState.failed;
}