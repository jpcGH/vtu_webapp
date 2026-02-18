from django.contrib import admin
from .models import LedgerEntry, Wallet

admin.site.register(Wallet)
admin.site.register(LedgerEntry)
