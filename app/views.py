from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required,user_passes_test
from .models import Profile,Product, Cart, CartItem, Customer, Invoice, InvoiceItem
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db import models
from .invoice_pdf import generate_invoice_pdf
from django.db.models import Sum,F
from django.db.models import Q
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import uuid

@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
  
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # Redirect based on role
            if user.is_superuser:
                return redirect('admin_dashboard')

            elif hasattr(user, 'profile'):
                if user.profile.role == 'manager':
                    return redirect('manager_dashboard')
                elif user.profile.role == 'cashier':
                    return redirect('cashier_dashboard')

            return redirect('/')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'login.html')

def superuser_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_superuser)(view_func)
    return decorated_view_func

@superuser_required
def admin_dashboard(request):
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    products = Product.objects.all().order_by('-created_at')
    categories = Product.CATEGORY_CHOICES  
    invoices = Invoice.objects.all().order_by('-created_at')
    low_stock_products = Product.objects.filter(
    stock_quantity__lte=models.F("low_stock_threshold")
).count()

    # DASHBOARD STATS
    total_users = Customer.objects.count()
    total_products = products.count()
    total_invoices = invoices.count()

   
    total_revenue = invoices.aggregate(total=Sum('grand_total'))['total'] or 0

    context = {
        'users': users,
        'products': products,
        'categories': categories,
        'invoices': invoices,

        # Stats for dashboard
        'total_users': total_users,
        'total_products': total_products,
        'total_invoices': total_invoices,
        'total_revenue': total_revenue,
        'low_stock_products': low_stock_products,
    }

    return render(request, 'admin_dashboard.html', context)


from django.db.models.functions import TruncWeek, TruncMonth
from datetime import datetime, timedelta
import json

from django.db.models import Sum, F
from django.utils.timezone import now
from django.db.models.functions import TruncMonth
from datetime import timedelta
import calendar
import json

@login_required
def manager_dashboard(request):

    # Manager role check
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'manager':
        return redirect('login')

    # ===== BASIC DASHBOARD DATA =====
    products = Product.objects.all().order_by('category', 'product_name')
    invoices = Invoice.objects.order_by('-created_at')[:5]
    low_stock_products = Product.objects.filter(stock_quantity__lte=F('low_stock_threshold')).count()

    customers = Customer.objects.annotate(
        total_spent=Sum('invoice__grand_total')
    ).order_by('-total_spent')

    total_sales = Invoice.objects.aggregate(total=Sum('grand_total'))['total'] or 0
    total_invoices = Invoice.objects.count()
    total_customers = Customer.objects.count()
    items_in_stock = Product.objects.aggregate(total=Sum('stock_quantity'))['total'] or 0

    # ===== CHART DATA =====
    today = now().date()

    # ---- WEEKLY SALES (LAST 7 DAYS) ----
    weekly_labels = []
    weekly_data = []
    for i in range(7):
        day = today - timedelta(days=6 - i)
        total = Invoice.objects.filter(created_at__date=day).aggregate(
            Sum("grand_total")
        )["grand_total__sum"] or 0

        weekly_labels.append(day.strftime("%a"))  # Mon, Tue
        weekly_data.append(float(total))

    # ---- MONTHLY SALES (Jan–Dec current year) ----
    monthly_labels = []
    monthly_data = []
    year = today.year

    for month in range(1, 13):
        total = Invoice.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).aggregate(Sum("grand_total"))["grand_total__sum"] or 0

        monthly_labels.append(calendar.month_abbr[month])  # Jan, Feb, Mar
        monthly_data.append(float(total))

    # ---- 6 MONTH SALES ----
    six_month_labels = []
    six_month_data = []
    for i in range(6):
        date_point = today.replace(day=1) - timedelta(days=30 * (5 - i))
        year_val = date_point.year
        month_val = date_point.month

        total = Invoice.objects.filter(
            created_at__year=year_val,
            created_at__month=month_val,
        ).aggregate(Sum("grand_total"))["grand_total__sum"] or 0

        six_month_labels.append(f"{calendar.month_abbr[month_val]} {year_val}")
        six_month_data.append(float(total))

    # ===== CONTEXT =====
    context = {
        "products": products,
        "invoices": invoices,
        "low_stock_products": low_stock_products,
        "customers": customers,

        "total_sales": total_sales,
        "total_invoices": total_invoices,
        "total_customers": total_customers,
        "items_in_stock": items_in_stock,

        "weekly_labels": json.dumps(weekly_labels),
        "weekly_data": json.dumps(weekly_data),

        "monthly_labels": json.dumps(monthly_labels),
        "monthly_data": json.dumps(monthly_data),

        "six_month_labels": json.dumps(six_month_labels),
        "six_month_data": json.dumps(six_month_data),
    }

    return render(request, "manager_dashboard.html", context)

from django.contrib import messages

@login_required
def delete_customer(request, customer_id):
    # Only manager is allowed
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'manager':
        return redirect("login")
    
    try:
        customer = Customer.objects.get(id=customer_id)
        customer.delete()
        messages.success(request, "Customer deleted successfully.")
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")

    return redirect("manager_dashboard")


@login_required
def cashier_dashboard(request):

    # If no current cart selected, create FIRST one
    if "current_cart_id" not in request.session:
        cart = Cart.objects.create(
            cashier=request.user,
            status="active",
            cart_number=1
        )
        request.session["current_cart_id"] = cart.id

    # Load current cart
    current_cart_id = request.session["current_cart_id"]
    cart = Cart.objects.get(id=current_cart_id)

    cart_items = cart.items.all()

    # Load ALL active carts (for multi-tab display)
    active_carts = Cart.objects.filter(
        cashier=request.user,
        status="active"
    ).order_by("cart_number")

    context = {
        "cart_items": cart_items,
        "totals": cart.get_totals,
        "active_carts": active_carts,
        "current_cart": cart
    }
    return render(request, "cashier_dashboard.html", context)
@login_required
def create_new_cart(request):
    # Get last cart to increment number
    last_cart = Cart.objects.filter(cashier=request.user).order_by('-cart_number').first()
    next_no = (last_cart.cart_number + 1) if last_cart else 1

    cart = Cart.objects.create(
        cashier=request.user,
        status="active",
        cart_number=next_no
    )

    request.session["current_cart_id"] = cart.id

    return JsonResponse({"status": "created", "cart_number": next_no})
@login_required
def switch_cart(request, cart_id):
    request.session["current_cart_id"] = int(cart_id)
    return JsonResponse({"status": "switched"})



def user_logout(request):
    logout(request)
    return redirect('login')








@superuser_required
def add_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']
        status = request.POST['status']
        full_name = request.POST['full_name']

        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            return render(request, 'admin_dashboard.html', {'error': 'Username already exists'})
        if User.objects.filter(email=email).exists():
            return render(request, 'admin_dashboard.html', {'error': 'Email already exists'})

        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create a related Profile entry
        Profile.objects.create(
            user=user,
            full_name=full_name,  
            role=role,
            status=status
        )

        users = User.objects.all()
        return render(request, 'admin_dashboard.html', {
            'success': f'{role.capitalize()} "{username}" added successfully!',
            'users': users
        })

    users = User.objects.all()
    return render(request, 'admin_dashboard.html', {'users': users})


def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile

    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        role = request.POST['role']
        status = request.POST['status']

        user.username = username
        user.email = email
        user.save()

        profile.role = role
        profile.status = status
        profile.save()

        messages.success(request, f'User "{username}" updated successfully!')
        return redirect('admin_dashboard')

    return render(request, 'edit_user.html', {'user_obj': user, 'profile': profile})


# --- Delete user ---
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted successfully!')
    return redirect('admin_dashboard')

def generate_product_code():
    last_product = Product.objects.order_by('id').last()
    if not last_product:
        return "PRD001"
    product_id = last_product.id + 1
    return f"PRD{product_id:03d}"



def add_product(request):
    if request.method == 'POST':
        product_name = request.POST.get('name')
        category = request.POST.get('category')
        price = request.POST.get('price')
        cost_price = request.POST.get('cost_price')  # NEW
        manufacturer = request.POST.get('manufacturer')  # NEW
        stock_quantity = request.POST.get('stock_quantity')
        low_stock_threshold = request.POST.get('low_stock_threshold')
        description = request.POST.get('description', '')

        product_code = generate_product_code()

        Product.objects.create(
            product_name=product_name,
            product_code=product_code,
            category=category,
            price=price,
            cost_price=cost_price,               
            manufacturer=manufacturer,           
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            description=description,
            status='active'
        )

        messages.success(request, f'Product "{product_name}" added successfully!')
        return redirect('admin_dashboard')

    return redirect('admin_dashboard')


def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.product_name = request.POST.get('name')
        product.category = request.POST.get('category')
        product.price = request.POST.get('price')
        product.stock_quantity = request.POST.get('stock_quantity')
        product.low_stock_threshold = request.POST.get('low_stock_threshold')
        product.description = request.POST.get('description')
        product.status = request.POST.get('status', 'active')
        product.cost_price = request.POST.get('cost_price')
        product.manufacturer = request.POST.get('manufacturer')
        product.save()
        messages.success(request, f'Product "{product.product_name}" updated successfully!')
        return redirect('admin_dashboard')

    categories = Product.CATEGORY_CHOICES
    return render(request, 'edit_product.html', {'product': product, 'categories': categories})


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    
    product.status = "inactive"
    product.save()

    messages.success(request, f'Product "{product.product_name}" has been deactivated (not deleted).')
    return redirect('admin_dashboard')


def filter_products(request):
    category = request.GET.get('category', '')
    if category:
        products = Product.objects.filter(category=category)
    else:
        products = Product.objects.all()

    # Directly render the same part of admin_dashboard
    html = render_to_string(
        'admin_dashboard.html',
        {'products': products},
        request=request
    )

    # Extract only the tbody content (optional but cleaner)
    start = html.find('<tbody id="productsTableBody">')
    end = html.find('</tbody>', start)
    rows_html = html[start + len('<tbody id="productsTableBody">'):end]

    return JsonResponse({'html': rows_html})

def dashboard_data(request):
    total_users = Customer.objects.count()
    total_products = Product.objects.count()
    total_invoices = Invoice.objects.count()

    total_revenue = Invoice.objects.aggregate(
        total=Sum("grand_total")
    )["total"] or 0

    return JsonResponse({
        "totalUsers": total_users,
        "totalProducts": total_products,
        "totalInvoices": total_invoices,
        "totalRevenue": float(total_revenue)
    })

def invoices_data(request):
    invoices = Invoice.objects.values(
        "id", "grand_total", "payment_method", "created_at"
    )
    return JsonResponse(list(invoices), safe=False)

def products_data(request):
    products = Product.objects.values(
        "id", "product_name", "category", "stock_quantity"
    )
    return JsonResponse(list(products), safe=False)

@login_required
def view_product_details(request, product_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'manager':
        return redirect('login')

    product = get_object_or_404(Product, id=product_id)
    return render(request, 'view_product.html', {'product': product})
@login_required
def update_stock(request, product_id):
    # Ensure only managers can access this
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'manager':
        return redirect('login')

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        new_quantity = request.POST.get('stock_quantity')
        if new_quantity:
            product.stock_quantity = new_quantity
            product.save()
            messages.success(request, f'Stock updated for "{product.product_name}"!')
            return redirect('manager_dashboard')

    return render(request, 'update_stock.html', {'product': product})


@login_required
def product_lookup(request):
    query = request.GET.get("q", "")

    if len(query) < 2:
        return JsonResponse({"products": []})

    products = Product.objects.filter(
        Q(product_name__icontains=query) |
        Q(product_code__icontains=query),
        status="active"
    )[:10]

    data = [
        {
            "id": p.id,
            "name": p.product_name,
            "price": str(p.price),
            "sku": p.product_code,
        }
        for p in products
    ]

    return JsonResponse({"products": data})

@login_required
def add_to_cart(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        product = Product.objects.get(id=product_id)

        cart_id = request.session["current_cart_id"]
        cart = Cart.objects.get(id=cart_id)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if not created:
            cart_item.quantity += 1

        cart_item.save()

        return JsonResponse({
            "status": "success",
            "message": "Product added",
            "totals": cart.get_totals
        })
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# 1. NEW VIEW: Start Payment (Creates Order ID)
def start_payment(request):
    if request.method == "POST":
        cart_id = request.session.get("current_cart_id")
        cart = get_object_or_404(Cart, id=cart_id)
        
        # Razorpay expects amount in PAISE (Rupees * 100)
        amount_in_paise = int(cart.get_totals['grand_total'] * 100)
        
        # Create Order
        data = { 
            "amount": amount_in_paise, 
            "currency": "INR", 
            "payment_capture": "1" 
        }
        order = client.order.create(data=data)
        
        return JsonResponse({
            "order_id": order['id'],
            "amount": amount_in_paise,
            "key": settings.RAZORPAY_KEY_ID,
            "name": "Supermarket POS",
            "description": f"Bill #{cart.cart_number}",
            "prefill_contact": "9999999999"
        })
@login_required
def remove_from_cart(request):
    product_id = request.POST.get("product_id")

    cart_id = request.session["current_cart_id"]
    cart = Cart.objects.get(id=cart_id)

    CartItem.objects.filter(cart=cart, product_id=product_id).delete()

    return JsonResponse({
        "status": "success",
        "totals": cart.get_totals
    })


@login_required
def update_quantity(request):
    product_id = request.POST.get("product_id")
    qty = int(request.POST.get("qty", 1))

    cart_id = request.session["current_cart_id"]
    cart = Cart.objects.get(id=cart_id)

    item = CartItem.objects.get(cart=cart, product_id=product_id)
    item.quantity = qty
    item.save()

    return JsonResponse({
        "status": "success",
        "totals": cart.get_totals
    })

@login_required
def generate_invoice(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Invalid method'}, status=400)

    # 1. Extract Form Data
    customer_phone = request.POST.get("customer_phone")
    customer_name = request.POST.get("customer_name")
    payment_method = request.POST.get("payment_method", "cash")

    # ---------------------------------------------------------
    # 2. RAZORPAY VERIFICATION (Only if UPI/Online is selected)
    # ---------------------------------------------------------
    transaction_id = "" # Default empty for Cash/Card
    
    if payment_method == 'upi':
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        # Prepare dictionary for verification
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            # Verify the signature
            client.utility.verify_payment_signature(params_dict)
            
            # If we reach here, payment is successful
            transaction_id = razorpay_payment_id
            print(f"Payment Verified: {transaction_id}")
            
        except razorpay.errors.SignatureVerificationError:
            # Security Breach: Signature didn't match
            return HttpResponse("Payment Verification Failed! Do not release goods.", status=400)
        except Exception as e:
            print(e)
            return HttpResponse("Error verifying payment", status=400)

    # ---------------------------------------------------------
    # 3. CUSTOMER & CART LOGIC (Existing Logic)
    # ---------------------------------------------------------
    
    customer, created = Customer.objects.get_or_create(
        phone=customer_phone,
        defaults={"name": customer_name or "Guest"}
    )

    cart_id = request.session.get("current_cart_id")
    # Safety check if session expired or cart missing
    if not cart_id:
        return redirect("cashier_dashboard")
        
    cart = get_object_or_404(Cart, id=cart_id)
    cart_items = cart.items.all()

    if not cart_items:
        messages.error(request, "Cart is empty.")
        return redirect("cashier_dashboard")

    # 4. STOCK CHECK
    for item in cart_items:
        if item.quantity > item.product.stock_quantity:
            messages.error(request, f"Not enough stock for {item.product.product_name}")
            return redirect("checkout")

    totals = cart.get_totals

    # 5. CREATE INVOICE
    invoice = Invoice.objects.create(
        invoice_number=str(uuid.uuid4())[:8].upper(),
        cashier=request.user,
        customer=customer,
        sub_total=totals["sub_total"],
        total_gst=totals["total_gst"],
        grand_total=totals["grand_total"],
        payment_method=payment_method,
        status="paid",
        # Optional: If your Invoice model has a transaction_id field, uncomment below:
        # transaction_id=transaction_id 
    )

    # 6. MOVE ITEMS TO INVOICE & DEDUCT STOCK
    for item in cart_items:
        InvoiceItem.objects.create(
            invoice=invoice,
            product=item.product,
            product_name=item.product.product_name,
            price_at_sale=item.product.price,
            quantity=item.quantity
        )

        # Deduct Stock
        new_stock = item.product.stock_quantity - item.quantity
        item.product.stock_quantity = max(new_stock, 0)
        item.product.save()

    # 7. CLOSE CURRENT CART
    cart.status = "completed"
    cart.save()

    # 8. CREATE NEW CART FOR NEXT CUSTOMER
    new_cart = Cart.objects.create(
        cashier=request.user,
        status="active",
        cart_number=cart.cart_number + 1
    )
    request.session["current_cart_id"] = new_cart.id

    return JsonResponse({
        'status': 'success',
        'invoice_id': invoice.id,
        'message': 'Invoice generated successfully'
    })


@login_required
def print_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    # Call your existing PDF helper function here
    return generate_invoice_pdf(invoice)


@property
def get_totals(self):
    items = self.items.all()
    sub_total = sum(item.total_price for item in items)

    gst_rate = Decimal("0.05")
    gst = sub_total * gst_rate

    grand = sub_total + gst

    return {
        "sub_total": round(sub_total, 2),
        "total_gst": round(gst, 2),
        "grand_total": round(grand, 2),
    }
@login_required
def remove_cart(request, cart_id):
    cart = Cart.objects.get(id=cart_id, cashier=request.user)

   
    if request.session.get("current_cart_id") == cart_id:
        next_cart = Cart.objects.filter(
            cashier=request.user, status="active"
        ).exclude(id=cart_id).first()

        if next_cart:
            request.session["current_cart_id"] = next_cart.id
        else:
            
            new_cart = Cart.objects.create(
                cashier=request.user,
                status="active",
                cart_number=cart.cart_number + 1
            )
            request.session["current_cart_id"] = new_cart.id

    cart.delete()

    return JsonResponse({"status": "deleted"})
@login_required
def checkout_page(request):
    cart_id = request.session.get("current_cart_id")

   
    if not cart_id:
        messages.error(request, "You do not have an active cart session.")
        return redirect("cashier_dashboard")

    
    try:
        cart = Cart.objects.get(
            id=cart_id,
            cashier=request.user,
            status="active"
        )
    except Cart.DoesNotExist:
        messages.error(request, "Your active cart could not be found or has expired.")
       
        if "current_cart_id" in request.session:
            del request.session["current_cart_id"]
        return redirect("cashier_dashboard")

    
    cart_items = cart.items.select_related('product').all()

    
    if not cart_items:
        messages.warning(request, "Your cart is empty. Please add items to proceed.")
        return redirect("cashier_dashboard")

    
    totals = cart.get_totals
    context = {
        "cart_items": cart_items,
        "totals": totals,
        "cart": cart
    }
    return render(request, "checkout.html", context)



@login_required
def customer_lookup(request):
    phone = request.GET.get("phone", "")

    
    if len(phone) < 3:
        return JsonResponse({"found": False})

    
    customer = Customer.objects.filter(phone__icontains=phone).first()

    if customer:
        data = {
            "found": True,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email
        }
    else:
        data = {"found": False}
    
    return JsonResponse(data)

@login_required
def sales_report(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'manager':
        return redirect('login')

    sales_data = Invoice.objects.values('created_at__date').annotate(
        daily_sales=Sum('grand_total')
    ).order_by('-created_at__date')

    context = {
        'sales_data': sales_data,
    }
    return render(request, 'sales_report.html', context)
    

def api_category_revenue(request):
    data = (
        InvoiceItem.objects
        .values(category=F('product__category'))
        .annotate(revenue=Sum(F('price_at_sale') * F('quantity')))
        .order_by('-revenue')
    )

    return JsonResponse(list(data), safe=False)

def api_cashier_performance(request):
    data = (
        Invoice.objects
        .values(cashier_name=F('cashier__username'))
        .annotate(total_sales=Sum('grand_total'))
        .order_by('-total_sales')
    )

    return JsonResponse(list(data), safe=False)

def api_top_products(request):
    data = (
        InvoiceItem.objects
        .values(product_label=F('product__product_name'))
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:10]
    )

    return JsonResponse(list(data), safe=False)

from django.db.models import Sum, F, ExpressionWrapper, DecimalField

def api_profit_report(request):
    data = (
        InvoiceItem.objects
        .annotate(
            revenue=F("price_at_sale") * F("quantity"),
            cost=F("product__cost_price") * F("quantity"),
            profit=ExpressionWrapper(
                F("price_at_sale") * F("quantity") - F("product__cost_price") * F("quantity"),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
        .values("product_name")
        .annotate(
            total_revenue=Sum("revenue"),
            total_cost=Sum("cost"),
            total_profit=Sum("profit")
        )
        .order_by("-total_profit")
    )

    return JsonResponse(list(data), safe=False)
def api_margin_report(request):
    data = (
        InvoiceItem.objects
        .annotate(
            revenue=F("price_at_sale") * F("quantity"),
            cost=F("product__cost_price") * F("quantity"),
        )
        .values("product_name")
        .annotate(
            total_revenue=Sum("revenue"),
            total_cost=Sum("cost"),
        )
    )

    final = []
    for d in data:
        rev = d["total_revenue"]
        cost = d["total_cost"]
        margin = ((rev - cost) / rev * 100) if rev > 0 else 0

        final.append({
            "product_name": d["product_name"],
            "margin": round(margin, 2)
        })

    return JsonResponse(final, safe=False)
def api_sales_report(request):
    data = (
        InvoiceItem.objects
        .values("product_name")
        .annotate(total_sold=Sum("quantity"))
        .order_by("-total_sold")
    )
    return JsonResponse(list(data), safe=False)


def api_stock_report(request):
    data = (
        Product.objects
        .annotate(
            stock_value=F("stock_quantity") * F("cost_price")
        )
        .values("product_name", "stock_quantity", "stock_value")
        .order_by("product_name")
    )
    return JsonResponse(list(data), safe=False)

def api_manufacturer_report(request):
    data = (
        Product.objects
        .values("manufacturer")
        .annotate(
            total_products=Sum(1),
            total_stock=Sum("stock_quantity"),
            stock_value=Sum(F("stock_quantity") * F("cost_price")),
        )
        .order_by("manufacturer")
    )
    return JsonResponse(list(data), safe=False)
    import json
from django.shortcuts import render
from .models import Product

def upload_products(request):
    if request.method == "POST":
        file = request.FILES['json_file']
        data = json.load(file)

        for item in data:
            Product.objects.create(
                product_name=item['product_name'],
                product_code=item['product_code'],
                category=item['category'],
                price=item['price'],
                cost_price=item['cost_price'],
                manufacturer=item['manufacturer'],
                stock_quantity=item['stock_quantity'],
                low_stock_threshold=item['low_stock_threshold'],
                description=item['description'],
                status=item['status']
            )

        return render(request, 'upload_products.html', {"msg": "Products uploaded successfully!"})

    return render(request, 'upload_products.html')

