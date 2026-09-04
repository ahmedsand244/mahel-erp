import 'dart:convert';

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
      'product_name': productName,
      'quantity': quantity,
      'unit_price': unitPrice,
    };
  }

  factory InvoiceItem.fromJson(Map<String, dynamic> json) {
    return InvoiceItem(
      productId: json['product_id'] ?? 0,
      productName: json['product_name'] ?? '',
      quantity: json['quantity'] ?? 1,
      unitPrice: (json['unit_price'] ?? 0.0).toDouble(),
    );
  }
}

class OfflineInvoice {
  final String clientId;
  final String paymentMethod;
  final int? customerId;
  final String? customerName;
  final double totalAmount;
  final DateTime createdAt;
  final List<InvoiceItem> items;
  bool isSynced;

  OfflineInvoice({
    required this.clientId,
    required this.paymentMethod,
    this.customerId,
    this.customerName,
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
      'customer_name': customerName,
      'total_amount': totalAmount,
      'created_at': createdAt.toIso8601String(),
      'items': items.map((i) => i.toJson()).toList(),
      'is_synced': isSynced ? 1 : 0,
    };
  }

  factory OfflineInvoice.fromMap(Map<String, dynamic> map) {
    List<InvoiceItem> parsedItems = [];
    if (map['itemsJson'] != null && map['itemsJson'].toString().isNotEmpty) {
      try {
        final decoded = jsonDecode(map['itemsJson']);
        if (decoded is List) {
          parsedItems = decoded.map((i) => InvoiceItem.fromJson(i)).toList();
        }
      } catch (_) {}
    }

    return OfflineInvoice(
      clientId: map['clientId'] ?? '',
      paymentMethod: map['paymentMethod'] ?? 'cash',
      customerId: map['customerId'],
      customerName: map['customerName'],
      totalAmount: (map['totalAmount'] ?? 0.0).toDouble(),
      createdAt: DateTime.tryParse(map['createdAt'] ?? '') ?? DateTime.now(),
      items: parsedItems,
      isSynced: (map['isSynced'] ?? 0) == 1,
    );
  }
}
