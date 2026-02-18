from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SiteSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_name', models.CharField(default='VTU Platform', max_length=100)),
                ('support_email', models.EmailField(max_length=254)),
                ('support_phone', models.CharField(blank=True, max_length=20)),
                ('maintenance_mode', models.BooleanField(default=False)),
            ],
        ),
    ]
