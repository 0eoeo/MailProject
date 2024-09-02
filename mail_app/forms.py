from django import forms
from .models import MailAddresses
from django.contrib.auth.hashers import make_password, check_password


class LoginForm(forms.ModelForm):
    address = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={"placeholder": "Введите вашу почту"}),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"placeholder": "Введите пароль"}),
    )

    class Meta:
        model = MailAddresses
        fields = ["address", "password"]
