import 'package:flutter/material.dart';
import '../models/invoice.dart';
import '../services/offline_db_service.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class InvoicesScreen extends StatefulWidget {
  const InvoicesScreen({super.key});

  @override
  State<InvoicesScreen> createState() => _InvoicesScreenState();
}

class _InvoicesScreenState extends State<InvoicesScreen> {
  List<OfflineInvoice> _invoices = [];
  bool _isLoading = true;
  bool _isSyncing = false;
  int _unsyncedCount = 0;

  @override
  void initState() {
    super.initState();
    _loadInvoices();
  }

  Future<void> _loadInvoices() async {
    setState(() => _isLoading = true);
    final list = await OfflineDbService.instance.getOfflineInvoices();
    final unsynced = list.where((inv) => !inv.isSynced).length;
    setState(() {
      _invoices = list;
      _unsyncedCount = unsynced;
      _isLoading = false;
    });
  }

  Future<void> _syncNow() async {
    setState(() => _isSyncing = true);
    final pushed = await ApiService.syncPendingInvoices();
    setState(() => _isSyncing = false);

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: pushed > 0 ? AppColors.success : AppColors.warning,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        content: Text(
          pushed > 0
              ? 'تم رفع $pushed فاتورة للسحابة بنجاح!'
              : 'لا توجد فواتير جديدة للمزامنة أو لا يوجد اتصال.',
          style: const TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold),
        ),
      ),
    );
    _loadInvoices();
  }

  void _showInvoiceDetails(OfflineInvoice inv) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(20),
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.75),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.receipt_long_rounded, color: AppColors.primary),
                    const SizedBox(width: 8),
                    Text(
                      'فاتورة: ${inv.clientId.replaceAll('MOB-', '')}',
                      style: const TextStyle(fontFamily: 'Cairo', fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: AppColors.textSecondary),
                  onPressed: () => Navigator.of(ctx).pop(),
                ),
              ],
            ),
            const Divider(color: AppColors.border),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'العميل: ${inv.customerName ?? "زبون نقدي"}',
                      style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'التاريخ: ${inv.createdAt.year}/${inv.createdAt.month.toString().padLeft(2, '0')}/${inv.createdAt.day.toString().padLeft(2, '0')} '
                      '${inv.createdAt.hour}:${inv.createdAt.minute.toString().padLeft(2, '0')}',
                      style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'طريقة الدفع: ${inv.paymentMethod == "cash" ? "نقدي (كاش)" : "آجل (شكك)"}',
                      style: TextStyle(
                        fontFamily: 'Cairo',
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: inv.paymentMethod == 'cash' ? AppColors.success : AppColors.warning,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: inv.isSynced ? AppColors.successSubtle : AppColors.warningSubtle,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    inv.isSynced ? '✓ متزامنة' : '⏳ محلية',
                    style: TextStyle(
                      fontFamily: 'Cairo',
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: inv.isSynced ? AppColors.success : AppColors.warning,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Text('تفاصيل الأصناف:', style: TextStyle(fontFamily: 'Cairo', fontSize: 14, fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                itemCount: inv.items.length,
                itemBuilder: (ctx, i) {
                  final item = inv.items[i];
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceElevated,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            item.productName,
                            style: const TextStyle(fontFamily: 'Cairo', fontSize: 13, color: AppColors.textPrimary),
                          ),
                        ),
                        Text(
                          '${item.quantity} × ${item.unitPrice.toStringAsFixed(2)} = ${item.totalPrice.toStringAsFixed(2)} ج.م',
                          style: const TextStyle(fontFamily: 'Cairo', fontSize: 12, color: AppColors.primary, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            const Divider(color: AppColors.border),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('الإجمالي النهائي:', style: TextStyle(fontFamily: 'Cairo', fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.textSecondary)),
                Text(
                  '${inv.totalAmount.toStringAsFixed(2)} ج.م',
                  style: const TextStyle(fontFamily: 'Cairo', fontSize: 20, fontWeight: FontWeight.w900, color: AppColors.primary),
                ),
              ],
            ),
          ],
        ),
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
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('سجل الفواتير', style: TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold, color: AppColors.textPrimary)),
            if (_unsyncedCount > 0)
              Text(
                '$_unsyncedCount فاتورة تنتظر المزامنة السحابية',
                style: const TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.warning),
              ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'مزامنة الفواتير مع السحابة',
            icon: _isSyncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                  )
                : Badge(
                    isLabelVisible: _unsyncedCount > 0,
                    label: Text('$_unsyncedCount', style: const TextStyle(fontSize: 10)),
                    backgroundColor: AppColors.warning,
                    child: const Icon(Icons.cloud_upload_rounded, color: AppColors.primary),
                  ),
            onPressed: _isSyncing ? null : _syncNow,
          ),
          IconButton(
            tooltip: 'تحديث القائمة',
            icon: const Icon(Icons.refresh_rounded, color: AppColors.textSecondary),
            onPressed: _loadInvoices,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _invoices.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.receipt_long_rounded, size: 60, color: AppColors.textSecondary),
                      const SizedBox(height: 12),
                      const Text('لا توجد فواتير مسجلة بعد!', style: TextStyle(fontFamily: 'Cairo', fontSize: 15, color: AppColors.textSecondary)),
                      const SizedBox(height: 8),
                      const Text('ابدأ بفتح شاشة البيع POS لإصدار أول فاتورة.', style: TextStyle(fontFamily: 'Cairo', fontSize: 12, color: AppColors.textSecondary), textAlign: TextAlign.center),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadInvoices,
                  color: AppColors.primary,
                  backgroundColor: AppColors.surface,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _invoices.length,
                    itemBuilder: (ctx, index) {
                      final inv = _invoices[index];
                      return InkWell(
                        onTap: () => _showInvoiceDetails(inv),
                        borderRadius: BorderRadius.circular(18),
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 10),
                          padding: const EdgeInsets.all(14),
                          decoration: AppStyles.glassCard(
                            border: inv.isSynced ? null : AppColors.warning.withOpacity(0.3),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(10),
                                    decoration: BoxDecoration(
                                      color: inv.paymentMethod == 'cash'
                                          ? AppColors.successSubtle
                                          : AppColors.warningSubtle,
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Icon(
                                      inv.paymentMethod == 'cash'
                                          ? Icons.payments_rounded
                                          : Icons.credit_card_rounded,
                                      color: inv.paymentMethod == 'cash'
                                          ? AppColors.success
                                          : AppColors.warning,
                                      size: 20,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        inv.customerName ?? 'زبون نقدي',
                                        style: const TextStyle(fontFamily: 'Cairo', fontSize: 14, fontWeight: FontWeight.bold, color: AppColors.textPrimary),
                                      ),
                                      Text(
                                        '${inv.items.length} صنف • '
                                        '${inv.createdAt.day}/${inv.createdAt.month}/${inv.createdAt.year}',
                                        style: const TextStyle(fontFamily: 'Cairo', fontSize: 11, color: AppColors.textSecondary),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(
                                    '${inv.totalAmount.toStringAsFixed(2)} ج.م',
                                    style: const TextStyle(fontFamily: 'Cairo', fontSize: 15, fontWeight: FontWeight.w900, color: AppColors.textPrimary),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: inv.isSynced ? AppColors.successSubtle : AppColors.warningSubtle,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      inv.isSynced ? '✓ سحابة' : '⏳ محلية',
                                      style: TextStyle(fontFamily: 'Cairo', fontSize: 9, fontWeight: FontWeight.bold, color: inv.isSynced ? AppColors.success : AppColors.warning),
                                    ),
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
    );
  }
}
