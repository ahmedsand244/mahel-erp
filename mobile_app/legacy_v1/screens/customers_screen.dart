import 'package:flutter/material.dart';
import '../models/customer.dart';
import '../services/offline_db_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class CustomersScreen extends StatefulWidget {
  const CustomersScreen({super.key});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  List<CustomerModel> _customers = [];
  List<CustomerModel> _filteredCustomers = [];
  bool _isLoading = true;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadCustomers();
  }

  Future<void> _loadCustomers() async {
    setState(() => _isLoading = true);
    final list = await OfflineDbService.instance.getOfflineCustomers();
    setState(() {
      _customers = list;
      _filteredCustomers = list;
      _isLoading = false;
    });

    ApiService.fetchCustomers().then((fresh) {
      if (mounted && fresh.isNotEmpty) {
        setState(() {
          _customers = fresh;
          _applyFilter();
        });
      }
    });
  }

  void _applyFilter() {
    final q = _searchController.text.trim().toLowerCase();
    setState(() {
      _filteredCustomers = _customers.where((c) {
        return q.isEmpty ||
            c.name.toLowerCase().contains(q) ||
            c.phone.toLowerCase().contains(q);
      }).toList();
    });
  }

  double get _totalDebts =>
      _customers.fold(0.0, (sum, c) => sum + (c.balance > 0 ? c.balance : 0.0));

  void _showAddCustomerDialog() {
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final balanceController = TextEditingController(text: '0.0');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.person_add_rounded, color: AppColors.primary),
            SizedBox(width: 8),
            Text('إضافة عميل جديد', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.textPrimary)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              style: const TextStyle(fontFamily: 'Cairo', color: AppColors.textPrimary),
              decoration: InputDecoration(
                labelText: 'اسم العميل *',
                labelStyle: const TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary),
                prefixIcon: const Icon(Icons.person_outline, color: AppColors.primary),
                filled: true,
                fillColor: AppColors.surfaceElevated,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: phoneController,
              keyboardType: TextInputType.phone,
              style: const TextStyle(fontFamily: 'Cairo', color: AppColors.textPrimary),
              decoration: InputDecoration(
                labelText: 'رقم الهاتف',
                labelStyle: const TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary),
                prefixIcon: const Icon(Icons.phone_outlined, color: AppColors.primary),
                filled: true,
                fillColor: AppColors.surfaceElevated,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: balanceController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(fontFamily: 'Cairo', color: AppColors.textPrimary),
              decoration: InputDecoration(
                labelText: 'الرصيد الافتتاحي (ديون سابقة إن وجدت)',
                labelStyle: const TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary),
                prefixIcon: const Icon(Icons.money_outlined, color: AppColors.primary),
                filled: true,
                fillColor: AppColors.surfaceElevated,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('إلغاء', style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () async {
              final name = nameController.text.trim();
              if (name.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('يرجى كتابة اسم العميل!', style: TextStyle(fontFamily: 'Cairo')), backgroundColor: AppColors.danger),
                );
                return;
              }

              final newCust = CustomerModel(
                id: DateTime.now().millisecondsSinceEpoch ~/ 1000,
                name: name,
                phone: phoneController.text.trim(),
                balance: double.tryParse(balanceController.text.trim()) ?? 0.0,
              );

              await OfflineDbService.instance.addOrUpdateCustomer(newCust);
              if (!mounted) return;
              Navigator.of(ctx).pop();
              _loadCustomers();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('تمت إضافة العميل بنجاح!', style: TextStyle(fontFamily: 'Cairo')), backgroundColor: AppColors.success),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('حفظ العميل', style: TextStyle(fontFamily: 'Cairo', color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showRecordPaymentDialog(CustomerModel customer) {
    final amountController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            const Icon(Icons.payments_rounded, color: AppColors.success),
            const SizedBox(width: 8),
            Text('سداد دفعة: ${customer.name}', style: const TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, fontSize: 16, color: AppColors.textPrimary)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('المديونية الحالية: ${customer.balance.toStringAsFixed(2)} ج.م', style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.danger, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: amountController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              autofocus: true,
              style: const TextStyle(fontFamily: 'Cairo', color: AppColors.textPrimary),
              decoration: InputDecoration(
                labelText: 'المبلغ المسدد (ج.م) *',
                labelStyle: const TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary),
                prefixIcon: const Icon(Icons.attach_money_rounded, color: AppColors.success),
                filled: true,
                fillColor: AppColors.surfaceElevated,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.border)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('إلغاء', style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () async {
              final amt = double.tryParse(amountController.text.trim()) ?? 0.0;
              if (amt <= 0) return;

              final updated = CustomerModel(
                id: customer.id,
                name: customer.name,
                phone: customer.phone,
                balance: (customer.balance - amt),
              );

              await OfflineDbService.instance.addOrUpdateCustomer(updated);
              if (!mounted) return;
              Navigator.of(ctx).pop();
              _loadCustomers();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('تم تسجيل سداد مبلغ $amt ج.م بنجاح!', style: const TextStyle(fontFamily: 'Cairo')), backgroundColor: AppColors.success),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('تأكيد السداد', style: TextStyle(fontFamily: 'Cairo', color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
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
        title: const Text('العملاء والديون (الشكك)', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
        actions: [
          IconButton(
            tooltip: 'تحديث قائمة العملاء',
            icon: const Icon(Icons.refresh_rounded, color: AppColors.primary),
            onPressed: _loadCustomers,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : Column(
              children: [
                // Top Debts Banner
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: AppStyles.glassCard(
                      border: AppColors.danger.withOpacity(0.3),
                      color: AppColors.dangerSubtle,
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('إجمالي الديون بالخارج (الشكك)', style: TextStyle(fontFamily: 'Cairo', fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.danger)),
                            Text('${_totalDebts.toStringAsFixed(2)} ج.م', style: const TextStyle(fontFamily: 'Cairo', fontSize: 22, fontWeight: FontWeight.w900, color: AppColors.danger)),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(color: AppColors.danger.withOpacity(0.2), borderRadius: BorderRadius.circular(14)),
                          child: const Icon(Icons.account_balance_wallet_rounded, color: AppColors.danger, size: 28),
                        ),
                      ],
                    ),
                  ),
                ),

                // Search Bar
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: TextField(
                    controller: _searchController,
                    onChanged: (_) => _applyFilter(),
                    style: const TextStyle(fontFamily: 'Cairo', color: AppColors.textPrimary),
                    decoration: InputDecoration(
                      hintText: 'ابحث باسم العميل أو رقم الهاتف...',
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
                const SizedBox(height: 10),

                // Customer List
                Expanded(
                  child: _filteredCustomers.isEmpty
                      ? const Center(child: Text('لا يوجد عملاء مسجلون بعد!', style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary)))
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredCustomers.length,
                          itemBuilder: (ctx, index) {
                            final c = _filteredCustomers[index];
                            final hasDebt = c.balance > 0;

                            return Container(
                              margin: const EdgeInsets.only(bottom: 10),
                              padding: const EdgeInsets.all(14),
                              decoration: AppStyles.glassCard(
                                border: hasDebt ? AppColors.warning.withOpacity(0.3) : null,
                              ),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    children: [
                                      CircleAvatar(
                                        backgroundColor: hasDebt ? AppColors.dangerSubtle : AppColors.primarySubtle,
                                        child: Icon(Icons.person_rounded, color: hasDebt ? AppColors.danger : AppColors.primary),
                                      ),
                                      const SizedBox(width: 12),
                                      Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(c.name, style: const TextStyle(fontFamily: 'Cairo', fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
                                          if (c.phone.isNotEmpty)
                                            Text(c.phone, style: const TextStyle(fontFamily: 'Cairo', fontSize: 12, color: AppColors.textSecondary)),
                                        ],
                                      ),
                                    ],
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text(
                                        '${c.balance.toStringAsFixed(2)} ج.م',
                                        style: TextStyle(
                                          fontFamily: 'Cairo',
                                          fontSize: 15,
                                          fontWeight: FontWeight.w900,
                                          color: hasDebt ? AppColors.danger : AppColors.success,
                                        ),
                                      ),
                                      if (hasDebt)
                                        TextButton(
                                          onPressed: () => _showRecordPaymentDialog(c),
                                          style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(50, 24)),
                                          child: const Text('سداد دفعة', style: TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.success, fontWeight: FontWeight.bold)),
                                        )
                                      else
                                        const Text('خالص الحساب', style: TextStyle(fontFamily: 'Cairo', fontSize: 10, color: AppColors.success)),
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
        onPressed: _showAddCustomerDialog,
        backgroundColor: AppColors.primary,
        icon: const Icon(Icons.person_add_rounded, color: Colors.white),
        label: const Text('عميل جديد', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: Colors.white)),
      ),
    );
  }
}
