from django.db import models

class BaseModel(models.Model):
    STATUS = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    ]

    status = models.CharField(max_length=10, choices=STATUS, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

# ---------------------------
# Main Tables
# ---------------------------

# catego
class Category(BaseModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# zona
class Zone(BaseModel):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

#dispositivo
class Device(BaseModel):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    max_consumption = models.FloatField()  # Cambiado a FloatField para coincidir con Measurement
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='devices', null=True, blank=True)

    def __str__(self):
        return self.name

# Mediciones
class Measurement(BaseModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    value = models.FloatField()  # consumption value
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.timestamp}"

class Alert(BaseModel):
    ALERT_TYPES = [
        ("HIGH_CONSUMPTION", "High Consumption"),
        ("DEVICE_FAILURE", "Device Failure"),
        ("MAINTENANCE", "Maintenance Required"),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.device.name} - {self.alert_type}"

class Organization(BaseModel):
    name = models.CharField(max_length=100, unique=True)  # Añadido unique=True para evitar nombres duplicados
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=128)  # Para almacenar contraseñas hasheadas

    def __str__(self):
        return self.name