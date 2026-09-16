"""
Database Speed & Performance Optimizations (Turbo Engine)
Configures high-speed SQLite PRAGMAs (WAL mode, RAM page caching, 256MB MMAP)
and connection pooling.
"""
from django.db.backends.signals import connection_created
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(connection_created)
def configure_db_performance(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        try:
            with connection.cursor() as cursor:
                # 1. WAL Mode: Write-Ahead Logging allows concurrent reads while writing without lock contention
                cursor.execute("PRAGMA journal_mode = WAL;")
                # 2. Synchronous NORMAL: Faster sync while maintaining full crash resilience in WAL mode
                cursor.execute("PRAGMA synchronous = NORMAL;")
                # 3. 64MB In-Memory Page Cache
                cursor.execute("PRAGMA cache_size = -64000;")
                # 4. In-Memory Temporary Storage for sorting & temporary tables
                cursor.execute("PRAGMA temp_store = MEMORY;")
                # 5. 256MB Memory-Mapped I/O for instant reads from OS cache
                cursor.execute("PRAGMA mmap_size = 268435456;")
                # 6. 5-second busy timeout to prevent 'database is locked' on multi-user access
                cursor.execute("PRAGMA busy_timeout = 5000;")
        except Exception as e:
            logger.debug(f"Failed to set SQLite performance pragmas: {e}")
