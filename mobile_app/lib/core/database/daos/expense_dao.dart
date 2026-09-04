import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class ExpenseDao {
  final AppDatabase db;
  ExpenseDao(this.db);

  Future<List<Expense>> getAllExpenses({int? tenantId, DateTime? startDate, DateTime? endDate}) {
    final query = select(db.expenses)..where((e) => e.deletedAt.isNull());
    if (tenantId != null) {
      query.where((e) => e.tenantId.equals(tenantId));
    }
    if (startDate != null) {
      query.where((e) => e.createdAt.isBiggerOrEqualValue(startDate));
    }
    if (endDate != null) {
      query.where((e) => e.createdAt.isSmallerOrEqualValue(endDate));
    }
    return query.orderBy([OrderingTerm.desc(db.expenses.createdAt)]).get();
  }

  Future<List<Expense>> getExpensesByCategory(String category, {int? tenantId}) {
    final query = select(db.expenses)
      ..where((e) => e.deletedAt.isNull() & e.category.equals(category));
    if (tenantId != null) {
      query.where((e) => e.tenantId.equals(tenantId));
    }
    return query.get();
  }

  Future<int> insertExpense(ExpensesCompanion expense) => into(db.expenses).insert(expense);

  Future<bool> updateExpense(ExpensesCompanion expense) => update(db.expenses).replace(expense);

  Future<int> deleteExpense(int id) =>
      (delete(db.expenses)..where((e) => e.id.equals(id))).go();

  Future<double> getTotalExpenses({int? tenantId, DateTime? startDate, DateTime? endDate}) async {
    final expenses = await getAllExpenses(tenantId: tenantId, startDate: startDate, endDate: endDate);
    return expenses.fold(0.0, (sum, e) => sum + e.amount);
  }

  Future<Map<String, double>> getExpensesByCategorySummary({int? tenantId, DateTime? startDate, DateTime? endDate}) async {
    final expenses = await getAllExpenses(tenantId: tenantId, startDate: startDate, endDate: endDate);
    final Map<String, double> summary = {};
    for (final e in expenses) {
      summary[e.category] = (summary[e.category] ?? 0) + e.amount;
    }
    return summary;
  }
}
