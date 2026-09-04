import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:mahel_pos_mobile/features/auth/presentation/providers/auth_providers.dart';

class TenantSelectionScreen extends ConsumerWidget {
  const TenantSelectionScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: Text('Ø§Ø®ØªØ± Ø§Ù„Ø´Ø±ÙƒØ©', style: GoogleFonts.cairo()),
        centerTitle: true,
        automaticallyImplyLeading: false,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.business_rounded,
                size: 40,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Ù…Ø±Ø­Ø¨Ø§Ù‹ ${authState is Authenticated ? authState.username : 'Ø¨ÙƒÙ…'}',
              style: GoogleFonts.cairo(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Ø§Ø®ØªØ± Ø§Ù„Ø´Ø±ÙƒØ© Ù„Ù„Ø¯Ø®ÙˆÙ„',
              style: GoogleFonts.cairo(fontSize: 14, color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 32),
            _buildTenantCard(context, 'mahel', 'Ø´Ø±ÙƒØ© Ø§Ù„Ù†Ù…Ø§Ø¡', Icons.storefront_rounded),
            const SizedBox(height: 16),
            _buildTenantCard(context, 'demo', 'Ø´Ø±ÙƒØ© ØªØ¬Ø±ÙŠØ¨ÙŠØ©', Icons.science_rounded),
            const SizedBox(height: 32),
            TextButton.icon(
              onPressed: () => ref.read(authStateProvider.notifier).logout(),
              icon: const Icon(Icons.logout),
              label: Text('ØªØ³Ø¬ÙŠÙ„ Ø®Ø±ÙˆØ¬', style: GoogleFonts.cairo()),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTenantCard(BuildContext context, String slug, String name, IconData icon) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 32),
      child: InkWell(
        onTap: () {
          // Navigate to main app with selected tenant
          // This would typically set the tenant and navigate to dashboard
        },
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primary.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: Theme.of(context).colorScheme.primary, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: GoogleFonts.cairo(fontSize: 16, fontWeight: FontWeight.bold)),
                    Text('Slug: $slug', style: GoogleFonts.cairo(fontSize: 12, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 16),
            ],
          ),
        ),
      ),
    );
  }
}
