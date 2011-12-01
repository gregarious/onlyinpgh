from django.db import models

class Tag(models.Model):
    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=50)
    
    def __unicode__(self):
        return self.name