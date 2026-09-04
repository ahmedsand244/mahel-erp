import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../services/offline_db_service.dart';
import '../models/invoice.dart';
import '../theme/app_theme.dart';

class DashboardScreen extends StatefulWidget {
  final Function(int)? onNavigateTab;
  const DashboardScreen({super.key, this.onNavigateTab});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _isLoading = true;
  bool _isSyncing = false;
  String _tenantName = 'النماء ERP & POS';
  bool _isCloud = false;

  double _todaySales = 0.0;
  int _todayOrders = 0;
  double _inventoryCost = 0.0;
  int _totalProducts = 0;
  int _lowStockCount = 0;
  List<OfflineInvoice> _recentInvoices = [];

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);
    final prefs = await SharedPreferences.getInstance();
    _tenantName = prefs.getString('tenant_name') ?? 'النماء ERP & POS';

    // 1. Fetch dashboard stats (tries Cloud, falls back to local SQLite)
    final stats = await ApiService.getDashboardStats();
    _isCloud = stats['is_cloud'] == true;
    _todaySales = (stats['today_sales'] ?? 0.0).toDouble();
    _todayOrders = stats['today_orders_count'] ?? 0;
    _inventoryCost = (stats['inventory_cost_val'] ?? 0.0).toDouble();
    _totalProducts = stats['total_products'] ?? 0;
    _lowStockCount = stats['low_stock_count'] ?? 0;

    // 2. Fetch recent invoices from local DB
    final allInvoices = await OfflineDbService.instance.getOfflineInvoices();
    _recentInvoices = allInvoices.take(5).toList();

    if (mounted) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _handleSync() async {
    setState(() => _isSyncing = true);
    final result = await ApiService.performFullSync();
    setState(() => _isSyncing = false);

    if (!mounted) return;

    if (result['success'] == true) {
      final pushed = result['pushed_invoices'] ?? 0;
      final prods = result['products_count'] ?? 0;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppColors.success,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          content: Text(
            'تمت المزامنة بنجاح! تم رفع $pushed فاتورة وتحديث $prods صنف.',
            style: const TextStyle(fontFamily: 'Cairo', fontWeight: FontWeight.bold),
          ),
        ),
      );
      _loadDashboardData();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: AppColors.danger,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          content: Text(
            'تعذر إتمام المزامنة السحابية (${result['error'] ?? 'خطأ في الاتصال'}). أنت تعمل بأمان محلياً.',
            style: const TextStyle(fontFamily: 'Cairo'),
          ),
        ),
      );
    }
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
            Text(
              _tenantName,
              style: const TextStyle(
                fontFamily: 'Cairo',
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppColors.textPrimary,
              ),
            ),
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: _isCloud ? AppColors.success : AppColors.warning,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  _isCloud ? 'متصل بالسحابة مباشر' : 'يعمل محلياً بدون نت (Offline)',
                  style: TextStyle(
                    fontFamily: 'Cairo',
                    fontSize: 11,
                    color: _isCloud ? AppColors.success : AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'تحديث ومزامنة',
            icon: _isSyncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                  )
                : const Icon(Icons.sync_rounded, color: AppColors.primary),
            onPressed: _isSyncing ? null : _handleSync,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : RefreshIndicator(
              onRefresh: _loadDashboardData,
              color: AppColors.primary,
              backgroundColor: AppColors.surface,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // --- Quick Sync Banner ---
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: AppStyles.glassCard(
                      border: AppColors.primary.withOpacity(0.3),
                      color: AppColors.primarySubtle,
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.cloud_done_rounded, color: AppColors.primary, size: 22),
                            SizedBox(width: 10),
                            Text(
                              'مزامنة شاملة ثنائية الاتجاه',
                              style: TextStyle(
                                fontFamily: 'Cairo',
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ],
                        ),
                        ElevatedButton.icon(
                          onPressed: _isSyncing ? null : _handleSync,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          ),
                          icon: const Icon(Icons.sync, size: 16, color: Colors.white),
                          label: Text(
                            _isSyncing ? 'جاري...' : 'مزامنة الآن',
                            style: const TextStyle(fontFamily: 'Cairo', fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // --- Quick Navigation Bar ---
                  Row(
                    children: [
                      Expanded(
                        child: _buildQuickActionButton(
                          icon: Icons.point_of_sale_rounded,
                          title: 'شاشة البيع POS',
                          color: AppColors.primary,
                          onTap: () => widget.onNavigateTab?.call(1),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildQuickActionButton(
                          icon: Icons.inventory_2_rounded,
                          title: 'إدارة المخزن',
                          color: AppColors.success,
                          onTap: () => widget.onNavigateTab?.call(2),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _buildQuickActionButton(
                          icon: Icons.people_alt_rounded,
                          title: 'العملاء والديون',
                          color: AppColors.warning,
                          onTap: () => widget.onNavigateTab?.call(3),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // --- Section Title ---
                  const Text(
                    'مؤشرات الأداء المالي والمخزون',
                    style: TextStyle(
                      fontFamily: 'Cairo',
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 12),

                  // --- 4 KPI STAT CARDS (Apple-Style) ---
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 1.35,
                    children: [
                      // Card 1: Today's Sales
                      _buildStatCard(
                        title: 'مبيعات اليوم',
                        value: '${_todaySales.toStringAsFixed(2)} ج.م',
                        subtitle: 'مبيعات الكاش والآجل',
                        icon: Icons.trending_up_rounded,
                        accentColor: AppColors.primary,
                      ),
                      // Card 2: Today's Orders
                      _buildStatCard(
                        title: 'عدد الفواتير',
                        value: '$_todayOrders فاتورة',
                        subtitle: 'المسجلة خلال اليوم',
                        icon: Icons.receipt_long_rounded,
                        accentColor: AppColors.success,
                      ),
                      // Card 3: Inventory Capital
                      _buildStatCard(
                        title: 'قيمة المخزون',
                        value: '${_inventoryCost.toStringAsFixed(1)} ج.م',
                        subtitle: '$_totalProducts صنف مسجل',
                        icon: Icons.storefront_rounded,
                        accentColor: const Color(0xFF8B5CF6),
                      ),
                      // Card 4: Low Stock Alert
                      _buildStatCard(
                        title: 'نواقص البضاعة',
                        value: '$_lowStockCount صنف',
                        subtitle: 'أقل من 5 قطع',
                        icon: Icons.warning_amber_rounded,
                        accentColor: AppColors.danger,
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // --- Recent Invoices Section ---
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'آخر فواتير المبيعات',
                        style: TextStyle(
                          fontFamily: 'Cairo',
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      TextButton(
                        onPressed: () => widget.onNavigateTab?.call(4),
                        child: const Text(
                          'عرض الكل',
                          style: TextStyle(fontFamily: 'Cairo', color: AppColors.primary, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  if (_recentInvoices.isEmpty)
                    Container(
                      padding: const EdgeInsets.all(24),
                      decoration: AppStyles.glassCard(),
                      child: const Center(
                        child: Text(
                          'لا توجد فواتير مسجلة اليوم حتى الآن.',
                          style: TextStyle(fontFamily: 'Cairo', color: AppColors.textSecondary),
                        ),
                      ),
                    )
                  else
                    ..._recentInvoices.map((inv) => _buildInvoiceItemTile(inv)),
                ],
              ),
            ),
    );
  }

  Widget _buildQuickActionButton({
    required IconData icon,
    required String title,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        decoration: AppStyles.glassCard(
          color: color.withOpacity(0.08),
          border: color.withOpacity(0.25),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 26),
            const SizedBox(height: 6),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: 'Cairo',
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatCard({
    required String title,
    required String value,
    required String subtitle,
    required IconData icon,
    required Color accentColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: AppStyles.glassCard(
        border: accentColor.withOpacity(0.2),
        color: AppColors.surface,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontFamily: 'Cairo',
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: accentColor,
                ),
              ),
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: accentColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: accentColor, size: 18),
              ),
            ],
          ),
          Text(
            value,
            style: const TextStyle(
              fontFamily: 'Cairo',
              fontSize: 18,
              fontWeight: FontWeight.w900,
              color: AppColors.textPrimary,
            ),
          ),
          Text(
            subtitle,
            style: const TextStyle(
              fontFamily: 'Cairo',
              fontSize: 10,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInvoiceItemTile(OfflineInvoice inv) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: AppStyles.glassCard(),
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
                      ? Icons.attach_money_rounded
                      : Icons.credit_score_rounded,
                  color: inv.paymentMethod == 'cash' ? AppColors.success : AppColors.warning,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    inv.customerName ?? 'زبون نقدي',
                    style: const TextStyle(
                      fontFamily: 'Cairo',
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  Text(
                    '${inv.items.length} صنف • ${inv.createdAt.hour}:${inv.createdAt.minute.toString().padLeft(2, '0')}',
                    style: const TextStyle(
                      fontFamily: 'Cairo',
                      fontSize: 11,
                      color: AppColors.textSecondary,
                    ),
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
                style: const TextStyle(
                  fontFamily: 'Cairo',
                  fontSize: 15,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textPrimary,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: inv.isSynced ? AppColors.successSubtle : AppColors.warningSubtle,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  inv.isSynced ? 'متزامنة سحابياً' : 'محفوظة محلياً',
                  style: TextStyle(
                    fontFamily: 'Cairo',
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    color: inv.isSynced ? AppColors.success : AppColors.warning,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
