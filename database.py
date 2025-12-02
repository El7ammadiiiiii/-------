"""
Database models and configuration for SmartSalesAgent
Using SQLAlchemy with SQLite for zero-cost storage
نظام مطبعة تغليف المطاعم والكافيهات
"""
try:
    from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, JSON
    from sqlalchemy.orm import declarative_base, sessionmaker, Session
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "SQLAlchemy is required for database operations. Install it with 'pip install SQLAlchemy'."
    ) from exc
from datetime import datetime
from typing import Generator

# Database setup
DATABASE_URL = "sqlite:///./shop.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

# Base class for models
Base = declarative_base()


class ProductCategory(Base):
    """فئات المنتجات الرئيسية"""
    __tablename__ = "product_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # أكواب، أكياس، علب...
    name_en = Column(String)  # Cups, Bags, Containers
    description = Column(Text)
    icon = Column(String, default="📦")
    
    def __repr__(self):
        return f"<Category(name='{self.name}')>"


class ProductType(Base):
    """أنواع المنتجات داخل كل فئة"""
    __tablename__ = "product_types"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, nullable=False)  # FK to ProductCategory
    name = Column(String, nullable=False)  # أكواب ساخنة، أكواب باردة
    name_en = Column(String)
    material = Column(String)  # ورق مقوى، بلاستيك PET، PP
    description = Column(Text)
    
    def __repr__(self):
        return f"<ProductType(name='{self.name}')>"


class ProductVariant(Base):
    """متغيرات المنتج (الأحجام والخيارات)"""
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, nullable=False)  # FK to ProductType
    name = Column(String, nullable=False)  # Single Wall 8oz
    size = Column(String)  # 4oz, 8oz, 12oz, صغير، وسط
    size_details = Column(String)  # 20×10×28 سم
    variant_type = Column(String)  # جدار واحد، دبل، مموج
    base_price = Column(Float, default=0)  # سعر الوحدة الأساسي
    min_quantity = Column(Integer, default=100)  # الحد الأدنى للطلب
    is_available = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Variant(name='{self.name}', size='{self.size}')>"


class PricingTier(Base):
    """شرائح الأسعار (خصم الكميات)"""
    __tablename__ = "pricing_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, nullable=False)  # FK to ProductVariant
    min_quantity = Column(Integer, nullable=False)  # 1000
    max_quantity = Column(Integer)  # 5000 (NULL = unlimited)
    price_per_unit = Column(Float, nullable=False)  # سعر الوحدة لهذه الشريحة
    
    def __repr__(self):
        return f"<PricingTier(qty={self.min_quantity}-{self.max_quantity}, price={self.price_per_unit})>"


class Accessory(Base):
    """الملحقات والإضافات"""
    __tablename__ = "accessories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # غطاء، كم، حامل
    name_en = Column(String)  # Lid, Sleeve, Holder
    compatible_with = Column(String)  # أنواع المنتجات المتوافقة
    price = Column(Float, default=0)
    description = Column(Text)
    
    def __repr__(self):
        return f"<Accessory(name='{self.name}')>"


class ConversationState(Base):
    """حالة المحادثة مع كل عميل"""
    __tablename__ = "conversation_states"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, nullable=False)
    current_step = Column(String, default="greeting")  # greeting, category, type, size, variant, quantity, confirm
    selected_category_id = Column(Integer)
    selected_type_id = Column(Integer)
    selected_variant_id = Column(Integer)
    selected_quantity = Column(Integer)
    selected_accessories = Column(JSON)  # [{"id": 1, "qty": 500}]
    customer_name = Column(String)
    notes = Column(Text)  # ملاحظات إضافية
    last_message = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ConversationState(phone='{self.phone_number}', step='{self.current_step}')>"


class Customer(Base):
    """Customer information extracted from conversations"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    business_name = Column(String)  # اسم المطعم/الكافيه
    first_contact = Column(DateTime, default=datetime.utcnow)
    last_contact = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_orders = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Customer(name='{self.name}', phone='{self.phone_number}')>"


class Order(Base):
    """Orders and invoices generated by bot"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_phone = Column(String, nullable=False)
    customer_name = Column(String, nullable=False)
    business_name = Column(String)
    order_details = Column(JSON)  # تفاصيل الطلب كاملة
    total_amount = Column(Float, nullable=True)  # يتم التحديد بعد موافقة الإدارة
    invoice_path = Column(String, nullable=True)
    status = Column(String, default="New")  # New, PendingApproval, ApprovedWaitingPayment, Paid, InProduction, Ready, Delivered, RejectedNoCapacity, Cancelled
    # حقول قرار الإدارة
    has_capacity = Column(Boolean, nullable=True)  # هل توجد إمكانية لتنفيذ الطلب
    approved_amount = Column(Float, nullable=True)  # المبلغ المعتمد من الإدارة
    estimated_days = Column(Integer, nullable=True)  # المدة الزمنية المتوقعة للتنفيذ
    # حقول الدفع
    payment_url = Column(String, nullable=True)
    payment_status = Column(String, default="Pending")  # Pending, Paid, Failed
    paid_at = Column(DateTime, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Order(id={self.id}, customer='{self.customer_name}', total={self.total_amount})>"


class ChatLog(Base):
    """Log of all WhatsApp interactions"""
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    message_type = Column(String)  # incoming, outgoing
    message_content = Column(String)
    intent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ChatLog(phone='{self.phone_number}', type='{self.message_type}')>"


# ============================================
# بيانات كتالوج المطبعة الكاملة
# ============================================

PRINT_SHOP_CATALOG = """
أنت مساعد مبيعات ذكي لمطبعة متخصصة في تغليف المطاعم والكافيهات.

═══════════════════════════════════════════
1️⃣ قسم الأكواب (Cups)
═══════════════════════════════════════════

🔥 أكواب المشروبات الساخنة (Hot Cups)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الخامة: ورق مقوى مخصص للأغذية

الأنواع:
• جدار واحد (Single Wall): اقتصادي، يحتاج أحياناً إلى "كم" (Sleeve)
• جدار مزدوج (Double Wall): فاخر، عزل حراري عالي، لا يحتاج لكم
• جدار مموج (Ripple Wall): ملمس بارز، عزل ممتاز، شكل فخم

المقاسات:
• 4 oz: اسبريسو / قهوة عربية
• 8 oz: كابتشينو / فلات وايت (الحجم الصغير)
• 12 oz: لاتيه / أمريكانو (الحجم الوسط)
• 16 oz: مشروبات كبيرة

🧊 أكواب المشروبات الباردة (Cold Cups)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
الخامات:
• PET: شفاف نقي (Crystal Clear)، قوي، قابل للتدوير - الأغلى والأفخم
• PP: نصف شفاف (ضبابي)، طري قليلاً، اقتصادي السعر

المقاسات: 12 oz، 14 oz، 16 oz

🔧 ملحقات الأكواب (Accessories)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• الأغطية (Lids): مسطحة (Flat) للساخن، قبة (Dome) للبارد والكريمة
• الكم (Sleeve): ورق كرتون للحماية من الحرارة (للسنجل)
• حامل الأكواب (Cup Holder): كرتون لـ 2 أو 4 أكواب
• المزازات (Straws): ورقية - 6 ملم للعصير، 8-10 ملم للسموذي

═══════════════════════════════════════════
2️⃣ قسم الأكياس الورقية (Paper Bags)
═══════════════════════════════════════════

الخامات:
• كرافت بني (Kraft): مظهر طبيعي (Organic)
• أبيض (Bleached): لطباعة ألوان زاهية

أنواع المقابض (اليدي):
• ميرومة (Twisted): قوية وأنيقة
• مسطحة (Flat): اقتصادية
• بدون يد (SOS): تغلق بالطي من الأعلى

المقاسات (عرض × عمق × ارتفاع):
• صغير (S): 20×10×28 سم - للبرجر الواحد/سندويش
• وسط (M): 26×12×32 سم - وجبات الأفراد
• كبير (L): 32×14×42 سم - طلبات عائلية/توصيل

═══════════════════════════════════════════
3️⃣ قسم الوجبات والأطعمة (Food Containers)
═══════════════════════════════════════════

🍔 السندويشات والبرجر
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• ورق التغليف (Wraps): ورق شمعي مقاوم للدهون - مقاسات 25×35 سم أو 30×40 سم
• علب البرجر: كرتون مانع للتسرب - 10×10 سم (عادي) أو 12×12 سم (جامبو)
• علب البطاطس: شكل كوب (Cup) أو جيب (Scoop)
• علب الصمون (Wedge): مثلثة بنافذة شفافة (للسندويشات الباردة)

🍕 الوجبات الكبيرة
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• علب البيتزا: كرتون مضلع (E-Flute) - مقاسات 25 سم، 30 سم، 35 سم
• علب النودلز/الباستا: دائرية مطلية PE - 16 oz أو 26 oz
• علب الوجبات (Meal Box): علبة كبيرة مع فواصل داخلية

═══════════════════════════════════════════
4️⃣ قسم الحلويات والمخابز (Bakery & Sweets)
═══════════════════════════════════════════

• علب الكيك/الحلوى: كرتون قوي مع نافذة بلاستيكية شفافة
• أكواب الآيس كريم: ورقية واسعة وقصيرة - 4 oz أو 8 oz
• أكياس الكوكيز (Tin Tie): مبطنة مع سلك معدني للإغلاق

═══════════════════════════════════════════
5️⃣ المكملات والدعاية (Branding Tools)
═══════════════════════════════════════════

• المناديل (Napkins): طباعة الشعار (1 أو 2 لون)
• المناديل المعطرة (Wet Wipes): مغلف مطبوع
• أظرف أدوات المائدة (Cutlery Sleeves): جيب ورقي للشوكة والسكين
• ورق الصينية (Tray Mat): ورقة دعائية للصواني
• الاستيكرات (Stickers): حل اقتصادي للعلب السادة

═══════════════════════════════════════════
📋 معلومات مهمة للعملاء
═══════════════════════════════════════════

• الحد الأدنى للطلب: يختلف حسب المنتج (عادة 500-1000 قطعة)
• مدة التسليم: 7-14 يوم عمل حسب الكمية
• الطباعة: متوفرة على جميع المنتجات (شعار، ألوان كاملة)
• عينات: متوفرة قبل الطلب الكبير

═══════════════════════════════════════════
"""


def init_db():
    """
    Initialize database and create all tables
    Add catalog data for the print shop
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    
    try:
        # ============================================
        # إضافة الفئات الرئيسية
        # ============================================
        if not session.query(ProductCategory).first():
            categories = [
                ProductCategory(id=1, name="أكواب", name_en="Cups", icon="☕", 
                               description="أكواب المشروبات الساخنة والباردة"),
                ProductCategory(id=2, name="أكياس ورقية", name_en="Paper Bags", icon="🛍️",
                               description="أكياس التغليف بجميع الأحجام"),
                ProductCategory(id=3, name="علب الطعام", name_en="Food Containers", icon="🍔",
                               description="علب السندويشات والوجبات"),
                ProductCategory(id=4, name="الحلويات والمخابز", name_en="Bakery", icon="🧁",
                               description="علب الكيك والحلويات"),
                ProductCategory(id=5, name="المكملات والدعاية", name_en="Branding", icon="🎨",
                               description="مناديل، استيكرات، ملحقات"),
            ]
            session.add_all(categories)
            session.commit()
            print("✅ Categories added")
        
        # ============================================
        # إضافة أنواع المنتجات
        # ============================================
        if not session.query(ProductType).first():
            types = [
                # أكواب ساخنة
                ProductType(id=1, category_id=1, name="أكواب ساخنة", name_en="Hot Cups",
                           material="ورق مقوى", description="للقهوة والشاي والمشروبات الساخنة"),
                # أكواب باردة
                ProductType(id=2, category_id=1, name="أكواب باردة", name_en="Cold Cups",
                           material="بلاستيك", description="للعصائر والمشروبات الباردة"),
                # ملحقات الأكواب
                ProductType(id=3, category_id=1, name="ملحقات الأكواب", name_en="Cup Accessories",
                           description="أغطية، أكمام، حوامل، مزازات"),
                # أكياس كرافت
                ProductType(id=4, category_id=2, name="أكياس كرافت بني", name_en="Kraft Bags",
                           material="ورق كرافت", description="مظهر طبيعي"),
                # أكياس بيضاء
                ProductType(id=5, category_id=2, name="أكياس بيضاء", name_en="White Bags",
                           material="ورق أبيض", description="لطباعة الألوان الزاهية"),
                # علب البرجر
                ProductType(id=6, category_id=3, name="علب البرجر", name_en="Burger Boxes",
                           material="كرتون", description="علب السندويشات والبرجر"),
                # ورق التغليف
                ProductType(id=7, category_id=3, name="ورق التغليف", name_en="Wrapping Paper",
                           material="ورق شمعي", description="ورق مقاوم للدهون"),
                # علب البيتزا
                ProductType(id=8, category_id=3, name="علب البيتزا", name_en="Pizza Boxes",
                           material="كرتون مضلع", description="E-Flute لحفظ الحرارة"),
                # علب الكيك
                ProductType(id=9, category_id=4, name="علب الكيك", name_en="Cake Boxes",
                           material="كرتون", description="مع نافذة شفافة"),
                # أكواب الآيس كريم
                ProductType(id=10, category_id=4, name="أكواب آيس كريم", name_en="Ice Cream Cups",
                           material="ورق", description="واسعة وقصيرة"),
                # المناديل
                ProductType(id=11, category_id=5, name="مناديل", name_en="Napkins",
                           description="طباعة 1-2 لون"),
                # استيكرات
                ProductType(id=12, category_id=5, name="استيكرات", name_en="Stickers",
                           description="حل اقتصادي للعلامة التجارية"),
            ]
            session.add_all(types)
            session.commit()
            print("✅ Product types added")
        
        # ============================================
        # إضافة المتغيرات (الأحجام والأنواع)
        # ============================================
        if not session.query(ProductVariant).first():
            variants = [
                # === أكواب ساخنة - جدار واحد ===
                ProductVariant(type_id=1, name="كوب ساخن 4oz سنجل", size="4 oz", 
                              variant_type="جدار واحد", min_quantity=500),
                ProductVariant(type_id=1, name="كوب ساخن 8oz سنجل", size="8 oz",
                              variant_type="جدار واحد", min_quantity=500),
                ProductVariant(type_id=1, name="كوب ساخن 12oz سنجل", size="12 oz",
                              variant_type="جدار واحد", min_quantity=500),
                ProductVariant(type_id=1, name="كوب ساخن 16oz سنجل", size="16 oz",
                              variant_type="جدار واحد", min_quantity=500),
                
                # === أكواب ساخنة - دبل ===
                ProductVariant(type_id=1, name="كوب ساخن 8oz دبل", size="8 oz",
                              variant_type="جدار مزدوج", min_quantity=500),
                ProductVariant(type_id=1, name="كوب ساخن 12oz دبل", size="12 oz",
                              variant_type="جدار مزدوج", min_quantity=500),
                ProductVariant(type_id=1, name="كوب ساخن 16oz دبل", size="16 oz",
                              variant_type="جدار مزدوج", min_quantity=500),
                
                # === أكواب ساخنة - مموج ===
                ProductVariant(type_id=1, name="كوب ساخن 8oz مموج", size="8 oz",
                              variant_type="جدار مموج", min_quantity=500),
                ProductVariant(type_id=1, name="كوب ساخن 12oz مموج", size="12 oz",
                              variant_type="جدار مموج", min_quantity=500),
                ProductVariant(type_id=1, name="كوب ساخن 16oz مموج", size="16 oz",
                              variant_type="جدار مموج", min_quantity=500),
                
                # === أكواب باردة PET ===
                ProductVariant(type_id=2, name="كوب بارد PET 12oz", size="12 oz",
                              variant_type="PET شفاف", min_quantity=500),
                ProductVariant(type_id=2, name="كوب بارد PET 14oz", size="14 oz",
                              variant_type="PET شفاف", min_quantity=500),
                ProductVariant(type_id=2, name="كوب بارد PET 16oz", size="16 oz",
                              variant_type="PET شفاف", min_quantity=500),
                
                # === أكواب باردة PP ===
                ProductVariant(type_id=2, name="كوب بارد PP 12oz", size="12 oz",
                              variant_type="PP اقتصادي", min_quantity=500),
                ProductVariant(type_id=2, name="كوب بارد PP 14oz", size="14 oz",
                              variant_type="PP اقتصادي", min_quantity=500),
                ProductVariant(type_id=2, name="كوب بارد PP 16oz", size="16 oz",
                              variant_type="PP اقتصادي", min_quantity=500),
                
                # === أكياس كرافت ===
                ProductVariant(type_id=4, name="كيس كرافت صغير", size="صغير",
                              size_details="20×10×28 سم", variant_type="يد ميرومة", min_quantity=500),
                ProductVariant(type_id=4, name="كيس كرافت وسط", size="وسط",
                              size_details="26×12×32 سم", variant_type="يد ميرومة", min_quantity=500),
                ProductVariant(type_id=4, name="كيس كرافت كبير", size="كبير",
                              size_details="32×14×42 سم", variant_type="يد ميرومة", min_quantity=300),
                
                # === أكياس بيضاء ===
                ProductVariant(type_id=5, name="كيس أبيض صغير", size="صغير",
                              size_details="20×10×28 سم", variant_type="يد ميرومة", min_quantity=500),
                ProductVariant(type_id=5, name="كيس أبيض وسط", size="وسط",
                              size_details="26×12×32 سم", variant_type="يد ميرومة", min_quantity=500),
                ProductVariant(type_id=5, name="كيس أبيض كبير", size="كبير",
                              size_details="32×14×42 سم", variant_type="يد ميرومة", min_quantity=300),
                
                # === علب البرجر ===
                ProductVariant(type_id=6, name="علبة برجر عادي", size="عادي",
                              size_details="10×10 سم", min_quantity=500),
                ProductVariant(type_id=6, name="علبة برجر جامبو", size="جامبو",
                              size_details="12×12 سم", min_quantity=500),
                
                # === ورق التغليف ===
                ProductVariant(type_id=7, name="ورق تغليف صغير", size="صغير",
                              size_details="25×35 سم", min_quantity=1000),
                ProductVariant(type_id=7, name="ورق تغليف كبير", size="كبير",
                              size_details="30×40 سم", min_quantity=1000),
                
                # === علب البيتزا ===
                ProductVariant(type_id=8, name="علبة بيتزا 25 سم", size="صغير",
                              size_details="25 سم", min_quantity=200),
                ProductVariant(type_id=8, name="علبة بيتزا 30 سم", size="وسط",
                              size_details="30 سم", min_quantity=200),
                ProductVariant(type_id=8, name="علبة بيتزا 35 سم", size="كبير",
                              size_details="35 سم", min_quantity=200),
                
                # === أكواب آيس كريم ===
                ProductVariant(type_id=10, name="كوب آيس كريم 4oz", size="4 oz",
                              min_quantity=500),
                ProductVariant(type_id=10, name="كوب آيس كريم 8oz", size="8 oz",
                              min_quantity=500),
            ]
            session.add_all(variants)
            session.commit()
            print("✅ Product variants added")
        
        # ============================================
        # إضافة الملحقات
        # ============================================
        if not session.query(Accessory).first():
            accessories = [
                Accessory(name="غطاء مسطح", name_en="Flat Lid", 
                         compatible_with="أكواب ساخنة", description="للمشروبات الساخنة"),
                Accessory(name="غطاء قبة", name_en="Dome Lid",
                         compatible_with="أكواب باردة", description="للكريمة والمخفوق"),
                Accessory(name="كم حراري", name_en="Sleeve",
                         compatible_with="أكواب ساخنة سنجل", description="حماية من الحرارة"),
                Accessory(name="حامل 2 كوب", name_en="2-Cup Holder",
                         compatible_with="أكواب", description="كرتون"),
                Accessory(name="حامل 4 أكواب", name_en="4-Cup Holder",
                         compatible_with="أكواب", description="كرتون"),
                Accessory(name="مزاز ورقي 6 ملم", name_en="Paper Straw 6mm",
                         compatible_with="أكواب باردة", description="للعصائر"),
                Accessory(name="مزاز ورقي 10 ملم", name_en="Paper Straw 10mm",
                         compatible_with="أكواب باردة", description="للسموذي"),
            ]
            session.add_all(accessories)
            session.commit()
            print("✅ Accessories added")
        
        print("✅ Database initialized with print shop catalog!")
    
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        session.rollback()
    
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_catalog_context():
    """Returns the full catalog as context for AI"""
    return PRINT_SHOP_CATALOG


if __name__ == "__main__":
    print("🔧 Initializing print shop database...")
    init_db()
