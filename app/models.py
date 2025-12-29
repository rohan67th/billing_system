from django.db import models
from decimal import Decimal

@property
def get_totals(self):
    items = self.items.all()

    sub_total = sum(item.total_price for item in items)

    gst_rate = Decimal("0.05")   # GST as Decimal, NOT float
    gst = Decimal(sub_total) * gst_rate

    grand = sub_total + gst

    return {
        'sub_total': round(sub_total, 2),
        'total_gst': round(gst, 2),
        'grand_total': round(grand, 2)
    }

from django.contrib.auth.models import User

# ======================================================
# USER PROFILE MODEL
# ======================================================

class Profile(models.Model):
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('cashier', 'Cashier'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, default="Admin")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.full_name} ({self.role})"


# ======================================================
# PRODUCT MODEL
# ======================================================

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('grocery', 'Grocery'),
        ('vegetables', 'Vegetables'),
        ('beverages', 'Beverages'),
        ('snacks', 'Snacks'),
        ('others', 'Others'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    product_name = models.CharField(max_length=100)
    product_code = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField()
    low_stock_threshold = models.PositiveIntegerField(default=10)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} ({self.product_code})"




class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"


# ======================================================
# CART & CART ITEMS
# ======================================================

class Cart(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
    ]

    cashier = models.ForeignKey(User, on_delete=models.CASCADE, related_name="carts")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cart_number = models.IntegerField(default=1)

    def __str__(self):
        return f"Cart {self.id} ({self.status}) by {self.cashier.username}"

    @property
    def get_totals(self):
        items = self.items.all()
        sub_total = sum(item.total_price for item in items)

        # Use Decimal("0.05") NOT the float 0.05
        gst_rate = Decimal("0.05")
        gst = sub_total * gst_rate  # <-- THE FIX

        grand = sub_total + gst

        return {
            'sub_total': round(sub_total, 2),
            'total_gst': round(gst, 2),
            'grand_total': round(grand, 2)
        }


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    

    class Meta:
        unique_together = ('cart', 'product')

    @property
    def total_price(self):
        return self.product.price * self.quantity


# ======================================================
# INVOICE & INVOICE ITEMS
# ======================================================

class Invoice(models.Model):
    STATUS = [
        ("paid", "Paid"),
        ("pending", "Pending"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("upi", "UPI"),
    ]

    invoice_number = models.CharField(max_length=100, unique=True)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    sub_total = models.DecimalField(max_digits=10, decimal_places=2)
    total_gst = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="cash")



class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=100)
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def total_price(self):
        return self.price_at_sale * self.quantity
