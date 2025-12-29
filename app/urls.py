from django.urls import path,include
from . import views

urlpatterns = [
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manager-dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('cashier-dashboard/', views.cashier_dashboard, name='cashier_dashboard'),
    path('add-user/', views.add_user, name='add_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('add_product/',views.add_product,name='add_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('filter-products/', views.filter_products, name='filter_products'),
    path('manager/product/<int:product_id>/', views.view_product_details, name='view_product_details'),
    path('manager/update-stock/<int:product_id>/', views.update_stock, name='update_stock'),
    path("product-lookup/",views.product_lookup, name="product_lookup"),
    path("add-to-cart/", views.add_to_cart, name="add_to_cart"),
    path("remove-from-cart/", views.remove_from_cart, name="remove_from_cart"),
    path("update-qty/", views.update_quantity, name="update_quantity"),
    path("generate-invoice/", views.generate_invoice, name="generate_invoice"),
    path('create-cart/', views.create_new_cart, name='create_new_cart'),
    path('switch-cart/<int:cart_id>/', views.switch_cart, name='switch_cart'),
    path("remove-cart/<int:cart_id>/", views.remove_cart, name="remove_cart"),
    path("checkout/", views.checkout_page, name="checkout"),
    path('customer-lookup/', views.customer_lookup, name='customer_lookup'),
    path("delete-customer/<int:customer_id>/", views.delete_customer, name="delete_customer"),
    path('sales-report/', views.sales_report, name='sales_report'),
    path("api/dashboard/", views.dashboard_data),
    path("api/products/", views.products_data),
    path("api/category-revenue/", views.api_category_revenue),
    path("api/cashier-performance/", views.api_cashier_performance),
    path("api/top-products/", views.api_top_products),
    path("api/invoices/", views.invoices_data),
    path("api/report/profit/", views.api_profit_report),
    path("api/report/margin/", views.api_margin_report), 
    path("api/report/sales/", views.api_sales_report),
    path("api/report/stock/", views.api_stock_report),
    path("api/report/manufacturer/",views.api_manufacturer_report),
    path('start-payment/', views.start_payment, name='start_payment'),
    path('upload-products/', views.upload_products, name='upload_products'),
    path('print-invoice/<int:invoice_id>/', views.print_invoice_pdf, name='print_invoice_pdf'),



    


]
