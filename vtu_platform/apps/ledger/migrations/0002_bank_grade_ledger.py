from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallet',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.DeleteModel(
            name='LedgerEntry',
        ),
        migrations.CreateModel(
            name='LedgerEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(max_length=64, unique=True)),
                ('tx_type', models.CharField(choices=[('FUNDING', 'Funding'), ('AIRTIME', 'Airtime'), ('DATA', 'Data'), ('BILL', 'Bill'), ('REFERRAL_BONUS', 'Referral Bonus'), ('REVERSAL', 'Reversal')], max_length=20)),
                ('direction', models.CharField(choices=[('CREDIT', 'Credit'), ('DEBIT', 'Debit')], max_length=6)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('REVERSED', 'Reversed')], default='PENDING', max_length=10)),
                ('meta', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ledger_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
    ]
