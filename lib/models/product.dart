class ProductModel {
  final int id;
  final String name;
  final String sku;
  final String barcode;
  final double salePrice;
  final double costPrice;
  final int stockQuantity;
  final String unit;
  final String categoryName;

  ProductModel({
    required this.id,
    required this.name,
    required this.sku,
    required this.barcode,
    required this.salePrice,
    required this.costPrice,
    required this.stockQuantity,
    required this.unit,
    required this.categoryName,
  });

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    return ProductModel(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      sku: json['sku'] ?? '',
      barcode: json['barcode'] ?? '',
      salePrice: (json['sale_price'] ?? 0.0).toDouble(),
      costPrice: (json['cost_price'] ?? 0.0).toDouble(),
      stockQuantity: json['stock_quantity'] ?? 0,
      unit: json['unit'] ?? 'حبة',
      categoryName: json['category_name'] ?? 'عام',
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'name': name,
      'sku': sku,
      'barcode': barcode,
      'salePrice': salePrice,
      'costPrice': costPrice,
      'stockQuantity': stockQuantity,
      'unit': unit,
      'categoryName': categoryName,
    };
  }

  factory ProductModel.fromMap(Map<String, dynamic> map) {
    return ProductModel(
      id: map['id'],
      name: map['name'],
      sku: map['sku'],
      barcode: map['barcode'],
      salePrice: map['salePrice'],
      costPrice: map['costPrice'],
      stockQuantity: map['stockQuantity'],
      unit: map['unit'],
      categoryName: map['categoryName'],
    );
  }
}
