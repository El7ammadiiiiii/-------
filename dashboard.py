"""
Admin Dashboard - Streamlit interface for managing products and viewing orders
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal, Product, Order, Customer
from services.product_service import (
    get_all_products,
    create_product,
    update_product_price,
    delete_product
)

# Page configuration
st.set_page_config(
    page_title="لوحة تحكم المدير - Smart Sales Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for RTL support
st.markdown("""
<style>
    .main {
        direction: rtl;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📊 نظام إدارة المبيعات الذكي")
st.markdown("---")

# Get database session
db = SessionLocal()

try:
    # Sidebar - Product Management
    st.sidebar.header("🛠️ إدارة المنتجات")
    
    with st.sidebar.expander("➕ إضافة منتج جديد"):
        with st.form("add_product_form"):
            new_name = st.text_input("اسم المنتج")
            new_price = st.number_input("السعر (دينار)", min_value=0.0, step=0.5)
            new_desc = st.text_area("الوصف (اختياري)")
            
            submit_new = st.form_submit_button("إضافة المنتج")
            
            if submit_new and new_name and new_price > 0:
                try:
                    product = create_product(db, new_name, new_price, new_desc)
                    st.success(f"✅ تم إضافة المنتج: {product.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    with st.sidebar.expander("✏️ تعديل سعر منتج"):
        products = get_all_products(db)
        if products:
            product_options = {p.name: p.id for p in products}
            
            selected_product_name = st.selectbox(
                "اختر المنتج",
                options=list(product_options.keys())
            )
            
            selected_product_id = product_options[selected_product_name]
            current_product = next(p for p in products if p.id == selected_product_id)
            
            new_price_edit = st.number_input(
                f"السعر الحالي: {current_product.price} دينار",
                min_value=0.0,
                value=float(current_product.price),
                step=0.5,
                key="edit_price"
            )
            
            if st.button("💾 حفظ السعر الجديد"):
                if new_price_edit != current_product.price:
                    update_product_price(db, selected_product_id, new_price_edit)
                    st.success(f"✅ تم تحديث سعر {current_product.name}")
                    st.rerun()
        else:
            st.info("لا توجد منتجات لتعديلها")
    
    # Main content area
    # Statistics
    st.header("📈 الإحصائيات")
    
    orders = db.query(Order).all()
    customers = db.query(Customer).all()
    products = get_all_products(db)
    
    # Today's orders
    today = datetime.now().date()
    today_orders = [o for o in orders if o.created_at.date() == today]
    today_revenue = sum(o.total_amount for o in today_orders)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="💰 إجمالي المبيعات اليوم",
            value=f"{today_revenue:.2f} د.ك",
            delta=f"{len(today_orders)} طلب"
        )
    
    with col2:
        total_revenue = sum(o.total_amount for o in orders)
        st.metric(
            label="💵 إجمالي المبيعات الكلي",
            value=f"{total_revenue:.2f} د.ك",
            delta=f"{len(orders)} طلب"
        )
    
    with col3:
        st.metric(
            label="👥 عدد العملاء",
            value=len(set(o.customer_phone for o in orders))
        )
    
    with col4:
        st.metric(
            label="📦 عدد المنتجات",
            value=len(products)
        )
    
    st.markdown("---")
    
    # Orders table
    st.header("📋 سجل الطلبات والفواتير")
    
    if orders:
        # Create DataFrame
        orders_data = []
        for order in sorted(orders, key=lambda x: x.created_at, reverse=True):
            orders_data.append({
                "رقم الطلب": order.id,
                "العميل": order.customer_name,
                "رقم الهاتف": order.customer_phone,
                "المنتج": order.product_name,
                "المبلغ": f"{order.total_amount:.2f} د.ك",
                "الحالة": order.status,
                "التاريخ": order.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        df_orders = pd.DataFrame(orders_data)
        
        # Search and filter
        search_term = st.text_input("🔍 البحث (اسم العميل أو رقم الهاتف)")
        
        if search_term:
            df_filtered = df_orders[
                df_orders["العميل"].str.contains(search_term, case=False, na=False) |
                df_orders["رقم الهاتف"].str.contains(search_term, case=False, na=False)
            ]
        else:
            df_filtered = df_orders
        
        # Display table
        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True
        )
        
        # Download button
        csv = df_filtered.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 تحميل التقرير (Excel)",
            data=csv,
            file_name=f"orders_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("📭 لا توجد طلبات حتى الآن")
    
    st.markdown("---")
    
    # Products table
    st.header("🛍️ قائمة المنتجات والأسعار")
    
    if products:
        products_data = []
        for product in products:
            products_data.append({
                "المعرف": product.id,
                "اسم المنتج": product.name,
                "السعر": f"{product.price:.2f} د.ك",
                "الوصف": product.description or "-"
            })
        
        df_products = pd.DataFrame(products_data)
        
        st.dataframe(
            df_products,
            use_container_width=True,
            hide_index=True
        )
        
        # Delete product section
        with st.expander("🗑️ حذف منتج"):
            delete_product_name = st.selectbox(
                "اختر المنتج للحذف",
                options=[p.name for p in products],
                key="delete_select"
            )
            
            if st.button("⚠️ تأكيد الحذف", type="secondary"):
                product_to_delete = next(p for p in products if p.name == delete_product_name)
                if delete_product(db, product_to_delete.id):
                    st.success(f"✅ تم حذف المنتج: {delete_product_name}")
                    st.rerun()
                else:
                    st.error("❌ فشل الحذف")
    else:
        st.warning("⚠️ لا توجد منتجات في القائمة")
    
    # Footer
    st.markdown("---")
    st.caption(f"آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("Smart Sales Agent v1.0 - Powered by FastAPI & Streamlit")

finally:
    db.close()
