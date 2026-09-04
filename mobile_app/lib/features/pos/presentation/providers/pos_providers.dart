import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:decimal/decimal.dart';
import 'package:mahel_pos_mobile/features/pos/domain/pos_models.dart';
import 'package:mahel_pos_mobile/features/pos/data/pos_repository.dart';
import 'package:mahel_pos_mobile/core/database/database_service.dart';
import 'package:mahel_pos_mobile/features/auth/presentation/providers/auth_providers.dart';

final posRepositoryProvider = Provider<PosRepository>((ref) {
  return PosRepository(ref.watch(databaseServiceProvider));
});

final cartProvider = StateNotifierProvider<CartNotifier, List<CartItem>>((ref) {
  return CartNotifier();
});

class CartNotifier extends StateNotifier<List<CartItem>> {
  CartNotifier() : super([]);

  void addItem(CartItem item) {
    final existingIndex = state.indexWhere((i) => i.productId == item.productId);
    if (existingIndex >= 0) {
      final updated = [...state];
      updated[existingIndex] = CartItem(
        productId: item.productId,
        name: item.name,
        price: item.price,
        quantity: updated[existingIndex].quantity + item.quantity,
        customerId: item.customerId,
      );
      state = updated;
    } else {
      state = [...state, item];
    }
  }

  void increaseQuantity(int productId) {
    state = state.map((item) {
      if (item.productId == productId) {
        return CartItem(
          productId: item.productId,
          name: item.name,
          price: item.price,
          quantity: item.quantity + 1,
          customerId: item.customerId,
        );
      }
      return item;
    }).toList();
  }

  void decreaseQuantity(int productId) {
    final item = state.firstWhere((i) => i.productId == productId);
    if (item.quantity <= 1) {
      removeItem(productId);
    } else {
      state = state.map((i) {
        if (i.productId == productId) {
          return CartItem(
            productId: i.productId,
            name: i.name,
            price: i.price,
            quantity: i.quantity - 1,
            customerId: i.customerId,
          );
        }
        return i;
      }).toList();
    }
  }

  void removeItem(int productId) {
    state = state.where((i) => i.productId != productId).toList();
  }

  void clear() {
    state = [];
  }

  Decimal get total => state.fold(Decimal.zero, (sum, item) => sum + item.totalPrice);
}

final paymentMethodProvider = StateProvider<PaymentMethod>((ref) => const PaymentMethod.cash());
final selectedCustomerProvider = StateProvider<int?>((ref) => null);
final searchQueryProvider = StateProvider<String>((ref) => '');
final isOnlineProvider = StateProvider<bool>((ref) => true);
