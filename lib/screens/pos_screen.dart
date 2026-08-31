import 'package:flutter/material.dart';
import '../models/product.dart';
import '../models/invoice.dart';
import '../services/api_service.dart';
import '../services/offline_db_service.dart';

class PosScreen extends StatefulWidget {
  final String tenantSlug;

  const PosScreen({super.key, required this.tenantSlug});

  @override
  State<PosScreen> createState() => _PosScreenState();
}

class _PosScreenState extends State<PosScreen> {
  final ApiService _apiService = ApiService();
  final OfflineDbService _dbService = OfflineDbService.instance;

  List<ProductModel> _products = [];
  final List<InvoiceItem> _cart = [];
  bool _isLoading = true;
  bool _isOfflineMode = false;

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  Future<void> _loadProducts() async {
    setState(() => _isLoading = true);

    // Try online fetch first
    var fetched = await _apiService.fetchProducts(widget.tenantSlug);
    if (fetched.isNotEmpty) {
      await _dbService.saveProducts(fetched);
      _isOfflineMode = false;
    } else {
      // Fallback to offline SQLite DB
      fetched = await _dbService.getOfflineProducts();
      _isOfflineMode = true;
    }

    setState(() {
      _products = fetched;
      _isLoading = false;
    });
  }

  void _addToCart(ProductModel product) {
    setState(() {
      int index = _cart.indexWhere((item) => item.productId == product.id);
      if (index >= 0) {
        final current = _cart[index];
        _cart[index] = InvoiceItem(
          productId: current.productId,
          productName: current.productName,
          quantity: current.quantity + 1,
          unitPrice: current.unitPrice,
        );
      } else {
        _cart.add(
          InvoiceItem(
            productId: product.id,
            productName: product.name,
            quantity: 1,
            unitPrice: product.salePrice,
          ),
        );
      }
    });
  }

  double get _cartTotal => _cart.fold(0, (sum, item) => sum + item.totalPrice);

  Future<void> _completeSale(String paymentMethod) async {
    if (_cart.isEmpty) return;

    final invoice = OfflineInvoice(
      clientId: "MOB-${DateTime.now().millisecondsSinceEpoch}",
      paymentMethod: paymentMethod,
      totalAmount: _cartTotal,
      createdAt: DateTime.now(),
      items: List.from(_cart),
    );

    // Attempt online sync immediately if connected
    bool syncedOnline = false;
    if (!_isOfflineMode) {
      final res = await _apiService.syncInvoices(widget.tenantSlug, [invoice]);
      if (res['success'] == true) {
        syncedOnline = true;
      }
    }

    if (!syncedOnline) {
      // Queue offline in SQLite
      await _dbService.queueOfflineInvoice(invoice);
    }

    setState(() {
      _cart.clear();
    });

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          syncedOnline
              ? "تم حفظ الفاتورة ورفعها للسيرفر بنجاح! 🚀"
              : "تم حفظ الفاتورة محلياً (Offline) وسيتم المزامنة عند توفر النت ⏳",
        ),
        backgroundColor: syncedOnline ? Colors.emerald : Colors.amber.shade800,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("شاشة البيع POS"),
        actions: [
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: _isOfflineMode
                  ? Colors.amber.withOpacity(0.2)
                  : Colors.emerald.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _isOfflineMode ? Colors.amber : Colors.emerald,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  _isOfflineMode ? Icons.wifi_off_rounded : Icons.wifi_rounded,
                  size: 14,
                  color: _isOfflineMode ? Colors.amber : Colors.emerald,
                ),
                const SizedBox(width: 4),
                Text(
                  _isOfflineMode ? "بدون إنترنت" : "متصل بالسيرفر",
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: _isOfflineMode ? Colors.amber : Colors.emerald,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Expanded(
                  flex: 5,
                  child: GridView.builder(
                    padding: const EdgeInsets.all(12),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      childAspectRatio: 1.1,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                    ),
                    itemCount: _products.length,
                    itemBuilder: (ctx, idx) {
                      final p = _products[idx];
                      return GestureDetector(
                        onTap: () => _addToCart(p),
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF161B22),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.08),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                p.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const Spacer(),
                              Text(
                                "${p.salePrice.toStringAsFixed(2)} ج.م",
                                style: const TextStyle(
                                  color: Color(0xFF10B981),
                                  fontWeight: FontWeight.black,
                                  fontSize: 15,
                                ),
                              ),
                              Text(
                                "المخزون: ${p.stockQuantity} ${p.unit}",
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.grey.shade400,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: const BoxDecoration(
                    color: Color(0xFF161B22),
                    borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.between,
                        children: [
                          const Text(
                            "إجمالي السلة:",
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            "${_cartTotal.toStringAsFixed(2)} ج.م",
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.black,
                              color: Color(0xFF2F81F7),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton(
                              onPressed: _cart.isEmpty
                                  ? null
                                  : () => _completeSale('cash'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF10B981),
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                              ),
                              child: const Text(
                                "دفع نقدي 💵",
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: ElevatedButton(
                              onPressed: _cart.isEmpty
                                  ? null
                                  : () => _completeSale('visa'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF2F81F7),
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                              ),
                              child: const Text(
                                "دفع فيزا 💳",
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}
