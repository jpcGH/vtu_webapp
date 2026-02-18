from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ServiceProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('base_url', models.URLField(blank=True)),
                ('api_key', models.CharField(blank=True, max_length=150)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_type', models.CharField(choices=[('airtime', 'Airtime'), ('data', 'Data'), ('bill', 'Bill Payment')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('destination', models.CharField(max_length=50)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('provider_reference', models.CharField(blank=True, max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='vtu.serviceprovider')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vtu_orders', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
