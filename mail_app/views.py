from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password, check_password
from .models import MailAddresses
from .forms import LoginForm


def messages(request):
    user_id = request.session.get("user_id")
    address = request.session.get("address")
    password = request.session.get("password")

    if not address or not password:
        # Если email и пароль отсутствуют в сессии, перенаправляем на страницу регистрации
        return redirect("login")

    # Если email и пароль есть, отображаем страницу списка сообщений
    return render(
        request,
        "mail_app/messages_list.html",
        {"address": address, "password": password, "user_id": user_id},
    )


def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data["address"]
            password = form.cleaned_data["password"]
            request.session["address"] = address
            request.session["password"] = password

            hashed_password = make_password(password)
            # Проверка на уникальность комбинации адреса и пароля
            if MailAddresses.objects.filter(address=address).exists():
                for entry in MailAddresses.objects.filter(address=address):
                    if check_password(password, entry.password):
                        request.session["user_id"] = entry.id
                        return redirect("/messages")
            mail_address = MailAddresses(address=address, password=hashed_password)
            mail_address.save()
            request.session["user_id"] = mail_address.id
            return redirect("/messages")
    else:
        form = LoginForm()

    return render(request, "mail_app/login.html", {"form": form})


def logout(request):
    # Очистка данных сессии
    request.session.flush()
    # Перенаправление на страницу регистрации
    return redirect("login")
