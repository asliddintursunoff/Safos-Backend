from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager,PermissionsMixin

from apps.common.models import BaseModel
from apps.common.choices import USER_ROLE_CHOICES


class UserManager(BaseUserManager):
    def create_user(self,phone_number,password = None,**extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required!')
        if password is None:
            extra_fields.setdefault("role_type", "CUSTOMER")
        user = self.model(phone_number = phone_number,**extra_fields)
        if password is not None:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using = self._db)
        return user
    
    def create_superuser(self,phone_number,password = None,**extra_fields):
        extra_fields.setdefault('role_type',"ADMIN")
        extra_fields.setdefault('color_code',"#0400FF")
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        return self.create_user(phone_number,password,**extra_fields)


class User(AbstractBaseUser, BaseModel,PermissionsMixin):
    
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    
    phone_number = models.CharField(max_length=15, unique=True,null = True,blank=True)
    telegram_id = models.BigIntegerField(unique = True,null = True,blank=True)

    # Profile photo
    photo = models.ImageField(upload_to="users/", null=True, blank=True)

    role_type = models.CharField(max_length=20,choices = USER_ROLE_CHOICES,default = "CUSTOMER")
    color_code = models.CharField(max_length=7,default = "#2FFFE3")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    USERNAME_FIELD = 'phone_number'
    # REQUIRED_FIELDS = ['date_of_birth']
    
    objects = UserManager()
    def __str__(self):
        return self.phone_number if self.phone_number else str(self.telegram_id)    

class UserCurrentLocation(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='current_location')
    location = models.PointField(srid=4326)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UserLocation {self.id} - {self.user.first_name} {self.user.last_name if self.user.last_name else ''}"
    
class UserLocationHistory(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_history')
    location = models.PointField(srid=4326)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UserLocationHistory {self.id} - {self.user.first_name} {self.user.last_name if self.user.last_name else ''}"
    


    
