# apps/locations/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Country Name"))
    code = models.CharField(max_length=2, unique=True, verbose_name=_("Country Code (ISO 3166-1 alpha-2)"))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")
        ordering = ['name']

    def __str__(self):
        return self.name

class State(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("State/Province/Region Name"))
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("State / Province")
        verbose_name_plural = _("States / Provinces")
        ordering = ['name']
        unique_together = ('name', 'country') # A state name should be unique within its country

    def __str__(self):
        return f"{self.name}, {self.country.name}"