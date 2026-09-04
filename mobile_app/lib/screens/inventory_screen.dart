import 'package:flutter/material.dart';
import '../models/product.dart';
import '../services/offline_db_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key});

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  List<ProductModel> _products = [];
  List<ProductModel> _filteredProducts = [];
  bool _isLoading = true;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  Future<void> _loadProducts() async {
    setState(() => _isLoading = true);
    final list = await OfflineDbService.instance.getOfflineProducts();
    setState(() {
      _products = list;
      _filteredProducts = list;
      _isLoading = false;
    });

    ApiService.fetchProducts().then((fresh) {
      if (mounted && fresh.isNotEmpty) {
        setState(() {
          _products = fresh;
          _applyFilter();
        });
      }
    });
  }

  void _applyFilter() {
    final q = _searchController.text.trim().toLowerCase();
    setState(() {
      _filteredProducts = _products.where((p) {
        return q.isEmpty ||
            p.name.toLowerCase().contains(q) ||
            p.barcode.toLowerCase().contains(q) ||
            p.sku.toLowerCase().contains(q) ||
            p.categoryName.toLowerCase().contains(q);
      }).toList();
    });
  }

  void _showAddProductDialog() {
    final nameController = TextEditingController();
    final barcodeController = TextEditingController();
    final priceController = TextEditingController();
    final costController = TextEditingController();
    final qtyController = TextEditingController(text: '10');
    final categoryController = TextEditingController(text: 'عام');
    final unitController = TextEditingController(text: 'حبة');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.add_box_rounded, color: AppColors.primary),
            SizedBox(width: 8),
            Text('إضافة صنف جديد للمخزن', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.textPrimary)),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildDialogField('اسم الصنف *', nameController, Icons.label_outline),
              const SizedBox(height: 10),
              _buildDialogField('الباركود / الكود', barcodeController, Icons.qr_code_2_rounded),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(child: _buildDialogField('سعر البيع *', priceController, Icons.attach_money_rounded, isNumber: true)),
                  const SizedBox(width: 8),
                  Expanded(child: _buildDialogField('سعر التكلفة', costController, Icons.money_off_rounded, isNumber: true)),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(child: _buildDialogField('الكمية *', qtyController, Icons.numbers_rounded, isNumber: true)),
                  const SizedBox(width: 8),
                  Expanded(child: _buildDialogField('الوحدة', unitController, Icons.straighten_rounded)),
                ],
              ),
              const SizedBox(height: 10),
              _buildDialogField('التصنيف', categoryController, Icons.category_outlined),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('إلغاء', style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () async {
              final name = nameController.text.trim();
              final price = double.tryParse(priceController.text.trim()) ?? 0.0;
              final cost = double.tryParse(costController.text.trim()) ?? 0.0;
              final qty = int.tryParse(qtyController.text.trim()) ?? 0;

              if (name.isEmpty || price <= 0) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('يرجى كتابة اسم الصنف وسعر البيع!', style: TextStyle(fontFamily: 'Cairo')), backgroundColor: AppColors.danger),
                );
                return;
              }

              final newProd = ProductModel(
                id: DateTime.now().millisecondsSinceEpoch ~/ 1000,
                name: name,
                sku: 'SKU-${DateTime.now().millisecondsSinceEpoch % 10000}',
                barcode: barcodeController.text.trim(),
                salePrice: price,
                costPrice: cost,
                stockQuantity: qty,
                unit: unitController.text.trim().isNotEmpty ? unitController.text.trim() : 'حبة',
                categoryName: categoryController.text.trim().isNotEmpty ? categoryController.text.trim() : 'عام',
              );

              await OfflineDbService.instance.addOrUpdateProduct(newProd);
              if (!mounted) return;
              Navigator.of(ctx).pop();
              _loadProducts();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('تمت إضافة الصنف وحفظه بنجاح!', style: TextStyle(fontFamily: 'Cairo')), backgroundColor: AppColors.success),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('حفظ الصنف', style: TextStyle(fontFamily: 'Cairo', color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildDialogField(String label, TextEditingController controller, IconData icon, {bool isNumber = false}) {
    return TextField(
      controller: controller,
      keyboardType: isNumber ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
      style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textPrimary),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(fontFamily: 'Cairo', fontSize: 12, color: AppColors.textSecondary),
        prefixIcon: Icon(icon, color: AppColors.primary, size: 20),
        filled: true,
        fillColor: AppColors.surfaceElevated,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        title: const Text('المخزن والمنتجات', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
        actions: [
          IconButton(
            tooltip: 'تحديث المخزن',
            icon: const Icon(Icons.refresh_rounded, color: AppColors.primary),
            onPressed: _loadProducts,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: TextField(
                    controller: _searchController,
                    onChanged: (_) => _applyFilter(),
                    style: const TextStyle(fontFamily: 'Cairo', color: AppColors.textPrimary),
                    decoration: InputDecoration(
                      hintText: 'ابحث في المخزن باسم الصنف أو الباركود...',
                      hintStyle: const TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary, fontSize: 13),
                      prefixIcon: const Icon(Icons.search_rounded, color: AppColors.primary),
                      filled: true,
                      fillColor: AppColors.surface,
                      contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.border)),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppColors.border)),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'إجمالي الأصناف: ${_filteredProducts.length}',
                        style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.textSecondary),
                      ),
                      Text(
                        'نواقص: ${_products.where((p) => p.stockQuantity <= 5).length}',
                        style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.danger),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: _filteredProducts.isEmpty
                      ? const Center(child: Text('لا توجد أصناف بالمخزن!', style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary)))
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredProducts.length,
                          itemBuilder: (ctx, index) {
                            final p = _filteredProducts[index];
                            final isLow = p.stockQuantity <= 5 && p.stockQuantity > 0;
                            final isOut = p.stockQuantity <= 0;

                            return Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(14),
                              decoration: AppStyles.glassCard(
                                border: isOut ? AppColors.danger.withOpacity(0.3) : null,
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          p.name,
                                          style: const TextStyle(fontFamily: 'Cairo', fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                                        ),
                                        const SizedBox(height: 4),
                                        Row(
                                          children: [
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(color: AppColors.surfaceElevated, borderRadius: BorderRadius.circular(6)),
                                              child: Text(p.categoryName, style: const TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.textSecondary)),
                                            ),
                                            if (p.barcode.isNotEmpty) ...[
                                              const SizedBox(width: 8),
                                              Text(p.barcode, style: const TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.textSecondary)),
                                            ],
                                          ],
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          'سعر البيع: ${p.salePrice.toStringAsFixed(2)} ج.م  •  التكلفة: ${p.costPrice.toStringAsFixed(2)} ج.م',
                                          style: const TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.primary),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: isOut
                                              ? AppColors.dangerSubtle
                                              : (isLow ? AppColors.warningSubtle : AppColors.successSubtle),
                                          borderRadius: BorderRadius.circular(10),
                                        ),
                                        child: Text(
                                          isOut ? 'نفد' : '${p.stockQuantity} ${p.unit}',
                                          style: TextStyle(
                                            fontFamily: 'Cairo',
                                            fontSize: 13,
                                            fontWeight: FontWeight.bold,
                                            color: isOut
                                                ? AppColors.danger
                                                : (isLow ? AppColors.warning : AppColors.success),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddProductDialog,
        backgroundColor: AppColors.primary,
        icon: const Icon(Icons.add_rounded, color: Colors.white),
        label: const Text('إضافة صنف', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: Colors.white)),
      ),
    );
  }
}
