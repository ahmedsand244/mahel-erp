import json
import urllib.request
import urllib.error
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import Product
from ledger.models import Customer, Supplier

class Command(BaseCommand):
    help = 'سحب كافة المنتجات والعملاء من السيرفر السحابي وتحديث قاعدة البيانات المحلية (db.sqlite3)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='https://webservises.pythonanywhere.com/api/v1/sync/full/',
            help='رابط الـ API السحابي للمزامنة'
        )

    def handle(self, *args, **options):
        cloud_url = options['url']
        self.stdout.write(self.style.NOTICE(f'🌐 جاري الاتصال بالسيرفر السحابي: {cloud_url}...'))

        try:
            req = urllib.request.Request(
                cloud_url,
                headers={'User-Agent': 'AlNamaa-Desktop-CLI-Sync/1.0'}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            if not data.get('success'):
                self.stdout.write(self.style.ERROR('❌ استجاب السيرفر السحابي برسالة فشل.'))
                return

            products_data = data.get('products', [])
            customers_data = data.get('customers', [])
            suppliers_data = data.get('suppliers', [])

            self.stdout.write(f'📦 تم العثور على {len(products_data)} منتج و {len(customers_data)} عميل في السحابة.')

            created_prods = 0
            updated_prods = 0

            with transaction.atomic():
                for p in products_data:
                    sku = (p.get('sku') or '').strip()
                    name = (p.get('name') or '').strip()
                    barcode = (p.get('barcode') or '').strip()
                    if not name:
                        continue

                    prod = None
                    if sku:
                        prod = Product.objects.filter(sku=sku).first()
                    if not prod and barcode:
                        prod = Product.objects.filter(barcode=barcode).first()
                    if not prod:
                        prod = Product.objects.filter(name=name).first()

                    if prod:
                        prod.purchase_price = Decimal(str(p.get('purchase_price', 0)))
                        prod.selling_price = Decimal(str(p.get('selling_price', 0)))
                        prod.stock_quantity = int(p.get('stock_quantity', 0))
                        if barcode: prod.barcode = barcode
                        if sku: prod.sku = sku
                        if p.get('category'): prod.category = p.get('category')
                        prod.save()
                        updated_prods += 1
                    else:
                        Product.objects.create(
                            name=name,
                            sku=sku or None,
                            barcode=barcode or None,
                            category=p.get('category') or 'عام',
                            purchase_price=Decimal(str(p.get('purchase_price', 0))),
                            selling_price=Decimal(str(p.get('selling_price', 0))),
                            stock_quantity=int(p.get('stock_quantity', 0)),
                            min_stock_threshold=int(p.get('min_stock_threshold', 5))
                        )
                        created_prods += 1

                created_custs = 0
                updated_custs = 0
                for c in customers_data:
                    phone = (c.get('phone') or '').strip() or None
                    name = (c.get('name') or '').strip()
                    if not name:
                        continue
                    cust = Customer.objects.filter(phone=phone).first() if phone else None
                    if not cust:
                        cust = Customer.objects.filter(name=name).first()

                    if cust:
                        if c.get('workplace'): cust.workplace = c.get('workplace')
                        if c.get('address'): cust.address = c.get('address')
                        if 'balance' in c:
                            try: cust.balance = Decimal(str(c['balance']))
                            except: pass
                        cust.save()
                        updated_custs += 1
                    else:
                        try: init_bal = Decimal(str(c.get('balance', 0)))
                        except: init_bal = Decimal('0.00')
                        Customer.objects.create(
                            name=name,
                            phone=phone,
                            workplace=c.get('workplace', ''),
                            address=c.get('address', ''),
                            balance=init_bal,
                            notes=c.get('notes', '')
                        )
                        created_custs += 1

            self.stdout.write(self.style.SUCCESS(
                f'🎉 تمت المزامنة بنجاح!\n'
                f'   - المنتجات: {created_prods} جديدة، {updated_prods} محدثة.\n'
                f'   - العملاء: {created_custs} جدد، {updated_custs} محدثين.'
            ))

        except urllib.error.URLError as e:
            self.stdout.write(self.style.ERROR(f'❌ تعذر الاتصال بالسيرفر السحابي: {str(e.reason)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطأ غير متوقع: {str(e)}'))
