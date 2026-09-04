import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:decimal/decimal.dart';
import '../../domain/pos_models.dart';
import 'package:mahel_pos_mobile/features/pos/presentation/providers/pos_providers.dart';
// no delegate
import 'package:mahel_pos_mobile/core/theme/app_theme.dart';
import 'package:mahel_pos_mobile/shared/widgets/app_button.dart';
import 'package:mahel_pos_mobile/shared/widgets/app_text_field.dart';

class PosScreen extends ConsumerStatefulWidget {
  const PosScreen({super.key});

  @override
  ConsumerState<PosScreen> createState() => _PosScreenState();
}

class _PosScreenState extends ConsumerState<PosScreen> {
  final _searchController = TextEditingController();
  bool _isCustomerDropdownOpen = false;
  String _customerSearchQuery = '';
  bool _showSuccessModal = false;
  String _successOrderNumber = '';
  int? _successOrderId;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cart = ref.watch(cartProvider);
    final products = ref.watch(productListProvider); // Will create this
    final customers = ref.watch(customerListProvider); // Will create this
    final selectedCustomer = ref.watch(selectedCustomerProvider);
    final paymentMethod = ref.watch(paymentMethodProvider);
    final isOnline = ref.watch(isOnlineProvider);
    final searchQuery = ref.watch(searchQueryProvider);

    final filteredProducts = products.where((p) {
      if (searchQuery.isEmpty) return true;
      final q = searchQuery.toLowerCase();
      return p.name.toLowerCase().contains(q) ||
          p.sku.toLowerCase().contains(q) ||
          (p.barcode?.toLowerCase().contains(q) ?? false);
    }).toList();

    final cartTotal = ref.watch(cartProvider.notifier).total;

    return Scaffold(
      body: Directionality(
        textDirection: TextDirection.rtl,
        child: CustomScrollView(
          slivers: [
            // Offline/Online Status Banner
            SliverToBoxAdapter(
              child: Container(
                margin: const EdgeInsets.all(16),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isOnline
                      ? theme.colorScheme.primary.withOpacity(0.1)
                      : theme.colorScheme.tertiary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isOnline
                        ? theme.colorScheme.primary.withOpacity(0.3)
                        : theme.colorScheme.tertiary.withOpacity(0.3),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      isOnline ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                      color: isOnline ? theme.colorScheme.primary : theme.colorScheme.tertiary,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        isOnline
                            ? 'Ù…ØªØµÙ„ Ø¨Ø§Ù„Ø³ÙŠØ±ÙØ± (Ø£ÙˆÙ†Ù„Ø§ÙŠÙ†) ðŸŸ¢'
                            : 'ÙŠØ¹Ù…Ù„ Ø¨Ø¯ÙˆÙ† Ø¥Ù†ØªØ±Ù†Øª (Ø£ÙˆÙÙ„Ø§ÙŠÙ† Ù…ØªØ§Ø­ Ù„Ù„Ø¨ÙŠØ¹) ðŸŸ¡',
                        style: GoogleFonts.cairo(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: isOnline ? theme.colorScheme.primary : theme.colorScheme.tertiary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Search Bar & Barcode Scanner
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    Expanded(
                      child: AppTextField(
                        controller: _searchController,
                        hintText: 'Ø§Ø¨Ø­Ø« Ø¹Ù† Ù…Ù†ØªØ¬ Ø¨Ø§Ù„Ø§Ø³Ù… Ø£Ùˆ Ø±Ù…Ø² Ø§Ù„Ø¨Ø§Ø±ÙƒÙˆÙˆØ¯...',
                        prefixIcon: const Icon(Icons.search),
                        onChanged: (v) => ref.read(searchQueryProvider.notifier).state = v,
                      ),
                    ),
                    const SizedBox(width: 12),
                    AppButton.icon(
                      icon: Icons.photo_camera,
                      label: 'Ù…Ø³Ø­ Ø¨Ø§Ù„Ø¨Ø§Ø±ÙƒÙˆØ¯',
                      onPressed: _openBarcodeScanner,
                      backgroundColor: theme.colorScheme.primary.withOpacity(0.15),
                      foregroundColor: theme.colorScheme.primary,
                    ),
                  ],
                ),
              ),
            ),

            // Products Grid
            SliverPadding(
              padding: const EdgeInsets.all(16),
              sliver: SliverGrid(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 0.9,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                ),
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final product = filteredProducts[index];
                    return _buildProductCard(product, theme);
                  },
                  childCount: filteredProducts.length,
                ),
              ),
            ),

            // Cart & Checkout - Bottom Sheet Style
            SliverToBoxAdapter(
              child: _buildCartBottomSheet(context, theme, cart, cartTotal, selectedCustomer, paymentMethod),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProductCard(ProductApi product, ThemeData theme) {
    final isLowStock = product.stockQuantity <= 3;
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: InkWell(
        onTap: () => _addToCart(product),
        borderRadius: BorderRadius.circular(18),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Stack(
                children: [
                  AspectRatio(
                    aspectRatio: 1,
                    child: Container(
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.2)),
                      ),
                      child: product.imagePath != null
                          ? ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: Image.asset(
                                product.imagePath!,
                                fit: BoxFit.cover,
                              ),
                            )
                          : Center(
                              child: Icon(
                                Icons.inventory_2_rounded,
                                size: 40,
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                    ),
                  ),
                  Positioned(
                    top: 8,
                    right: 8,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: isLowStock
                            ? theme.colorScheme.error.withOpacity(0.9)
                            : theme.colorScheme.primary.withOpacity(0.9),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        isLowStock ? 'Ù…Ù†Ø®ÙØ¶ (${product.stockQuantity})' : 'Ù…ØªÙˆÙØ± (${product.stockQuantity})',
                        style: GoogleFonts.cairo(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                product.name,
                style: GoogleFonts.cairo(fontSize: 13, fontWeight: FontWeight.bold),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                'SKU: ${product.sku}',
                style: GoogleFonts.cairo(fontSize: 10, color: theme.colorScheme.onSurfaceVariant),
              ),
              const Spacer(),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${product.salePrice.toStringAsFixed(2)} Ø¬.Ù…',
                    style: GoogleFonts.cairo(
                      fontSize: 15,
                      fontWeight: FontWeight.w900,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  Container(
                    decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withOpacity(0.1),
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      icon: const Icon(Icons.add, size: 18),
                      onPressed: () => _addToCart(product),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCartBottomSheet(
    BuildContext context,
    ThemeData theme,
    List<CartItem> cart,
    Decimal cartTotal,
    int? selectedCustomer,
    PaymentMethod paymentMethod,
  ) {
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(top: BorderSide(color: theme.colorScheme.outline.withOpacity(0.3))),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 20,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle bar
          Container(
            margin: const EdgeInsets.only(top: 12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: theme.colorScheme.onSurfaceVariant.withOpacity(0.4),
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Customer Selection
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: () => _openCustomerSelector(context),
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.3)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.person_rounded, color: theme.colorScheme.onSurfaceVariant),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              selectedCustomer != null
                                  ? _getCustomerName(customers, selectedCustomer)
                                  : 'Ø¹Ù…ÙŠÙ„ Ù†Ù‚Ø¯ÙŠ Ø³Ø±ÙŠØ¹',
                              style: GoogleFonts.cairo(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: theme.colorScheme.onSurface,
                              ),
                            ),
                          ),
                          if (selectedCustomer != null)
                            IconButton(
                              icon: Icon(Icons.close, size: 18, color: theme.colorScheme.onSurfaceVariant),
                              onPressed: () => ref.read(selectedCustomerProvider.notifier).state = null,
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                AppButton.icon(
                  icon: Icons.person_add,
                  label: '+ Ø¹Ù…ÙŠÙ„ Ø¬Ø¯ÙŠØ¯',
                  onPressed: _openAddCustomerModal,
                  backgroundColor: theme.colorScheme.primary.withOpacity(0.1),
                  foregroundColor: theme.colorScheme.primary,
                ),
              ],
            ),
          ),

          // Cart Items
          if (cart.isEmpty)
            Padding(
              padding: const EdgeInsets.all(32),
              child: Center(
                child: Text(
                  'Ø³Ù„Ø© Ø§Ù„Ù…Ø´ØªØ±ÙŠØ§Øª ÙØ§Ø±ØºØ©. Ø§Ø¶ØºØ· Ø¹Ù„Ù‰ Ø£ÙŠ Ù…Ù†ØªØ¬ Ù„Ø¥Ø¶Ø§ÙØªÙ‡.',
                  style: GoogleFonts.cairo(color: theme.colorScheme.onSurfaceVariant, fontSize: 13),
                ),
              ),
            )
          else
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: cart.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final item = cart[index];
                  return _buildCartItem(item, theme);
                },
              ),
            ),

          // Totals & Payment
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
              border: Border(top: BorderSide(color: theme.colorScheme.outline.withOpacity(0.3))),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Ø§Ù„Ù…Ø¬Ù…ÙˆØ¹ Ø§Ù„Ø¥Ø¬Ù…Ø§Ù„ÙŠ',
                      style: GoogleFonts.cairo(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      '${cartTotal.toStringAsFixed(2)} Ø¬.Ù…',
                      style: GoogleFonts.cairo(
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _buildPaymentMethodSelector(paymentMethod, theme),
                const SizedBox(height: 16),
                AppButton(
                  label: 'Ø¥ØªÙ…Ø§Ù… Ø§Ù„ÙØ§ØªÙˆØ±Ø©',
                  icon: Icons.shopping_basket,
                  onPressed: cart.isEmpty || _isSubmitting ? null : _submitCheckout,
                  isLoading: _isSubmitting,
                  fullWidth: true,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCartItem(CartItem item, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.name,
                  style: GoogleFonts.cairo(fontSize: 13, fontWeight: FontWeight.bold),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  '${item.price.toStringAsFixed(2)} Ø¬.Ù…',
                  style: GoogleFonts.cairo(fontSize: 12, fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
                ),
              ],
            ),
          ),
          Row(
            children: [
              IconButton(
                icon: const Icon(Icons.remove, size: 18),
                onPressed: () => ref.read(cartProvider.notifier).decreaseQuantity(item.productId),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
              ),
              Text(
                '${item.quantity}',
                style: GoogleFonts.cairo(fontSize: 14, fontWeight: FontWeight.bold),
              ),
              IconButton(
                icon: const Icon(Icons.add, size: 18),
                onPressed: () => ref.read(cartProvider.notifier).increaseQuantity(item.productId),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
              ),
            ],
          ),
          const SizedBox(width: 8),
          Text(
            '${item.totalPrice.toStringAsFixed(2)} Ø¬.Ù…',
            style: GoogleFonts.cairo(fontSize: 13, fontWeight: FontWeight.bold, color: theme.colorScheme.primary),
          ),
          IconButton(
            icon: Icon(Icons.delete, color: theme.colorScheme.error, size: 20),
            onPressed: () => ref.read(cartProvider.notifier).removeItem(item.productId),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
          ),
        ],
      );
    }
  }

  Widget _buildPaymentMethodSelector(PaymentMethod selected, ThemeData theme) {
    return Row(
      children: [
        _paymentMethodButton(PaymentMethod.cash(), selected, theme),
        const SizedBox(width: 8),
        _paymentMethodButton(PaymentMethod.visa(), selected, theme),
        const SizedBox(width: 8),
        _paymentMethodButton(PaymentMethod.deferred(), selected, theme),
      ],
    );
  }

  Widget _paymentMethodButton(PaymentMethod method, PaymentMethod selected, ThemeData theme) {
    final isSelected = method == selected;
    return Expanded(
      child: InkWell(
        onTap: () => ref.read(paymentMethodProvider.notifier).state = method,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected
                ? theme.colorScheme.primary.withOpacity(0.15)
                : theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isSelected ? theme.colorScheme.primary : theme.colorScheme.outline.withOpacity(0.3),
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Column(
            children: [
              Icon(
                IconData(
                  method.icon == 'payments' ? 0xe4b8 : method.icon == 'credit_card' ? 0xe870 : 0xe2d4,
                  fontFamily: 'MaterialSymbols',
                ),
                size: 24,
                color: isSelected ? theme.colorScheme.primary : theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(height: 4),
              Text(
                method.displayName,
                style: GoogleFonts.cairo(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: isSelected ? theme.colorScheme.primary : theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _addToCart(ProductApi product) {
    ref.read(cartProvider.notifier).addItem(CartItem(
      productId: product.id,
      name: product.name,
      price: Decimal.fromDouble(product.salePrice),
      quantity: 1,
    ));
    // Haptic feedback
  }

  void _openBarcodeScanner() {
    // TODO: Implement barcode scanner
  }

  void _openCustomerSelector(BuildContext context) {
    // TODO: Implement customer selector modal
  }

  void _openAddCustomerModal() {
    // TODO: Implement add customer modal
  }

  Future<void> _submitCheckout() async {
    setState(() => _isSubmitting = true);

    final cart = ref.read(cartProvider);
    final paymentMethod = ref.read(paymentMethodProvider);
    final selectedCustomer = ref.read(selectedCustomerProvider);

    if (paymentMethod is PaymentMethod.deferred && selectedCustomer == null) {
      // Show error
      setState(() => _isSubmitting = false);
      return;
    }

    // Generate order number
    final orderNumber = 'POS-${DateTime.now().millisecondsSinceEpoch}';

    // Calculate totals
    Decimal totalAmount = Decimal.zero;
    Decimal totalCost = Decimal.zero;
    
    for (final item in cart) {
      totalAmount += item.totalPrice;
      // Would need product cost from database
    }

    try {
      await ref.read(posRepositoryProvider).createOrder(
        orderNumber: orderNumber,
        paymentMethod: paymentMethod.when(
          cash: () => 'cash',
          visa: () => 'visa',
          deferred: () => 'deferred',
        ),
        customerId: selectedCustomer,
        items: cart,
        totalAmount: totalAmount,
        costOfGoodsSold: totalCost,
        tenantId: 1,
      );

      ref.read(cartProvider.notifier).clear();
      
      setState(() {
        _successOrderNumber = orderNumber;
        _successOrderId = 1; // Would get actual ID
        _showSuccessModal = true;
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() => _isSubmitting = false);
      // Show error
    }
  }

  String _getCustomerName(List<CustomerApi> customers, int id) {
    final customer = customers.firstWhere((c) => c.id == id, orElse: () => CustomerApi(id: 0, name: '', phone: '', balance: 0));
    return customer.name;
  }
}

// Placeholder providers - will be created in inventory/ledger features
final productListProvider = StateProvider<List<ProductApi>>((ref) => []);
final customerListProvider = StateProvider<List<CustomerApi>>((ref) => []);
