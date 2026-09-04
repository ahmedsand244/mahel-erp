import 'package:drift/drift.dart';
import 'package:mahel_pos_mobile/core/database/app_database.dart';

class SyncQueueDao extends DatabaseAccessor<AppDatabase> {
  SyncQueueDao(super.db);
  AppDatabase get db => attachedDatabase;

  Future<List<SyncQueue>> getPendingOperations() =>
      (select(db.syncQueue)
            ..where((s) => s.status.equals('pending'))
            ..orderBy([OrderingTerm.asc(db.syncQueue.createdAt)]))
          .get();

  Future<List<SyncQueue>> getFailedOperations({int maxRetries = 3}) =>
      (select(db.syncQueue)
            ..where((s) => s.status.equals('failed') & s.retryCount.isSmallerThanValue(maxRetries))
            ..orderBy([OrderingTerm.asc(db.syncQueue.createdAt)]))
          .get();

  Future<int> enqueueOperation(SyncQueueCompanion operation) => into(db.syncQueue).insert(operation);

  Future<int> markProcessing(int id) {
    return (update(db.syncQueue)
          ..where((s) => s.id.equals(id)))
        .write(SyncQueueCompanion(
          status: const Value('processing'),
          updatedAt: Value(DateTime.now()),
        ));
  }

  Future<int> markCompleted(int id) {
    return (update(db.syncQueue)
          ..where((s) => s.id.equals(id)))
        .write(SyncQueueCompanion(
          status: const Value('completed'),
          processedAt: Value(DateTime.now()),
          updatedAt: Value(DateTime.now()),
        ));
  }

  Future<int> markFailed(int id, String errorMessage) {
    return (update(db.syncQueue)
          ..where((s) => s.id.equals(id)))
        .write(SyncQueueCompanion(
          status: const Value('failed'),
          errorMessage: Value(errorMessage),
          retryCount: Value(0),
          updatedAt: Value(DateTime.now()),
        ));
  }

  Future<int> incrementRetry(int id) {
    return (update(db.syncQueue)
          ..where((s) => s.id.equals(id)))
        .write(SyncQueueCompanion(
          retryCount: Value(0),
          updatedAt: Value(DateTime.now()),
        ));
  }

  Future<int> clearCompleted() =>
      (delete(db.syncQueue)..where((s) => s.status.equals('completed'))).go();
}

