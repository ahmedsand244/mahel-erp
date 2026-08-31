import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/product.dart';
import '../models/invoice.dart';

class ApiService {
  final String baseUrl;

  ApiService({this.baseUrl = "https://webservises.pythonanywhere.com"});

  Future<Map<String, dynamic>> login({
    required String username,
    required String password,
    String? tenantSlug,
  }) async {
    final url = Uri.parse("$baseUrl/api/v1/login/");
    try {
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "username": username,
          "password": password,
          "tenant_slug": tenantSlug,
        }),
      );

      final data = jsonDecode(response.body);
      return data;
    } catch (e) {
      return {"success": false, "error": "تعذر الاتصال بالسيرفر: $e"};
    }
  }

  Future<List<ProductModel>> fetchProducts(String tenantSlug) async {
    final url = Uri.parse("$baseUrl/api/v1/products/?tenant_slug=$tenantSlug");
    try {
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          final List list = data['products'] ?? [];
          return list.map((json) => ProductModel.fromJson(json)).toList();
        }
      }
    } catch (e) {
      print("Error fetching products: $e");
    }
    return [];
  }

  Future<Map<String, dynamic>> syncInvoices(
    String tenantSlug,
    List<OfflineInvoice> invoices,
  ) async {
    final url = Uri.parse("$baseUrl/api/v1/invoices/sync/");
    try {
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "tenant_slug": tenantSlug,
          "invoices": invoices.map((inv) => inv.toJson()).toList(),
        }),
      );

      return jsonDecode(response.body);
    } catch (e) {
      return {"success": false, "error": "تعذر رفع الفواتير: $e"};
    }
  }
}
