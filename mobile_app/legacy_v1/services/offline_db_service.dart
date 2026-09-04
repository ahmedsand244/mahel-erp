import 'dart:async';
import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/product.dart';
import '../models/customer.dart';
import '../models/invoice.dart';

class OfflineDbService {
  static final OfflineDbService instance = OfflineDbService._init();
  static Database? _database;

  OfflineDbService._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('mahel_erp_offline_v2.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 2,
      onCreate: _createDB,
      onUpgrade: _upgradeDB,
    );
  }

  Future _createDB(Database db, int version) async {
    await db.execute('''
      CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        sku TEXT,
        barcode TEXT,
        salePrice REAL NOT NULL,
        costPrice REAL NOT NULL,
        stockQuantity INTEGER NOT NULL,
        unit TEXT,
        categoryName TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE customers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT,
        balance REAL NOT NULL DEFAULT 0.0
      )
    ''');

    await db.execute('''
      CREATE TABLE pending_invoices (
        clientId TEXT PRIMARY KEY,
        paymentMethod TEXT NOT NULL,
        customerId INTEGER,
        customerName TEXT,
        totalAmount REAL NOT NULL,
        createdAt TEXT NOT NULL,
        itemsJson TEXT NOT NULL,
        isSynced INTEGER NOT NULL DEFAULT 0
      )
    ''');
  }

  Future _upgradeDB(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) {
      await db.execute('''
        CREATE TABLE IF NOT EXISTS customers (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          phone TEXT,
          balance REAL NOT NULL DEFAULT 0.0
        )
      ''');
      try {
        await db.execute('ALTER TABLE pending_invoices ADD COLUMN customerName TEXT');
      } catch (_) {}
    }
  }

  // --- PRODUCTS ---
  Future<void> saveProducts(List<ProductModel> products) async {
    final db = await instance.database;
    final batch = db.batch();
    batch.delete('products');
    for (var p in products) {
      batch.insert('products', p.toMap(), conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit();
  }

  Future<List<ProductModel>> getOfflineProducts() async {
    final db = await instance.database;
    final result = await db.query('products', orderBy: 'name ASC');
    return result.map((json) => ProductModel.fromMap(json)).toList();
  }

  Future<void> addOrUpdateProduct(ProductModel p) async {
    final db = await instance.database;
    await db.insert(
      'products',
      p.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  // --- CUSTOMERS ---
  Future<void> saveCustomers(List<CustomerModel> customers) async {
    final db = await instance.database;
    final batch = db.batch();
    batch.delete('customers');
    for (var c in customers) {
      batch.insert('customers', c.toMap(), conflictAlgorithm: ConflictAlgorithm.replace);
    }
    await batch.commit();
  }

  Future<List<CustomerModel>> getOfflineCustomers() async {
    final db = await instance.database;
    final result = await db.query('customers', orderBy: 'name ASC');
    return result.map((json) => CustomerModel.fromMap(json)).toList();
  }

  Future<void> addOrUpdateCustomer(CustomerModel c) async {
    final db = await instance.database;
    await db.insert(
      'customers',
      c.toMap(),
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  // --- INVOICES ---
  Future<void> queueOfflineInvoice(OfflineInvoice invoice) async {
    final db = await instance.database;
    await db.insert(
      'pending_invoices',
      {
        'clientId': invoice.clientId,
        'paymentMethod': invoice.paymentMethod,
        'customerId': invoice.customerId,
        'customerName': invoice.customerName,
        'totalAmount': invoice.totalAmount,
        'createdAt': invoice.createdAt.toIso8601String(),
        'itemsJson': jsonEncode(invoice.items.map((i) => i.toJson()).toList()),
        'isSynced': invoice.isSynced ? 1 : 0,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );

    // Deduct local product stock immediately for offline cashier accuracy
    for (var item in invoice.items) {
      final res = await db.query('products', where: 'id = ?', whereArgs: [item.productId]);
      if (res.isNotEmpty) {
        int currentStock = (res.first['stockQuantity'] as int?) ?? 0;
        int newStock = (currentStock - item.quantity);
        if (newStock < 0) newStock = 0;
        await db.update(
          'products',
          {'stockQuantity': newStock},
          where: 'id = ?',
          whereArgs: [item.productId],
        );
      }
    }

    // Update local customer balance if deferred
    if (invoice.paymentMethod == 'deferred' && invoice.customerId != null) {
      final res = await db.query('customers', where: 'id = ?', whereArgs: [invoice.customerId]);
      if (res.isNotEmpty) {
        double currentBal = ((res.first['balance'] as num?) ?? 0.0).toDouble();
        double newBal = currentBal + invoice.totalAmount;
        await db.update(
          'customers',
          {'balance': newBal},
          where: 'id = ?',
          whereArgs: [invoice.customerId],
        );
      }
    }
  }

  Future<List<OfflineInvoice>> getOfflineInvoices() async {
    final db = await instance.database;
    final result = await db.query('pending_invoices', orderBy: 'createdAt DESC');
    return result.map((m) => OfflineInvoice.fromMap(m)).toList();
  }

  Future<List<OfflineInvoice>> getUnsyncedInvoices() async {
    final db = await instance.database;
    final result = await db.query('pending_invoices', where: 'isSynced = 0');
    return result.map((m) => OfflineInvoice.fromMap(m)).toList();
  }

  Future<void> markInvoicesSynced(List<String> clientIds) async {
    final db = await instance.database;
    final batch = db.batch();
    for (var id in clientIds) {
      batch.update(
        'pending_invoices',
        {'isSynced': 1},
        where: 'clientId = ?',
        whereArgs: [id],
      );
    }
    await batch.commit();
  }

  // --- LOCAL STATS CALCULATION ---
  Future<Map<String, dynamic>> calculateLocalStats() async {
    final db = await instance.database;
    final invoicesRes = await db.query('pending_invoices');
    final productsRes = await db.query('products');

    final todayStr = DateTime.now().toIso8601String().substring(0, 10);
    double todaySales = 0.0;
    int todayOrders = 0;
    double totalCostCapital = 0.0;
    int lowStockCount = 0;

    for (var row in invoicesRes) {
      final dateStr = (row['createdAt'] as String? ?? '').substring(0, 10);
      if (dateStr == todayStr) {
        todaySales += ((row['totalAmount'] as num?) ?? 0.0).toDouble();
        todayOrders++;
      }
    }

    for (var p in productsRes) {
      final cost = ((p['costPrice'] as num?) ?? 0.0).toDouble();
      final qty = (p['stockQuantity'] as int?) ?? 0;
      totalCostCapital += (cost * qty);
      if (qty <= 5) {
        lowStockCount++;
      }
    }

    return {
      'today_sales': todaySales,
      'today_orders_count': todayOrders,
      'inventory_cost_val': totalCostCapital,
      'total_products': productsRes.length,
      'low_stock_count': lowStockCount,
    };
  }
}
