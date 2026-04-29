from django.apps import AppConfig, apps as django_apps
from django.conf import settings
from django.db import connections


def rename_demo_tables_for_using(using="default"):
    """Best-effort rename of already-created DB tables to demo-prefixed names.

    This can be invoked manually in tests after enabling DEMO_MODE so that
    migrations (which ran without demo settings) can be adjusted at runtime.
    """
    try:
        if not getattr(settings, "DEMO_MODE", False) or not getattr(settings, "DEMO_DB_PREFIX", None):
            return
        prefix = settings.DEMO_DB_PREFIX
        if not prefix.endswith("_"):
            prefix = prefix + "_"
        conn = connections[using]
        existing = set(conn.introspection.table_names())
        models = list(django_apps.get_app_config("account").get_models())
        with conn.schema_editor() as editor:
            for model in models:
                mt = model._meta
                if not getattr(mt, "managed", True):
                    continue
                desired = prefix + mt.db_table if not mt.db_table.startswith(prefix) else mt.db_table
                app_label = mt.app_label
                model_name = mt.model_name
                original = f"{app_label}_{model_name}"
                if desired in existing:
                    continue
                if original in existing and desired not in existing:
                    try:
                        editor.alter_db_table(model, original, desired)
                    except Exception:
                        continue
    except Exception:
        pass


class AccountConfig(AppConfig):
    name = "account"

    def ready(self):
        # If demo DB prefix is configured, apply it to all models' db_table
        # and attempt to rename physical tables after migrations run so the
        # test database and migrations reflect the prefix.
        try:
            # If demo DB prefix is configured at startup, update model db_table metadata
            if getattr(settings, "DEMO_MODE", False) and getattr(settings, "DEMO_DB_PREFIX", None):
                prefix = settings.DEMO_DB_PREFIX
                if not prefix.endswith("_"):
                    prefix = prefix + "_"

                for model in django_apps.get_models():
                    try:
                        mt = model._meta
                        if not getattr(mt, "managed", True):
                            continue
                        if not mt.db_table.startswith(prefix):
                            mt.db_table = prefix + mt.db_table
                    except Exception:
                        continue
        except Exception:
            # Be robust to settings not being fully configured in some contexts
            pass


# Unconditional post_migrate handler: at the end of migrations (including test DB creation)
# this will run and, if demo mode + prefix are enabled at that time, rename existing
# physical tables to their prefixed names. Connecting unconditionally ensures the
# handler runs even if DEMO_MODE is toggled via environment prior to migrations.
from django.db.models.signals import post_migrate


def _post_migrate_ensure_demo_prefix(sender, app_config, using, **kwargs):
    try:
        if not getattr(settings, "DEMO_MODE", False) or not getattr(settings, "DEMO_DB_PREFIX", None):
            return
        prefix = settings.DEMO_DB_PREFIX
        if not prefix.endswith("_"):
            prefix = prefix + "_"
        conn = connections[using]
        existing = set(conn.introspection.table_names())
        models = list(app_config.get_models())
        if not models:
            return
        with conn.schema_editor() as editor:
            for model in models:
                mt = model._meta
                if not getattr(mt, "managed", True):
                    continue
                app_label = mt.app_label
                model_name = mt.model_name
                original = f"{app_label}_{model_name}"
                desired = prefix + original
                if desired in existing:
                    continue
                if original in existing and desired not in existing:
                    try:
                        editor.alter_db_table(model, original, desired)
                    except Exception:
                        continue
    except Exception:
        pass


post_migrate.connect(_post_migrate_ensure_demo_prefix, dispatch_uid="account_demo_prefix_ensure")
