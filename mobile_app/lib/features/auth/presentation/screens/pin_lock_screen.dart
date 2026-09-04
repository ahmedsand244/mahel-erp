import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mahel_pos_mobile/features/auth/presentation/providers/auth_providers.dart';
import 'package:mahel_pos_mobile/core/storage/secure_storage_service.dart';

class PinLockScreen extends ConsumerStatefulWidget {
  const PinLockScreen({super.key});

  @override
  ConsumerState<PinLockScreen> createState() => _PinLockScreenState();
}

class _PinLockScreenState extends ConsumerState<PinLockScreen> {
  final List<String> _enteredPin = [];
  String _errorMessage = '';

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      body: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 320),
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary.withOpacity(0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.lock_rounded,
                  size: 40,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Ø¥Ø¯Ø®Ø§Ù„ Ø±Ù…Ø² PIN',
                style: GoogleFonts.cairo(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'Ø£Ø¯Ø®Ù„ Ø±Ù…Ø² Ø§Ù„Ø¯Ø®ÙˆÙ„ Ø§Ù„Ø³Ø±ÙŠØ¹ Ù„Ù„ÙˆØµÙˆÙ„ Ù„Ù„Ù†Ø¸Ø§Ù…',
                style: GoogleFonts.cairo(fontSize: 13, color: theme.colorScheme.onSurfaceVariant),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(4, (index) {
                  final isFilled = index < _enteredPin.length;
                  return Container(
                    margin: const EdgeInsets.symmetric(horizontal: 8),
                    width: 16,
                    height: 16,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: isFilled ? theme.colorScheme.primary : theme.colorScheme.outline,
                    ),
                  );
                }),
              ),
              if (_errorMessage.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  _errorMessage,
                  style: GoogleFonts.cairo(fontSize: 12, color: theme.colorScheme.error),
                ),
              ],
              const SizedBox(height: 32),
              _buildKeypad(theme),
              const SizedBox(height: 24),
              TextButton(
                onPressed: () => _usePasswordInstead(),
                child: Text(
                  'Ø§Ø³ØªØ®Ø¯Ø§Ù… ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ± Ø¨Ø¯Ù„Ø§Ù‹ Ù…Ù† PIN',
                  style: GoogleFonts.cairo(color: theme.colorScheme.primary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildKeypad(ThemeData theme) {
    const keys = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      ['', '0', 'âŒ«'],
    ];

    return Column(
      children: keys.map((row) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: row.map((key) {
            if (key.isEmpty) {
              return const SizedBox(width: 72, height: 56);
            }
            return Padding(
              padding: const EdgeInsets.all(6),
              child: Material(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(16),
                child: InkWell(
                  onTap: () => _onKeyPressed(key),
                  borderRadius: BorderRadius.circular(16),
                  child: Container(
                    width: 72,
                    height: 56,
                    alignment: Alignment.center,
                    child: Text(
                      key,
                      style: GoogleFonts.cairo(
                        fontSize: key == 'âŒ«' ? 20 : 24,
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.onSurface,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        );
      }).toList(),
    );
  }

  void _onKeyPressed(String key) {
    if (key == 'âŒ«') {
      if (_enteredPin.isNotEmpty) {
        setState(() => _enteredPin.removeLast());
      }
    } else if (_enteredPin.length < 4) {
      setState(() {
        _enteredPin.add(key);
        _errorMessage = '';
      });
    }

    if (_enteredPin.length == 4) {
      _verifyPin();
    }
  }

  Future<void> _verifyPin() async {
    final storedPin = await SecureStorageService.getPinCode();
    if (storedPin != null && storedPin == _enteredPin.join()) {
      if (mounted) {
        // Navigate to main app
        // This would typically pop to the main scaffold
        Navigator.of(context).pop(true);
      }
    } else {
      setState(() {
        _errorMessage = 'Ø±Ù…Ø² PIN ØºÙŠØ± ØµØ­ÙŠØ­';
        _enteredPin.clear();
      });
      await Future.delayed(const Duration(seconds: 1));
      if (mounted) setState(() => _errorMessage = '');
    }
  }

  void _usePasswordInstead() {
    Navigator.of(context).pushReplacementNamed('/login');
  }
}
