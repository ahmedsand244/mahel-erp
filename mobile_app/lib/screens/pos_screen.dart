import 'package:flutter/material.dart';
import '../models/product.dart';
import '../models/customer.dart';
import '../models/invoice.dart';
import '../services/offline_db_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class PosScreen extends StatefulWidget {
  const PosScreen({super.key});

  @override
  State<PosScreen> createState() => _PosScreenState();
}

class _PosScreenState extends State<PosScreen> {
  List<ProductModel> _allProducts = [];
  List<ProductModel> _filteredProducts = [];
  List<CustomerModel> _customers = [];
  List<String> _categories = ['الكل'];
  String _selectedCategory = 'الكل';

  final Map<int, int> _cart = {}; // productId -> quantity
  CustomerModel? _selectedCustomer;
  String _paymentMethod = 'cash'; // 'cash' or 'deferred'
  double _discount = 0.0;

  final TextEditingController _searchController = TextEditingController();
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    // Load from local SQLite first
    final products = await OfflineDbService.instance.getOfflineProducts();
    final customers = await OfflineDbService.instance.getOfflineCustomers();

    final cats = {'الكل'};
    for (var p in products) {
      if (p.categoryName.isNotEmpty) cats.add(p.categoryName);
    }

    setState(() {
      _allProducts = products;
      _filteredProducts = products;
      _customers = customers;
      _categories = cats.toList();
      _isLoading = false;
    });

    // Background sync check if online
    ApiService.fetchProducts().then((fresh) {
      if (mounted && fresh.isNotEmpty) {
        setState(() {
          _allProducts = fresh;
          _applyFilter();
        });
      }
    });

    ApiService.fetchCustomers().then((freshCust) {
      if (mounted && freshCust.isNotEmpty) {
        setState(() => _customers = freshCust);
      }
    });
  }

  void _applyFilter() {
    final q = _searchController.text.trim().toLowerCase();
    setState(() {
      _filteredProducts = _allProducts.where((p) {
        final matchesCat = _selectedCategory == 'الكل' || p.categoryName == _selectedCategory;
        final matchesQuery = q.isEmpty ||
            p.name.toLowerCase().contains(q) ||
            p.barcode.toLowerCase().contains(q) ||
            p.sku.toLowerCase().contains(q);
        return matchesCat && matchesQuery;
      }).toList();
    });
  }

  void _addToCart(ProductModel p) {
    if (p.stockQuantity <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('عفواً، نفدت كمية هذا الصنف من المخزن!', style: TextStyle(fontFamily: 'Cairo')),
          backgroundColor: AppColors.danger,
          duration: Duration(seconds: 1),
        ),
      );
      return;
    }

    final currentQty = _cart[p.id] ?? 0;
    if (currentQty >= p.stockQuantity) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('لا تتوفر كمية إضافية بالمخزن!', style: TextStyle(fontFamily: 'Cairo')),
          backgroundColor: AppColors.warning,
          duration: Duration(seconds: 1),
        ),
      );
      return;
    }

    setState(() {
      _cart[p.id] = currentQty + 1;
    });
  }

  void _removeFromCart(int productId) {
    setState(() {
      final currentQty = _cart[productId] ?? 0;
      if (currentQty <= 1) {
        _cart.remove(productId);
      } else {
        _cart[productId] = currentQty - 1;
      }
    });
  }

  double get _subtotal {
    double sum = 0.0;
    for (var entry in _cart.entries) {
      final p = _allProducts.firstWhere((prod) => prod.id == entry.key, orElse: () => ProductModel(id: 0, name: '', sku: '', barcode: '', salePrice: 0, costPrice: 0, stockQuantity: 0, unit: '', categoryName: ''));
      sum += p.salePrice * entry.value;
    }
    return sum;
  }

  double get _finalTotal => (_subtotal - _discount) > 0 ? (_subtotal - _discount) : 0.0;

  int get _cartItemCount => _cart.values.fold(0, (a, b) => a + b);

  Future<void> _completeCheckout() async {
    if (_cart.isEmpty) return;

    if (_paymentMethod == 'deferred' && _selectedCustomer == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('يرجى تحديد العميل أولاً لتسجيل فاتورة آجل/شكك!', style: TextStyle(fontFamily: 'Cairo')),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    final invoiceItems = <InvoiceItem>[];
    for (var entry in _cart.entries) {
      final p = _allProducts.firstWhere((prod) => prod.id == entry.key);
      invoiceItems.add(InvoiceItem(
        productId: p.id,
        productName: p.name,
        quantity: entry.value,
        unitPrice: p.salePrice,
      ));
    }

    final clientId = 'MOB-${DateTime.now().millisecondsSinceEpoch}';
    final offlineInvoice = OfflineInvoice(
      clientId: clientId,
      paymentMethod: _paymentMethod,
      customerId: _selectedCustomer?.id,
      customerName: _selectedCustomer?.name ?? 'زبون نقدي',
      totalAmount: _finalTotal,
      createdAt: DateTime.now(),
      items: invoiceItems,
      isSynced: false,
    );

    // Save offline in SQLite
    await OfflineDbService.instance.queueOfflineInvoice(offlineInvoice);

    // Trigger background sync
    ApiService.syncPendingInvoices();

    if (!mounted) return;
    Navigator.of(context).pop(); // close cart sheet

    // Show success dialog
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.check_circle_rounded, color: AppColors.success, size: 28),
            SizedBox(width: 8),
            Text('تم إصدار الفاتورة!', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('رقم الفاتورة: $clientId', style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(height: 6),
            Text('المبلغ الإجمالي: ${_finalTotal.toStringAsFixed(2)} ج.م', style: const TextStyle(fontFamily: 'Cairo', fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.primary)),
            Text('طريقة الدفع: ${_paymentMethod == "cash" ? "نقدي (كاش)" : "آجل (شكك)"}', style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textSecondary)),
            if (_selectedCustomer != null)
              Text('العميل: ${_selectedCustomer!.name}', style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textSecondary)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: AppColors.successSubtle, borderRadius: BorderRadius.circular(10)),
              child: const Row(
                children: [
                  Icon(Icons.offline_pin_rounded, color: AppColors.success, size: 18),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text('حُفظت بأمان محلياً وستُرفع تلقائياً عند توفر النت.', style: TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.success)),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              setState(() {
                _cart.clear();
                _selectedCustomer = null;
                _discount = 0.0;
                _paymentMethod = 'cash';
              });
              _loadData();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('فاتورة جديدة', style: TextStyle(fontFamily: 'Cairo', color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showCartBottomSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Container(
              padding: const EdgeInsets.all(16),
              constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.85),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.shopping_cart_rounded, color: AppColors.primary),
                          SizedBox(width: 8),
                          Text('سلة المبيعات', style: TextStyle(fontFamily: 'Cairo', fontSize: 18, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
                        ],
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: AppColors.textSecondary),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ],
                  ),
                  const Divider(color: AppColors.border),

                  // Cart items list
                  Expanded(
                    child: _cart.isEmpty
                        ? const Center(
                            child: Text('السلة فارغة!', style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary)),
                          )
                        : ListView(
                            children: _cart.entries.map((entry) {
                              final p = _allProducts.firstWhere((prod) => prod.id == entry.key);
                              return Container(
                                margin: const EdgeInsets.only(bottom: 8),
                                padding: const EdgeInsets.all(10),
                                decoration: AppStyles.glassCard(),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(p.name, style: const TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
                                          Text('${p.salePrice.toStringAsFixed(2)} ج.م', style: const TextStyle(fontFamily: 'Cairo', fontSize: 12, color: AppColors.primary)),
                                        ],
                                      ),
                                    ),
                                    Row(
                                      children: [
                                        IconButton(
                                          icon: const Icon(Icons.remove_circle_outline, color: AppColors.danger, size: 22),
                                          onPressed: () {
                                            _removeFromCart(p.id);
                                            setModalState(() {});
                                            setState(() {});
                                          },
                                        ),
                                        Text('${entry.value}', style: const TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, fontSize: 15, color: AppColors.textPrimary)),
                                        IconButton(
                                          icon: const Icon(Icons.add_circle_outline, color: AppColors.success, size: 22),
                                          onPressed: () {
                                            _addToCart(p);
                                            setModalState(() {});
                                            setState(() {});
                                          },
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              );
                            }).toList(),
                          ),
                  ),

                  const Divider(color: AppColors.border),

                  // Options: Customer & Payment Method
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<CustomerModel?>(
                          value: _selectedCustomer,
                          decoration: InputDecoration(
                            labelText: 'العميل',
                            labelStyle: const TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary, fontSize: 12),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
                            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
                          ),
                          dropdownColor: AppColors.surface,
                          items: [
                            const DropdownMenuItem(value: null, child: Text('زبون نقدي عام', style: TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textPrimary))),
                            ..._customers.map((c) => DropdownMenuItem(value: c, child: Text('${c.name} (${c.balance.toStringAsFixed(0)} ج.م)', style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textPrimary)))),
                          ],
                          onChanged: (val) {
                            setModalState(() => _selectedCustomer = val);
                            setState(() => _selectedCustomer = val);
                          },
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Payment Method
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceElevated,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            ChoiceChip(
                              label: const Text('كاش', style: TextStyle(fontFamily: 'Cairo', fontSize: 11)),
                              selected: _paymentMethod == 'cash',
                              selectedColor: AppColors.success,
                              onSelected: (val) {
                                if (val) {
                                  setModalState(() => _paymentMethod = 'cash');
                                  setState(() => _paymentMethod = 'cash');
                                }
                              },
                            ),
                            const SizedBox(width: 4),
                            ChoiceChip(
                              label: const Text('آجل', style: TextStyle(fontFamily: 'Cairo', fontSize: 11)),
                              selected: _paymentMethod == 'deferred',
                              selectedColor: AppColors.warning,
                              onSelected: (val) {
                                if (val) {
                                  setModalState(() => _paymentMethod = 'deferred');
                                  setState(() => _paymentMethod = 'deferred');
                                }
                              },
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Total and Confirm button
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('الإجمالي النهائي:', style: TextStyle(fontFamily: 'Cairo', fontSize: 12, color: AppColors.textSecondary)),
                          Text('${_finalTotal.toStringAsFixed(2)} ج.م', style: const TextStyle(fontFamily: 'Cairo', fontSize: 22, fontWeight: FontWeight.w900, color: AppColors.primary)),
                        ],
                      ),
                      ElevatedButton.icon(
                        onPressed: _cart.isEmpty ? null : _completeCheckout,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        ),
                        icon: const Icon(Icons.check_rounded, color: Colors.white),
                        label: const Text('إتمام الفاتورة', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white)),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        title: const Text('نقطة البيع (POS)', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
        actions: [
          IconButton(
            tooltip: 'تحديث الأصناف',
            icon: const Icon(Icons.refresh_rounded, color: AppColors.primary),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : Column(
              children: [
                // Search Bar
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                  child: TextField(
                    controller: _searchController,
                    onChanged: (_) => _applyFilter(),
                    style: const TextStyle(fontFamily: 'Cairo', color: AppColors.textPrimary),
                    decoration: InputDecoration(
                      hintText: 'ابحث بالاسم، الباركود، أو الكود...',
                      hintStyle: const TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary, fontSize: 13),
                      prefixIcon: const Icon(Icons.search_rounded, color: AppColors.primary),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear, color: AppColors.textSecondary, size: 18),
                              onPressed: () {
                                _searchController.clear();
                                _applyFilter();
                              },
                            )
                          : null,
                      filled: true,
                      fillColor: AppColors.surface,
                      contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.border)),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.border)),
                      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.primary, width: 1.5)),
                    ),
                  ),
                ),

                // Category Chips
                SizedBox(
                  height: 40,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _categories.length,
                    itemBuilder: (ctx, index) {
                      final cat = _categories[index];
                      final isSelected = cat == _selectedCategory;
                      return Padding(
                        padding: const EdgeInsets.only(left: 6),
                        child: ChoiceChip(
                          label: Text(cat, style: TextStyle(fontFamily: 'Cairo', fontSize: 11, fontWeight: isSelected ? FontWeight.bold : FontWeight.normal, color: isSelected ? Colors.white : AppColors.textSecondary)),
                          selected: isSelected,
                          selectedColor: AppColors.primary,
                          backgroundColor: AppColors.surface,
                          side: BorderSide(color: isSelected ? AppColors.primary : AppColors.border),
                          onSelected: (val) {
                            if (val) {
                              setState(() {
                                _selectedCategory = cat;
                                _applyFilter();
                              });
                            }
                          },
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 6),

                // Product Grid
                Expanded(
                  child: _filteredProducts.isEmpty
                      ? const Center(
                          child: Text('لا توجد أصناف مطابقة!', style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary)),
                        )
                      : GridView.builder(
                          padding: const EdgeInsets.all(16),
                          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 2,
                            mainAxisSpacing: 12,
                            crossAxisSpacing: 12,
                            childAspectRatio: 0.95,
                          ),
                          itemCount: _filteredProducts.length,
                          itemBuilder: (ctx, index) {
                            final p = _filteredProducts[index];
                            final qtyInCart = _cart[p.id] ?? 0;
                            final isOutOfStock = p.stockQuantity <= 0;

                            return InkWell(
                              onTap: isOutOfStock ? null : () => _addToCart(p),
                              borderRadius: BorderRadius.circular(18),
                              child: Container(
                                decoration: AppStyles.glassCard(
                                  border: qtyInCart > 0 ? AppColors.primary : null,
                                  color: isOutOfStock ? AppColors.surface.withOpacity(0.5) : AppColors.surface,
                                ),
                                padding: const EdgeInsets.all(12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: isOutOfStock ? AppColors.dangerSubtle : AppColors.successSubtle,
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(
                                            isOutOfStock ? 'نفد' : '${p.stockQuantity} ${p.unit}',
                                            style: TextStyle(
                                              fontFamily: 'Cairo',
                                              fontSize: 10,
                                              fontWeight: FontWeight.bold,
                                              color: isOutOfStock ? AppColors.danger : AppColors.success,
                                            ),
                                          ),
                                        ),
                                        if (qtyInCart > 0)
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: AppColors.primary,
                                              borderRadius: BorderRadius.circular(10),
                                            ),
                                            child: Text(
                                              '$qtyInCart',
                                              style: const TextStyle(fontFamily: 'Cairo', fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                                            ),
                                          ),
                                      ],
                                    ),
                                    Text(
                                      p.name,
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontFamily: 'Cairo',
                                        fontSize: 13,
                                        fontWeight: FontWeight.bold,
                                        color: isOutOfStock ? AppColors.textSecondary : AppColors.textPrimary,
                                      ),
                                    ),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text(
                                          '${p.salePrice.toStringAsFixed(2)} ج.م',
                                          style: const TextStyle(
                                            fontFamily: 'Cairo',
                                            fontSize: 14,
                                            fontWeight: FontWeight.w900,
                                            color: AppColors.primary,
                                          ),
                                        ),
                                        CircleAvatar(
                                          radius: 14,
                                          backgroundColor: isOutOfStock ? AppColors.border : AppColors.primary,
                                          child: const Icon(Icons.add, size: 16, color: Colors.white),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),

      // Bottom Floating Cart Bar
      bottomNavigationBar: _cart.isEmpty
          ? null
          : Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                border: const Border(top: BorderSide(color: AppColors.border)),
                boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 10, offset: Offset(0, -2))],
              ),
              child: SafeArea(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('$_cartItemCount قطعة في السلة', style: const TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.textSecondary)),
                        Text('${_finalTotal.toStringAsFixed(2)} ج.م', style: const TextStyle(fontFamily: 'Cairo', fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.primary)),
                      ],
                    ),
                    ElevatedButton.icon(
                      onPressed: _showCartBottomSheet,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                      icon: const Icon(Icons.shopping_bag_rounded, color: Colors.white),
                      label: const Text('عرض السلة والدفع', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white)),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
