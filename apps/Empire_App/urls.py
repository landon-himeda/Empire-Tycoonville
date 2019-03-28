from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^process_register$', views.process_register),
    url(r'^process_login$', views.process_login),
    url(r'^dashboard$', views.dashboard),
    url(r'^market$', views.market),
    url(r'^business/(?P<business_id>\d+)$', views.business),
    url(r'^process_buy_business/(?P<business_type_id>\d+)$', views.process_buy_business),
    url(r'^process_sell_business/(?P<business_id>\d+)$', views.process_sell_business),
    url(r'^process_buy_addon/(?P<business_id>\d+)/(?P<addon_type_id>\d+)$', views.process_buy_addon),
    url(r'^buy_business/(?P<business_type_id>\d+)$', views.buy_business),
    url(r'^process_log_out$', views.process_log_out),
]
