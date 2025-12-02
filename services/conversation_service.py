"""
Conversation Service - Manages conversation state and flow
إدارة حالة المحادثة مع كل عميل
"""
from typing import Dict, Optional, List, Any

try:
    from sqlalchemy.orm import Session
except ImportError:  # pragma: no cover - fallback for environments without SQLAlchemy
    class _QueryStub:
        def filter(self, *args: Any, **kwargs: Any) -> "_QueryStub":
            return self

        def all(self) -> List[Any]:
            return []

        def first(self) -> Any:
            return None

        def get(self, *_args: Any, **_kwargs: Any) -> Any:
            return None

    class Session:  # type: ignore
        def query(self, *_args: Any, **_kwargs: Any) -> _QueryStub:
            return _QueryStub()

        def add(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def commit(self) -> None:
            return None

        def refresh(self, *_args: Any, **_kwargs: Any) -> None:
            return None
from database import ConversationState, ProductCategory, ProductType, ProductVariant, Accessory
from datetime import datetime


class ConversationManager:
    """
    Manages the conversation flow with customers
    Tracks state and determines next steps
    """
    
    STEPS = [
        "greeting",      # الترحيب
        "category",      # اختيار الفئة (أكواب/أكياس/علب)
        "type",          # اختيار النوع (ساخن/بارد)
        "size",          # اختيار الحجم
        "variant",       # اختيار المتغير (سنجل/دبل)
        "quantity",      # تحديد الكمية
        "accessories",   # الملحقات (اختياري)
        "confirm",       # تأكيد الطلب
        "invoice"        # إصدار الفاتورة
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_or_create_state(self, phone_number: str) -> ConversationState:
        """Get existing conversation state or create new one"""
        state = self.db.query(ConversationState).filter(
            ConversationState.phone_number == phone_number
        ).first()
        
        if not state:
            state = ConversationState(
                phone_number=phone_number,
                current_step="greeting"
            )
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        
        return state
    
    def update_state(self, phone_number: str, **kwargs) -> ConversationState:
        """Update conversation state"""
        state = self.get_or_create_state(phone_number)
        
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        state.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(state)
        
        return state
    
    def reset_state(self, phone_number: str) -> ConversationState:
        """Reset conversation to start"""
        state = self.get_or_create_state(phone_number)
        
        state.current_step = "greeting"
        state.selected_category_id = None
        state.selected_type_id = None
        state.selected_variant_id = None
        state.selected_quantity = None
        state.selected_accessories = None
        state.notes = None
        state.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(state)
        
        return state
    
    def get_next_step(self, current_step: str) -> str:
        """Get the next step in conversation flow"""
        try:
            current_index = self.STEPS.index(current_step)
            if current_index < len(self.STEPS) - 1:
                return self.STEPS[current_index + 1]
        except ValueError:
            pass
        return "greeting"
    
    def generate_step_message(self, state: ConversationState) -> str:
        """Generate appropriate message for current step"""
        
        if state.current_step == "greeting":
            return self._greeting_message()
        
        elif state.current_step == "category":
            return self._category_message()
        
        elif state.current_step == "type":
            return self._type_message(state.selected_category_id)
        
        elif state.current_step == "size":
            return self._size_message(state.selected_type_id)
        
        elif state.current_step == "variant":
            return self._variant_message(state.selected_type_id)
        
        elif state.current_step == "quantity":
            return self._quantity_message(state)
        
        elif state.current_step == "confirm":
            return self._confirm_message(state)
        
        return "كيف يمكنني مساعدتك؟"
    
    def _greeting_message(self) -> str:
        base_greeting = (
            "أهلاً بك! نحن هنا لتحويل فكرتك إلى واقع. في أي طلب، يمكنك كتابة ملاحظاتك الدقيقة إذا كنت "
            "تفضل شيئاً خاصاً بالتصميم، مثل: 'أريد حبل الكيس مخفياً من الداخل' أو 'استبداله بشريطة حمراء'. "
            "أنا أفهم طلبك جيداً، وجميع ملاحظاتك ستؤخذ بعين الاعتبار بدقة، فلا تقلق."
        )
        identity_line = "أنا وكيل المبيعات لدى مطبعة خالد الحسن، ومستعد أخدمك من البداية للنهاية."
        follow_up = (
            "هل تود أن نبدأ الآن بتحديد نوع المنتج أو المواد التي تفكر بها؟ أرسل لي أي تفاصيل موجودة عندك وسأرتبها لك."
        )
        return f"{base_greeting}\n{identity_line}\n{follow_up}"
    
    def _category_message(self) -> str:
        categories: List[ProductCategory] = self.db.query(ProductCategory).all()
        
        msg = "اختر القسم:\n\n"
        for i, cat in enumerate(categories, 1):
            msg += f"{cat.icon} {i}. {cat.name}\n"
        
        return msg
    
    def _type_message(self, category_id: int) -> str:
        types = self.db.query(ProductType).filter(
            ProductType.category_id == category_id
        ).all()
        
        if not types:
            return "عذراً، لا توجد منتجات في هذا القسم حالياً."
        
        msg = "اختر النوع:\n\n"
        for i, t in enumerate(types, 1):
            material = f" ({t.material})" if t.material else ""
            msg += f"{i}. {t.name}{material}\n"
        
        return msg
    
    def _size_message(self, type_id: int) -> str:
        variants = self.db.query(ProductVariant).filter(
            ProductVariant.type_id == type_id
        ).all()
        
        # Get unique sizes
        sizes = {}
        for v in variants:
            if v.size and v.size not in sizes:
                details = f" ({v.size_details})" if v.size_details else ""
                sizes[v.size] = details
        
        if not sizes:
            return "ما هو الحجم المطلوب؟"
        
        msg = "📏 اختر الحجم:\n\n"
        for i, (size, details) in enumerate(sizes.items(), 1):
            msg += f"{i}. {size}{details}\n"
        
        return msg
    
    def _variant_message(self, type_id: int) -> str:
        variants = self.db.query(ProductVariant).filter(
            ProductVariant.type_id == type_id
        ).all()
        
        # Get unique variant types
        variant_types = set()
        for v in variants:
            if v.variant_type:
                variant_types.add(v.variant_type)
        
        if not variant_types:
            return None  # Skip this step
        
        msg = "اختر النوع:\n\n"
        for i, vt in enumerate(variant_types, 1):
            # Add descriptions
            if "مزدوج" in vt or "دبل" in vt:
                msg += f"{i}. {vt} (فاخر - عزل حراري عالي) ⭐\n"
            elif "واحد" in vt or "سنجل" in vt:
                msg += f"{i}. {vt} (اقتصادي)\n"
            elif "مموج" in vt:
                msg += f"{i}. {vt} (فخم - ملمس بارز) ✨\n"
            else:
                msg += f"{i}. {vt}\n"
        
        return msg
    
    def _quantity_message(self, state: ConversationState) -> str:
        # Get min quantity for selected variant
        min_qty = 500  # default
        
        if state.selected_variant_id:
            variant = self.db.query(ProductVariant).filter(
                ProductVariant.id == state.selected_variant_id
            ).first()
            if variant:
                min_qty = variant.min_quantity
        
        return f"""
🔢 كم الكمية المطلوبة؟

📌 الحد الأدنى للطلب: {min_qty} قطعة
💡 كلما زادت الكمية، انخفض سعر الوحدة
"""
    
    def _confirm_message(self, state: ConversationState) -> str:
        summary = self.build_final_summary(state)
        summary += "\n\nهذا هو ملخص طلبك النهائي.\n\nهل أنت موافق على هذا الطلب؟\nاكتب: موافق / تعديل / إلغاء"
        return summary

    def build_final_summary(self, state: ConversationState) -> str:
        """Build a human-readable final order summary from state"""
        lines: List[str] = ["📋 ملخص طلبك النهائي:", ""]

        # Category / type
        if state.selected_category_id:
            category = self.db.query(ProductCategory).get(state.selected_category_id)
            if category:
                lines.append(f"🗂 القسم: {category.name}")

        if state.selected_type_id:
            ptype = self.db.query(ProductType).get(state.selected_type_id)
            if ptype:
                material = f" ({ptype.material})" if ptype.material else ""
                lines.append(f"📄 النوع: {ptype.name}{material}")

        # Variant
        if state.selected_variant_id:
            variant = self.db.query(ProductVariant).get(state.selected_variant_id)
            if variant:
                lines.append(f"📦 المنتج: {variant.name}")
                if variant.size_details:
                    lines.append(f"📏 المقاس: {variant.size_details}")
                elif variant.size:
                    lines.append(f"📏 المقاس: {variant.size}")
                if variant.variant_type:
                    lines.append(f"⚙️ النوع: {variant.variant_type}")

        # Quantity
        if state.selected_quantity:
            lines.append(f"🔢 الكمية: {state.selected_quantity}")

        # Accessories
        if state.selected_accessories:
            lines.append("➕ الملحقات:")
            for acc in state.selected_accessories:
                name = acc.get("name") or acc.get("id")
                qty = acc.get("qty")
                if name and qty:
                    lines.append(f"  • {name} × {qty}")

        # Notes
        if state.notes:
            lines.append("")
            lines.append(f"📝 ملاحظات العميل: {state.notes}")

        lines.append("")
        lines.append("💰 السعر: سيتم تحديده من قبل إدارة مطبعة خالد الحسن بعد مراجعة الإمكانية.")

        return "\n".join(lines)
    
    def find_matching_variant(self, type_id: int, size: str = None, variant_type: str = None) -> Optional[ProductVariant]:
        """Find variant matching the given criteria"""
        query = self.db.query(ProductVariant).filter(
            ProductVariant.type_id == type_id,
            ProductVariant.is_available == True
        )
        
        if size:
            query = query.filter(ProductVariant.size.like(f"%{size}%"))
        
        if variant_type:
            query = query.filter(ProductVariant.variant_type.like(f"%{variant_type}%"))
        
        return query.first()
    
    def get_order_summary(self, state: ConversationState) -> Dict:
        """Get full order details from state"""
        result = {
            "category": None,
            "type": None,
            "variant": None,
            "quantity": state.selected_quantity,
            "accessories": state.selected_accessories,
            "customer_name": state.customer_name
        }
        
        if state.selected_category_id:
            cat = self.db.query(ProductCategory).get(state.selected_category_id)
            if cat:
                result["category"] = cat.name
        
            base_greeting = (
                "أهلاً بك! نحن هنا لتحويل فكرتك إلى واقع. في أي طلب، يمكنك كتابة ملاحظاتك الدقيقة إذا كنت "
                "تفضل شيئاً خاصاً بالتصميم، مثل: 'أريد حبل الكيس مخفياً من الداخل' أو 'استبداله بشريطة حمراء'. "
                "أنا أفهم طلبك جيداً، وجميع ملاحظاتك ستؤخذ بعين الاعتبار بدقة، فلا تقلق."
            )
            identity_line = "أنا وكيل المبيعات لدى مطبعة خالد الحسن، ومستعد أخدمك من البداية للنهاية."
            follow_up = (
                "هل تود أن نبدأ الآن بتحديد نوع المنتج أو المواد التي تفكر بها؟ أرسل لي أي تفاصيل موجودة عندك وسأرتبها لك."
            )
            return f"{base_greeting}\n{identity_line}\n{follow_up}"
        
        if state.selected_variant_id:
            variant = self.db.query(ProductVariant).get(state.selected_variant_id)
            if variant:
                result["variant"] = {
                    "name": variant.name,
                    "size": variant.size,
                    "size_details": variant.size_details,
                    "variant_type": variant.variant_type,
                    "min_quantity": variant.min_quantity
                }
        
        return result
