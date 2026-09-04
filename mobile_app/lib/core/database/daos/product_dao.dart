import 'package:drift/drift.dart';
import '../../app_database.dart';

class ProductDao {
  final AppDatabase db;
  ProductDao(this.db);

  Future<List<Product>> getAllProducts({int? tenantId}) {
    final query = select(db.products)..where((p) => p.deletedAt.isNull());
    if (tenantId != null) {
      query.where((p) => p.tenantId.equals(tenantId));
    }
    return query.get();
  }

  Future<Product?> getProductById(int id) =>
      (select(db.products)..where((p) => p.id.equals(id) & p.deletedAt.isNull())).getSingleOrNull();

  Future<Product?> getProductByBarcode(String barcode) =>
      (select(db.products)..where((p) => p.barcode.equals(barcode) & p.deletedAt.isNull())).getSingleOrNull();

  Future<Product?> getProductBySku(String sku) =>
      (select(db.products)..where((p) => p.sku.equals(sku) & p.deletedAt.isNull())).getSingleOrNull();

  Future<List<Product>> searchProducts(String query, {int? tenantId}) {
    final q = '%${query.toLowerCase()}%';
    final queryBuilder = select(db.products)
      ..where((p) =>
          p.deletedAt.isNull() &
          (p.name.lower().like(q) | p.sku.lower().like(q) | p.barcode.like(q)));
    if (tenantId != null) {
      queryBuilder.where((p) => p.tenantId.equals(tenantId));
    }
    return queryBuilder.get();
  }

  Future<List<Product>> getLowStockProducts({int? tenantId}) {
    final query = select(db.products)
      ..where((p) =>
          p.deletedAt.isNull() &
          p.stockQuantity.isSmallerOrEqualValue(p.minStockThreshold));
    if (tenantId != null) {
      query.where((p) => p.tenantId.equals(tenantId));
    }
    return query.get();
  }

  Future<int> insertProduct(ProductsCompanion product) => into(db.products).insert(product);

  Future<bool> updateProduct(ProductsCompanion product) => update(db.products).replace(product);

  Future<int> updateStock(int productId, int newQuantity) {
    return (update(db.products)
          ..where((p) => p.id.equals(productId)))
        .write(ProductsCompanion(
          stockQuantity: Value(newQuantity),
          lastModified: Value(DateTime.now()),
          syncStatus: const Value('pending'),
        ));
  }

  Future<int> adjustStock(int productId, int delta) {
    return transaction(() async {
      final product = await getProductById(productId);
      if (product == null) return 0;
      final newQty = (product.stockQuantity + delta).clamp(0, 999999);
      return updateStock(productId, newQty);
    });
  }

  Future<int> bulkUpsertProducts(List<ProductsCompanion> products) {
    return transaction(() async {
      int count = 0;
      for (final product in products) {
        final existing = product.sku.value.isNotEmpty
            ? await (select(db.products)
                  ..where((p) => p.sku.equals(product.sku.value) & p.deletedAt.isNull()))
                .getSingleOrNull()
            : null;

        if (existing != null) {
          await update(db.products).replace(ProductsCompanion(
            id: Value(existing.id),
            name: product.name,
            sku: product.sku,
            barcode: product.barcode,
            category: product.category,
            categoryId: product.categoryId,
            imagePath: product.imagePath,
            purchasePrice: product.purchasePrice,
            sellingPrice: product.sellingPrice,
            stockQuantity: product.stockQuantity,
            minStockThreshold: product.minStockThreshold,
            defaultSupplierId: product.defaultSupplierId,
            tenantId: product.tenantId,
            lastModified: Value(DateTime.now()),
            syncStatus: const Value('synced'),
          ));
        } else {
          await into(db.products).insert(product);
        }
        count++;
      }
      return count;
    });
  }

  Stream<List<Product>> watchProducts({int? tenantId}) {
    final query = select(db.products)..where((p) => p.deletedAt.isNull());
    if (tenantId != null) {
      query.where((p) => p.tenantId.equals(tenantId));
    }
    return query.watch();
  }

  Future<int> deleteProduct(int id) =>
      (delete(db.products)..where((p) => p.id.equals(id))).go();

  Future<Map<String, dynamic>> getInventoryValuation({int? tenantId}) async {
    final products = await getAllProducts(tenantId: tenantId);
    double costValue = 0;
    double retailValue = 0;
    for (final p in products) {
      costValue += p.purchasePrice * p.stockQuantity;
      retailValue += p.sellingPrice * p.stockQuantity;
    }
    return {
      'costValue': costValue,
      'retailValue': retailValue,
      'potentialProfit': retailValue - costValue,
      'totalProducts': products.length,
    };
  }
}