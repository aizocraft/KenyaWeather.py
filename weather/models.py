from django.db import models

class Location(models.Model):
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    lat = models.FloatField()
    lon = models.FloatField()
    
    def __str__(self):
        return f"{self.city}, {self.country}"