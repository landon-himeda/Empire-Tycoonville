from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^process_register$', views.process_register),
    url(r'^process_login$', views.process_login),
    url(r'^dashboard$', views.dashboard),
    url(r'^business$', views.business),
    url(r'^process_sell_business$', views.process_sell_business),
    url(r'^process_log_out$', views.process_log_out),
    url(r'^process_buy_business$', views.process_buy_business),
    url(r'^process_buy_addon$', views.process_buy_addon),
    ]