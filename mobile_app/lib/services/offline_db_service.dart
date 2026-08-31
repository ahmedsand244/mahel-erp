import 'dart:async';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/product.dart';
import '../models/invoice.dart';

class OfflineDbService {
  static final OfflineDbService instance = OfflineDbService._init();
  static Database? _database;

  OfflineDbService._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('mahel_pos_offline.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(path, version: 1, onCreate: _createDB);
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
      CREATE TABLE pending_invoices (
        clientId TEXT PRIMARY KEY,
        paymentMethod TEXT NOT NULL,
        customerId INTEGER,
        totalAmount REAL NOT NULL,
        createdAt TEXT NOT NULL,
        itemsJson TEXT NOT NULL,
        isSynced INTEGER NOT NULL DEFAULT 0
      )
    ''');
  }

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
    final result = await db.query('products');
    return result.map((json) => ProductModel.fromMap(json)).toList();
  }

  Future<void> queueOfflineInvoice(OfflineInvoice invoice) async {
    final db = await instance.database;
    await db.insert(
      'pending_invoices',
      {
        'clientId': invoice.clientId,
        'paymentMethod': invoice.paymentMethod,
        'customerId': invoice.customerId,
        'totalAmount': invoice.totalAmount,
        'createdAt': invoice.createdAt.toIso8601String(),
        'itemsJson': invoice.toJson()['items'].toString(),
        'isSynced': 0,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }
}
