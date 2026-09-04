import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/product.dart';
import '../models/customer.dart';
import '../models/invoice.dart';
import 'offline_db_service.dart';

class ApiService {
  static const String defaultBaseUrl = 'https://webservises.pythonanywhere.com';

  static Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('custom_server_url') ?? defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    var cleanUrl = url.trim();
    if (cleanUrl.endsWith('/')) {
      cleanUrl = cleanUrl.substring(0, cleanUrl.length - 1);
    }
    await prefs.setString('custom_server_url', cleanUrl);
  }

  static Future<String?> getTenantSlug() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('tenant_slug') ?? 'mahel';
  }

  // --- LOGIN ---
  static Future<Map<String, dynamic>> login(String username, String password, {String? tenantSlug}) async {
    try {
      final baseUrl = await getBaseUrl();
      final url = Uri.parse('$baseUrl/api/v1/login/');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
          'tenant_slug': tenantSlug,
        }),
      ).timeout(const Duration(seconds: 12));

      final data = jsonDecode(utf8.decode(response.bodyBytes));
      if (response.statusCode == 200 && data['success'] == true) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('username', username);
        if (data['tenant'] != null) {
          await prefs.setString('tenant_slug', data['tenant']['slug'] ?? 'mahel');
          await prefs.setString('tenant_name', data['tenant']['name'] ?? 'النماء ERP');
        }
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': data['error'] ?? 'فشل تسجيل الدخول'};
      }
    } catch (e) {
      return {'success': false, 'error': 'تعذر الاتصال بالسيرفر ($e)'};
    }
  }

  // --- FETCH PRODUCTS & CACHE OFFLINE ---
  static Future<List<ProductModel>> fetchProducts() async {
    try {
      final baseUrl = await getBaseUrl();
      final slug = await getTenantSlug();
      final url = Uri.parse('$baseUrl/api/v1/products/?tenant_slug=$slug');
      final response = await http.get(url).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data['products'] is List) {
          final products = (data['products'] as List)
              .map((p) => ProductModel.fromJson(p))
              .toList();
          await OfflineDbService.instance.saveProducts(products);
          return products;
        }
      }
    } catch (_) {}
    return await OfflineDbService.instance.getOfflineProducts();
  }

  // --- FETCH CUSTOMERS & CACHE OFFLINE ---
  static Future<List<CustomerModel>> fetchCustomers() async {
    try {
      final baseUrl = await getBaseUrl();
      final slug = await getTenantSlug();
      final url = Uri.parse('$baseUrl/api/v1/customers/?tenant_slug=$slug');
      final response = await http.get(url).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data['customers'] is List) {
          final customers = (data['customers'] as List)
              .map((c) => CustomerModel.fromJson(c))
              .toList();
          await OfflineDbService.instance.saveCustomers(customers);
          return customers;
        }
      }
    } catch (_) {}
    return await OfflineDbService.instance.getOfflineCustomers();
  }

  // --- SYNC PENDING INVOICES TO CLOUD ---
  static Future<int> syncPendingInvoices() async {
    final unsynced = await OfflineDbService.instance.getUnsyncedInvoices();
    if (unsynced.isEmpty) return 0;

    try {
      final baseUrl = await getBaseUrl();
      final slug = await getTenantSlug();
      final url = Uri.parse('$baseUrl/api/v1/invoices/sync/');

      final payload = {
        'tenant_slug': slug,
        'invoices': unsynced.map((inv) => {
          'client_id': inv.clientId,
          'payment_method': inv.paymentMethod,
          'customer_id': inv.customerId,
          'items': inv.items.map((i) => {
            'product_id': i.productId,
            'quantity': i.quantity,
            'unit_price': i.unitPrice,
          }).toList(),
        }).toList(),
      };

      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data['success'] == true && data['synced'] is List) {
          final syncedList = data['synced'] as List;
          final syncedClientIds = syncedList
              .map((s) => s is Map ? s['client_id']?.toString() : null)
              .whereType<String>()
              .toList();

          await OfflineDbService.instance.markInvoicesSynced(syncedClientIds);
          return syncedClientIds.length;
        }
      }
    } catch (_) {}
    return 0;
  }

  // --- PERFORM FULL 2-WAY SYNC ---
  static Future<Map<String, dynamic>> performFullSync() async {
    int pushedInvoices = 0;
    int productsCount = 0;
    int customersCount = 0;
    String? syncError;

    try {
      // 1. Push pending offline invoices first
      pushedInvoices = await syncPendingInvoices();

      // 2. Fetch fresh catalog and customers from cloud
      final freshProducts = await fetchProducts();
      productsCount = freshProducts.length;

      final freshCustomers = await fetchCustomers();
      customersCount = freshCustomers.length;

      return {
        'success': true,
        'pushed_invoices': pushedInvoices,
        'products_count': productsCount,
        'customers_count': customersCount,
      };
    } catch (e) {
      syncError = e.toString();
      return {
        'success': false,
        'error': syncError,
        'pushed_invoices': pushedInvoices,
      };
    }
  }

  // --- GET DASHBOARD STATS (Cloud with Local Fallback) ---
  static Future<Map<String, dynamic>> getDashboardStats() async {
    try {
      final baseUrl = await getBaseUrl();
      final slug = await getTenantSlug();
      final url = Uri.parse('$baseUrl/api/v1/dashboard/?tenant_slug=$slug');
      final response = await http.get(url).timeout(const Duration(seconds: 7));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        if (data['success'] == true) {
          return {
            'is_cloud': true,
            'today_sales': (data['today_sales'] ?? 0.0).toDouble(),
            'today_orders_count': data['today_orders_count'] ?? 0,
            'low_stock_count': data['low_stock_count'] ?? 0,
            'total_products': data['total_products'] ?? 0,
          };
        }
      }
    } catch (_) {}

    // Fallback to local SQLite calculated stats
    final local = await OfflineDbService.instance.calculateLocalStats();
    return {
      'is_cloud': false,
      ...local,
    };
  }
}
