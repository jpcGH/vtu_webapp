from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards_fill_fields(apps, schema_editor):
    LedgerEntry = apps.get_model('ledger', 'LedgerEntry')
    for entry in LedgerEntry.objects.select_related('wallet__user').all():
        wallet = getattr(entry, 'wallet', None)
        if wallet is None:
            continue
        entry.user_id = wallet.user_id
        entry.direction = 'CREDIT' if entry.entry_type == 'CREDIT' else 'DEBIT'
        entry.tx_type = 'FUNDING' if entry.entry_type == 'CREDIT' else 'BILL'
        entry.status = 'SUCCESS'
        entry.save(update_fields=['user', 'direction', 'tx_type', 'status'])


def backwards_fill_fields(apps, schema_editor):
    LedgerEntry = apps.get_model('ledger', 'LedgerEntry')
    Wallet = apps.get_model('ledger', 'Wallet')

    for entry in LedgerEntry.objects.select_related('user').all():
        wallet, _ = Wallet.objects.get_or_create(user_id=entry.user_id, defaults={'balance': Decimal('0.00')})
        entry.wallet_id = wallet.id
        entry.entry_type = 'CREDIT' if entry.direction == 'CREDIT' else 'DEBIT'
        entry.narration = 'Backfilled narration'
        entry.save(update_fields=['wallet', 'entry_type', 'narration'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ledger', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallet',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.RemoveField(
            model_name='wallet',
            name='currency',
        ),
        migrations.AddField(
            model_name='ledgerentry',
            name='direction',
            field=models.CharField(choices=[('CREDIT', 'Credit'), ('DEBIT', 'Debit')], default='CREDIT', max_length=6),
        ),
        migrations.AddField(
            model_name='ledgerentry',
            name='status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('REVERSED', 'Reversed')], default='PENDING', max_length=8),
        ),
        migrations.AddField(
            model_name='ledgerentry',
            name='tx_type',
            field=models.CharField(choices=[('FUNDING', 'Funding'), ('AIRTIME', 'Airtime'), ('DATA', 'Data'), ('BILL', 'Bill'), ('REFERRAL_BONUS', 'Referral Bonus'), ('REVERSAL', 'Reversal')], default='FUNDING', max_length=20),
        ),
        migrations.AddField(
            model_name='ledgerentry',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ledger_entries', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RenameField(
            model_name='ledgerentry',
            old_name='metadata',
            new_name='meta',
        ),
        migrations.RunPython(forwards_fill_fields, backwards_fill_fields),
        migrations.AlterField(
            model_name='ledgerentry',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ledger_entries', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ledgerentry',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
        migrations.RemoveField(
            model_name='ledgerentry',
            name='wallet',
        ),
        migrations.RemoveField(
            model_name='ledgerentry',
            name='entry_type',
        ),
        migrations.RemoveField(
            model_name='ledgerentry',
            name='narration',
        ),
    ]
