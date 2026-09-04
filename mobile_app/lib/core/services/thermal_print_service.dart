import 'dart:typed_data';
import 'package:esc_pos_bluetooth/esc_pos_bluetooth.dart';
import 'package:esc_pos_utils/esc_pos_utils.dart';

class ThermalPrintService {
  final PrinterBluetoothManager _printerManager = PrinterBluetoothManager();
  List<PrinterBluetooth> _devices = [];
  PrinterBluetooth? _connectedPrinter;

  ThermalPrintService();

  Stream<List<PrinterBluetooth>> get devicesStream => _printerManager.scanResults;

  Future<void> startScan() async {
    await _printerManager.startScan(Duration(seconds: 4));
  }

  void stopScan() {
    _printerManager.stopScan();
  }

  Future<void> connect(PrinterBluetooth device) async {
    _connectedPrinter = device;
    await _printerManager.selectPrinter(device);
  }

  Future<void> disconnect() async {
    _connectedPrinter = null;
  }

  Future<void> printReceipt({
    required String companyName,
    required String orderNumber,
    required DateTime dateTime,
    required List<ReceiptItem> items,
    required double subtotal,
    required double tax,
    required double total,
    required String paymentMethod,
    String? customerName,
    String? customerPhone,
    String? notes,
  }) async {
    if (_connectedPrinter == null) {
      throw Exception('لا توجد طابعة متصلة');
    }

    final profile = await CapabilityProfile.load();
    final generator = Generator(PaperSize.mm80, profile);

    List<int> bytes = [];

    // Header
    bytes += generator.text(
      companyName,
      styles: PosStyles(align: PosAlign.center, bold: true, height: PosTextSize.size2, width: PosTextSize.size2),
    );
    bytes += generator.text(
      'فاتورة مبيعات',
      styles: PosStyles(align: PosAlign.center, bold: true, height: PosTextSize.size2),
    );
    bytes += generator.hr();
    
    // Order info
    bytes += generator.row([
      PosColumn(text: 'رقم الفاتورة:', width: 6, styles: PosStyles(bold: true)),
      PosColumn(text: orderNumber, width: 6, styles: PosStyles(align: PosAlign.right)),
    ]);
    bytes += generator.row([
      PosColumn(text: 'التاريخ:', width: 6, styles: PosStyles(bold: true)),
      PosColumn(text: _formatDateTime(dateTime), width: 6, styles: PosStyles(align: PosAlign.right)),
    ]);
    if (customerName != null) {
      bytes += generator.row([
        PosColumn(text: 'العميل:', width: 6, styles: PosStyles(bold: true)),
        PosColumn(text: customerName, width: 6, styles: PosStyles(align: PosAlign.right)),
      ]);
    }
    if (customerPhone != null) {
      bytes += generator.row([
        PosColumn(text: 'الهاتف:', width: 6, styles: PosStyles(bold: true)),
        PosColumn(text: customerPhone, width: 6, styles: PosStyles(align: PosAlign.right)),
      ]);
    }
    bytes += generator.hr();

    // Items header
    bytes += generator.row([
      PosColumn(text: 'الصنف', width: 5, styles: PosStyles(bold: true)),
      PosColumn(text: 'الكمية', width: 2, styles: PosStyles(bold: true, align: PosAlign.center)),
      PosColumn(text: 'السعر', width: 2, styles: PosStyles(bold: true, align: PosAlign.right)),
      PosColumn(text: 'الإجمالي', width: 3, styles: PosStyles(bold: true, align: PosAlign.right)),
    ]);
    bytes += generator.hr();

    // Items
    for (final item in items) {
      bytes += generator.row([
        PosColumn(text: item.name, width: 5),
        PosColumn(text: item.quantity.toString(), width: 2, styles: PosStyles(align: PosAlign.center)),
        PosColumn(text: '${item.unitPrice.toStringAsFixed(2)}', width: 2, styles: PosStyles(align: PosAlign.right)),
        PosColumn(text: '${item.totalPrice.toStringAsFixed(2)}', width: 3, styles: PosStyles(align: PosAlign.right, bold: true)),
      ]);
    }

    bytes += generator.hr();

    // Totals
    bytes += generator.row([
      PosColumn(text: 'المجموع الفرعي:', width: 8, styles: PosStyles(bold: true, align: PosAlign.right)),
      PosColumn(text: '${subtotal.toStringAsFixed(2)} ج.م', width: 4, styles: PosStyles(align: PosAlign.right)),
    ]);
    if (tax > 0) {
      bytes += generator.row([
        PosColumn(text: 'الضريبة:', width: 8, styles: PosStyles(bold: true, align: PosAlign.right)),
        PosColumn(text: '${tax.toStringAsFixed(2)} ج.م', width: 4, styles: PosStyles(align: PosAlign.right)),
      ]);
    }
    bytes += generator.row([
      PosColumn(text: 'الإجمالي:', width: 8, styles: PosStyles(bold: true, align: PosAlign.right, height: PosTextSize.size2, width: PosTextSize.size2)),
      PosColumn(text: '${total.toStringAsFixed(2)} ج.م', width: 4, styles: PosStyles(align: PosAlign.right, bold: true, height: PosTextSize.size2)),
    ]);

    bytes += generator.hr();

    // Payment method
    bytes += generator.row([
      PosColumn(text: 'طريقة الدفع:', width: 8, styles: PosStyles(bold: true)),
      PosColumn(text: _translatePaymentMethod(paymentMethod), width: 4, styles: PosStyles(align: PosAlign.right)),
    ]);

    if (notes != null && notes.isNotEmpty) {
      bytes += generator.hr();
      bytes += generator.text(
        'ملاحظات: $notes',
        styles: PosStyles(align: PosAlign.center),
      );
    }

    bytes += generator.hr();
    bytes += generator.text(
      'شكراً لتعاملكم معنا',
      styles: PosStyles(align: PosAlign.center, bold: true),
    );
    bytes += generator.text(
      'النماء ERP & POS',
      styles: PosStyles(align: PosAlign.center),
    );

    // Cut paper
    bytes += generator.cut();

    // Print
    await _printBytes(bytes);
  }

  Future<void> _printBytes(List<int> bytes) async {
    if (_connectedPrinter == null) return;
    
    final ticket = await _connectedPrinter!.printTicket(bytes);
    if (ticket != null) {
      // Print successful
    } else {
      throw Exception('فشلت عملية الطباعة');
    }
  }

  String _formatDateTime(DateTime dt) {
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
           '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }

  String _translatePaymentMethod(String method) {
    switch (method) {
      case 'cash':
        return 'نقداً';
      case 'visa':
        return 'بطاقة / شبكة';
      case 'deferred':
        return 'آجل / شكك';
      default:
        return method;
    }
  }

  void dispose() {
    _printerManager.stopScan();
  }
}

class ReceiptItem {
  final String name;
  final int quantity;
  final double unitPrice;

  ReceiptItem({
    required this.name,
    required this.quantity,
    required this.unitPrice,
  });

  double get totalPrice => quantity * unitPrice;
}