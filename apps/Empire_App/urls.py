from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^register$', views.register),
    url(r'^login$', views.login),
    url(r'^dashboard$', views.dashboard),
    url(r'^business$', views.business),
    url(r'^sell_business$', views.sell_business),
    url(r'^log_out$', views.log_out),
    url(r'^buy_business$', views.buy_business),
    url(r'^buy_addon$', views.buy_addon),
    ]