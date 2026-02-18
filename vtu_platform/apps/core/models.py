from django.db import models


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100, default='VTU Platform')
    support_email = models.EmailField()
    support_phone = models.CharField(max_length=20, blank=True)
    maintenance_mode = models.BooleanField(default=False)

    def __str__(self):
        return self.site_name
