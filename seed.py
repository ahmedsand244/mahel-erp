import os
import sys
import django
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')
django.setup()

from seed_and_test_e2e import run_e2e_scenarios

if __name__ == '__main__':
    run_e2e_scenarios()
