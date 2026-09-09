from django.core.management.base import BaseCommand
from inventory.models import Product, generate_unique_sku, generate_unique_barcode

class Command(BaseCommand):
    help = 'توليد باركود ورمز SKU تلقائياً لجميع المنتجات القديمة التي ينقصها ذلك'

    def handle(self, *args, **options):
        products = Product.all_objects.all()
        updated_sku_count = 0
        updated_barcode_count = 0

        for p in products:
            changed = False
            if not p.sku or str(p.sku).strip() in ['', 'None', '-']:
                p.sku = generate_unique_sku(p.tenant)
                changed = True
                updated_sku_count += 1

            if not p.barcode or str(p.barcode).strip() in ['', 'None', '-']:
                p.barcode = generate_unique_barcode()
                changed = True
                updated_barcode_count += 1

            if changed:
                p.save()

        self.stdout.write(
            f"Done: Updated {updated_sku_count} SKUs and {updated_barcode_count} Barcodes successfully!"
        )
