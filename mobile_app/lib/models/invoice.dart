class InvoiceItem {
  final int productId;
  final String productName;
  final int quantity;
  final double unitPrice;

  InvoiceItem({
    required this.productId,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
  });

  double get totalPrice => quantity * unitPrice;

  Map<String, dynamic> toJson() {
    return {
      'product_id': productId,
      'quantity': quantity,
      'unit_price': unitPrice,
    };
  }

  factory InvoiceItem.fromJson(Map<String, dynamic> json) {
    return InvoiceItem(
      productId: json['product_id'],
      productName: json['product_name'] ?? '',
      quantity: json['quantity'],
      unitPrice: (json['unit_price'] ?? 0.0).toDouble(),
    );
  }
}

class OfflineInvoice {
  final String clientId;
  final String paymentMethod;
  final int? customerId;
  final double totalAmount;
  final DateTime createdAt;
  final List<InvoiceItem> items;
  bool isSynced;

  OfflineInvoice({
    required this.clientId,
    required this.paymentMethod,
    this.customerId,
    required this.totalAmount,
    required this.createdAt,
    required this.items,
    this.isSynced = false,
  });

  Map<String, dynamic> toJson() {
    return {
      'client_id': clientId,
      'payment_method': paymentMethod,
      'customer_id': customerId,
      'total_amount': totalAmount,
      'created_at': createdAt.toIso8601String(),
      'items': items.map((i) => i.toJson()).toList(),
    };
  }
}
