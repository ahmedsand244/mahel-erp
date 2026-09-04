import 'dart:async';
import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:sqlite3_flutter_libs/sqlite3_flutter_libs.dart';

part 'app_database.g.dart';

class Tenants extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1, max: 200)();
  TextColumn get slug => text().withLength(min: 1, max: 100).unique()();
  IntColumn get ownerId => integer().nullable()();
  TextColumn get plan => text().withLength(min: 1, max: 20).withDefault(const Constant('trial'))();
  DateTimeColumn get trialEndsAt => dateTime().nullable()();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();
  TextColumn get phone => text().nullable()();
  TextColumn get address => text().nullable()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class TenantUsers extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get tenantId => integer().references(Tenants, #id, onDelete: KeyAction.cascade)();
  IntColumn get userId => integer()();
  TextColumn get role => text().withLength(min: 1, max: 20).withDefault(const Constant('cashier'))();
  DateTimeColumn get joinedAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();

  @override
  List<Set<Column>> get uniqueKeys => [{tenantId, userId}];
}

class Users extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get username => text().withLength(min: 1, max: 150).unique()();
  TextColumn get email => text().nullable()();
  TextColumn get firstName => text().nullable()();
  TextColumn get lastName => text().nullable()();
  TextColumn get passwordHash => text()();
  BoolColumn get isActive => boolean().withDefault(const Constant(true))();
  BoolColumn get isSuperuser => boolean().withDefault(const Constant(false))();
  DateTimeColumn get dateJoined => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get lastLogin => dateTime().nullable()();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class Categories extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1, max: 100)();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class Products extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1, max: 200)();
  TextColumn get sku => text().withLength(min: 1, max: 100)();
  TextColumn get barcode => text().nullable()();
  TextColumn get category => text().withLength(max: 100).withDefault(const Constant('عام / متنوع'))();
  IntColumn get categoryId => integer().nullable().references(Categories, #id, onDelete: KeyAction.setNull)();
  TextColumn get imagePath => text().nullable()();
  RealColumn get purchasePrice => real().withDefault(const Constant(0.0))();
  RealColumn get sellingPrice => real().withDefault(const Constant(0.0))();
  IntColumn get stockQuantity => integer().withDefault(const Constant(0))();
  IntColumn get minStockThreshold => integer().withDefault(const Constant(5))();
  IntColumn get defaultSupplierId => integer().nullable()();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class StockAlerts extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get productId => integer().references(Products, #id, onDelete: KeyAction.cascade)();
  TextColumn get message => text()();
  BoolColumn get isResolved => boolean().withDefault(const Constant(false))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class Customers extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1, max: 200)();
  TextColumn get phone => text().nullable()();
  TextColumn get workplace => text().nullable()();
  TextColumn get address => text().nullable()();
  TextColumn get avatarPath => text().nullable()();
  TextColumn get notes => text().nullable()();
  RealColumn get balance => real().withDefault(const Constant(0.0))();
  DateTimeColumn get dueDate => dateTime().nullable()();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class Suppliers extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1, max: 200)();
  TextColumn get company => text().nullable()();
  TextColumn get phone => text().nullable()();
  TextColumn get address => text().nullable()();
  TextColumn get avatarPath => text().nullable()();
  TextColumn get notes => text().nullable()();
  RealColumn get balance => real().withDefault(const Constant(0.0))();
  DateTimeColumn get dueDate => dateTime().nullable()();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class Transactions extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get customerId => integer().nullable().references(Customers, #id, onDelete: KeyAction.cascade)();
  IntColumn get supplierId => integer().nullable().references(Suppliers, #id, onDelete: KeyAction.cascade)();
  RealColumn get amount => real()();
  TextColumn get transactionType => text().withLength(min: 1, max: 30)();
  TextColumn get notes => text().withDefault(const Constant(''))();
  DateTimeColumn get dueDate => dateTime().nullable()();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class Orders extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get orderNumber => text().withLength(min: 1, max: 100)();
  IntColumn get customerId => integer().nullable().references(Customers, #id, onDelete: KeyAction.setNull)();
  TextColumn get paymentMethod => text().withLength(min: 1, max: 20).withDefault(const Constant('cash'))();
  RealColumn get totalAmount => real()();
  RealColumn get costOfGoodsSold => real().withDefault(const Constant(0.0))();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class OrderItems extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get orderId => integer().references(Orders, #id, onDelete: KeyAction.cascade)();
  IntColumn get productId => integer().references(Products, #id, onDelete: KeyAction.restrict)();
  IntColumn get quantity => integer().withDefault(const Constant(1))();
  RealColumn get unitPrice => real()();
  RealColumn get cost => real()();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class PurchaseOrders extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get orderNumber => text().withLength(min: 1, max: 50)();
  IntColumn get supplierId => integer().nullable().references(Suppliers, #id, onDelete: KeyAction.setNull)();
  TextColumn get status => text().withLength(min: 1, max: 20).withDefault(const Constant('draft'))();
  TextColumn get notes => text().withDefault(const Constant(''))();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get receivedAt => dateTime().nullable()();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class PurchaseOrderItems extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get purchaseOrderId => integer().references(PurchaseOrders, #id, onDelete: KeyAction.cascade)();
  IntColumn get productId => integer().nullable().references(Products, #id, onDelete: KeyAction.setNull)();
  TextColumn get customItemName => text().withDefault(const Constant(''))();
  IntColumn get supplierId => integer().nullable().references(Suppliers, #id, onDelete: KeyAction.setNull)();
  IntColumn get quantityRequested => integer().withDefault(const Constant(1))();
  RealColumn get unitCost => real().withDefault(const Constant(0.0))();
  BoolColumn get isReceived => boolean().withDefault(const Constant(false))();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class Expenses extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get category => text().withLength(min: 1, max: 30).withDefault(const Constant('other'))();
  TextColumn get description => text().withLength(min: 1, max: 255)();
  RealColumn get amount => real()();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class MaintenanceTickets extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get ticketNumber => text().withLength(min: 1, max: 100)();
  IntColumn get customerId => integer().references(Customers, #id, onDelete: KeyAction.cascade)();
  TextColumn get deviceName => text().withLength(min: 1, max: 200)();
  TextColumn get status => text().withLength(min: 1, max: 30).withDefault(const Constant('pending'))();
  RealColumn get laborFees => real().withDefault(const Constant(0.0))();
  RealColumn get partsCost => real().withDefault(const Constant(0.0))();
  RealColumn get partsSell => real().withDefault(const Constant(0.0))();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class TicketPartConsumptions extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get ticketId => integer().references(MaintenanceTickets, #id, onDelete: KeyAction.cascade)();
  IntColumn get productId => integer().references(Products, #id, onDelete: KeyAction.restrict)();
  IntColumn get quantity => integer().withDefault(const Constant(1))();
  RealColumn get priceCharged => real()();
  RealColumn get cost => real()();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class StoreAudits extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get title => text().withLength(min: 1, max: 200)();
  DateTimeColumn get startDate => dateTime().nullable()();
  DateTimeColumn get endDate => dateTime().nullable()();
  RealColumn get grossSales => real().withDefault(const Constant(0.0))();
  RealColumn get cogs => real().withDefault(const Constant(0.0))();
  RealColumn get maintenanceLabor => real().withDefault(const Constant(0.0))();
  RealColumn get maintenancePartsSell => real().withDefault(const Constant(0.0))();
  RealColumn get maintenancePartsCost => real().withDefault(const Constant(0.0))();
  RealColumn get totalExpenses => real().withDefault(const Constant(0.0))();
  RealColumn get netProfit => real().withDefault(const Constant(0.0))();
  RealColumn get inventoryCostValue => real().withDefault(const Constant(0.0))();
  RealColumn get inventoryRetailValue => real().withDefault(const Constant(0.0))();
  RealColumn get customerDebts => real().withDefault(const Constant(0.0))();
  RealColumn get supplierDebts => real().withDefault(const Constant(0.0))();
  TextColumn get notes => text().nullable()();
  IntColumn get tenantId => integer().nullable().references(Tenants, #id, onDelete: KeyAction.cascade)();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get serverId => integer().nullable()();
  TextColumn get syncStatus => text().withDefault(const Constant('synced'))();
  DateTimeColumn get lastModified => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get deletedAt => dateTime().nullable()();
}

class SyncQueue extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get operationType => text().withLength(min: 1, max: 50)();
  TextColumn get payloadJson => text()();
  IntColumn get retryCount => integer().withDefault(const Constant(0))();
  TextColumn get status => text().withLength(min: 1, max: 20).withDefault(const Constant('pending'))();
  TextColumn get errorMessage => text().nullable()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get processedAt => dateTime().nullable()();
}

@DriftDatabase(tables: [
  Tenants,
  TenantUsers,
  Users,
  Categories,
  Products,
  StockAlerts,
  Customers,
  Suppliers,
  Transactions,
  Orders,
  OrderItems,
  PurchaseOrders,
  PurchaseOrderItems,
  Expenses,
  MaintenanceTickets,
  TicketPartConsumptions,
  StoreAudits,
  SyncQueue,
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration {
    return MigrationStrategy(
      onCreate: (Migrator m) async {
        await m.createAll();
      },
      onUpgrade: (Migrator m, int from, int to) async {
        // Future migrations will go here
      },
      beforeOpen: (details) async {
        await customStatement('PRAGMA foreign_keys = ON');
      },
    );
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'mahel_pos_offline.db'));
    return NativeDatabase.createInBackground(file);
  });
}