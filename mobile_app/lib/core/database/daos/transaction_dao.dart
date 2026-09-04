import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class TransactionDao extends DatabaseAccessor<AppDatabase> {
  TransactionDao(super.db);
  AppDatabase get db => attachedDatabase;

  Future<List<Transaction>> getAllTransactions({int? tenantId, int? customerId, int? supplierId, DateTime? startDate, DateTime? endDate}) {
    final query = select(db.transactions)..where((t) => t.deletedAt.isNull());
    if (tenantId != null) {
      query.where((t) => t.tenantId.equals(tenantId));
    }
    if (customerId != null) {
      query.where((t) => t.customerId.equals(customerId));
    }
    if (supplierId != null) {
      query.where((t) => t.supplierId.equals(supplierId));
    }
    if (startDate != null) {
      query.where((t) => t.createdAt.isBiggerOrEqualValue(startDate));
    }
    if (endDate != null) {
      query.where((t) => t.createdAt.isSmallerOrEqualValue(endDate));
    }
    query.orderBy([(t) => OrderingTerm.desc(t.createdAt)]);
    return query.get();
  }

  Future<int> insertTransaction(TransactionsCompanion transaction) => into(db.transactions).insert(transaction);

  Future<double> getCustomerPayments(int customerId, {DateTime? startDate, DateTime? endDate}) async {
    final transactions = await getAllTransactions(
      customerId: customerId,
      startDate: startDate,
      endDate: endDate,
    );
    return transactions
        .where((t) => t.transactionType == 'pay_received')
        .fold<double>(0.0, (double sum, t) => sum + t.amount);
  }

  Future<double> getSupplierPayments(int supplierId, {DateTime? startDate, DateTime? endDate}) async {
    final transactions = await getAllTransactions(
      supplierId: supplierId,
      startDate: startDate,
      endDate: endDate,
    );
    return transactions
        .where((t) => t.transactionType == 'pay_sent')
        .fold<double>(0.0, (double sum, t) => sum + t.amount);
  }

  Future<Map<String, double>> getTransactionSummary({
    int? tenantId,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final transactions = await getAllTransactions(
      tenantId: tenantId,
      startDate: startDate,
      endDate: endDate,
    );

    double saleCredit = 0;
    double purchaseCredit = 0;
    double payReceived = 0;
    double paySent = 0;

    for (final t in transactions) {
      switch (t.transactionType) {
        case 'sale_credit':
          saleCredit += t.amount;
          break;
        case 'purchase_credit':
          purchaseCredit += t.amount;
          break;
        case 'pay_received':
          payReceived += t.amount;
          break;
        case 'pay_sent':
          paySent += t.amount;
          break;
      }
    }

    return {
      'saleCredit': saleCredit,
      'purchaseCredit': purchaseCredit,
      'payReceived': payReceived,
      'paySent': paySent,
    };
  }
}

