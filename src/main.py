#!/usr/bin/env python3

from typing import List, Optional, Dict
from database import GroceryDB
from agents import ActionAgent, IngredientAgent, CartItem


class ShoppingAssistant:
    def __init__(self, user_id: str, db: GroceryDB, model: str = "llama3.2"):
        self.user_id = user_id
        self.db = db
        self.model = model
        self.user = db.get_user(user_id)
        self.cart: List[CartItem] = []
        
        self.action_agent = ActionAgent(model)
        self.ingredient_agent = IngredientAgent(model)
    
    def process(self, user_input: str):
        print(f"\n🧠 Analyse...")
        
        actions = self.action_agent.parse(user_input)
        if not actions:
            print("⚠️  Je n'ai pas compris. Reformulez ?")
            return
        
        # Validation: filter out hallucinated actions
        user_lower = user_input.lower()
        validated_actions = []
        for action in actions:
            if action.type in ["view", "validate", "clear"]:
                validated_actions.append(action)
            elif action.target:
                # Check if target keywords appear in user input
                target_words = action.target.lower().split()
                # Keep action if at least one word from target is in user input
                if any(word in user_lower for word in target_words if len(word) > 2):
                    validated_actions.append(action)
                else:
                    print(f"   ⚠️  Action ignorée (hallucination détectée): {action.type} → {action.target}")
        
        actions = validated_actions
        
        if not actions:
            print("⚠️  Aucune action valide détectée.")
            return
        
        print(f"🎯 Actions: {len(actions)}")
        for action in actions:
            print(f"   - {action.type.upper()}: {action.target}")
        
        for action in actions:
            if action.type == "add":
                self._add(action)
            elif action.type == "remove":
                self._remove(action)
            elif action.type == "view":
                self._view()
            elif action.type == "validate":
                self._validate()
            elif action.type == "clear":
                self._clear()
        
        if any(a.type in ["add", "remove"] for a in actions):
            print()
            self._view()
    
    def _add(self, action):
        print(f"   🔍 Parse: '{action.target}'")
        ingredients = self.ingredient_agent.parse(action.target)
        
        if not ingredients:
            print(f"   ⚠️  Aucun ingrédient trouvé")
            return
        
        print(f"   📝 {len(ingredients)} ingrédient(s):")
        for ing in ingredients:
            print(f"      - {ing.name} (x{ing.quantity}) [{ing.category}]")
        
        for ingredient in ingredients:
            self._add_ingredient(ingredient)
    
    def _add_ingredient(self, ingredient):
        products = self.db.semantic_search(
            query=ingredient.name,
            user_id=self.user_id,
            category=ingredient.category,
            limit=10
        )
        
        if not products:
            print(f"      ❌ Non trouvé: {ingredient.name}")
            return
        
        user_prefs = self.user.get('favorite_brands', {})
        preferred_brand = user_prefs.get(ingredient.category)
        
        selected = None
        if preferred_brand:
            for p in products:
                if p['brand'] == preferred_brand:
                    selected = p
                    print(f"      💡 Utilisation de votre marque préférée: {preferred_brand}")
                    break
        
        if not selected:
            if ingredient.category not in user_prefs and len(products) > 1:
                unique_brands = {}
                for p in products:
                    if p['brand'] not in unique_brands:
                        unique_brands[p['brand']] = p
                
                if len(unique_brands) > 1:
                    selected = self._ask_brand(ingredient.category, list(unique_brands.values())[:4])
                else:
                    selected = products[0]
            else:
                selected = products[0]
        
        if selected:
            cart_item = CartItem(
                product_id=selected['id'],
                name=selected['name'],
                quantity=ingredient.quantity,
                brand=selected['brand'],
                price=float(selected['price']),
                category=selected['category']
            )
            
            existing = next((item for item in self.cart if item.product_id == cart_item.product_id), None)
            
            if existing:
                existing.quantity += cart_item.quantity
                print(f"      ✓ Mis à jour: {cart_item.name} (total: {existing.quantity})")
            else:
                self.cart.append(cart_item)
                print(f"      ✓ Ajouté: {cart_item.name} ({cart_item.brand}) x{cart_item.quantity}")
    
    def _remove(self, action):
        matches = self.db.semantic_search_cart(action.target, self.cart)
        
        if matches:
            for match in matches:
                self.cart = [item for item in self.cart if item.product_id != match.product_id]
                print(f"   ✓ Retiré: {match.name} ({match.brand})")
        else:
            print(f"   ⚠️  Rien ne correspond à: {action.target}")
            if self.cart:
                print(f"   💡 Dans le panier:")
                for item in self.cart:
                    print(f"      - {item.name}")
    
    def _view(self):
        print("="*70)
        print("🛒 PANIER".center(70))
        print("="*70)
        
        if not self.cart:
            print("Vide.")
        else:
            total = 0.0
            for i, item in enumerate(self.cart, 1):
                subtotal = item.price * item.quantity
                total += subtotal
                print(f"{i}. {item.name} ({item.brand})")
                print(f"   Quantité: {item.quantity} | Prix: {item.price:.2f}€ | Sous-total: {subtotal:.2f}€")
            
            print("-"*70)
            print(f"TOTAL: {total:.2f}€".rjust(70))
        
        print("="*70)
    
    def _validate(self):
        if not self.cart:
            print("   ⚠️  Panier vide")
            return
        
        # Sauvegarder toutes les préférences du panier
        preferences_saved = 0
        for item in self.cart:
            current_pref = self.user.get('favorite_brands', {}).get(item.category)
            if current_pref != item.brand:
                self.db.update_user_preference(self.user_id, item.category, item.brand)
                preferences_saved += 1
        
        # Recharger les préférences
        if preferences_saved > 0:
            self.user = self.db.get_user(self.user_id)
            print(f"   ✓ {preferences_saved} préférence(s) sauvegardée(s)")
        
        total = sum(item.price * item.quantity for item in self.cart)
        print(f"   ✓ Commande validée!")
        print(f"   💰 Total: {total:.2f}€")
        print(f"   📦 {len(self.cart)} article(s)")
        
        self.cart.clear()
    
    def _clear(self):
        count = len(self.cart)
        self.cart.clear()
        print(f"   ✓ Panier vidé ({count} articles)")
    
    def _ask_brand(self, category: str, options: List[Dict]) -> Optional[Dict]:
        print(f"\n   ❓ Pas de préférence pour {category}. Quelle marque ?")
        
        for i, p in enumerate(options, 1):
            bio = " 🌱" if p.get('is_bio') else ""
            vegan = " 🌿" if p.get('is_vegan') else ""
            print(f"      {i}. {p['brand']} - {p['name']} ({p['price']:.2f}€){bio}{vegan}")
        
        print(f"      0. Peu importe (moins cher)")
        
        try:
            choice = input("   Votre choix: ").strip()
            if choice == "0":
                chosen = min(options, key=lambda p: p['price'])
            else:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    chosen = options[idx]
                else:
                    chosen = min(options, key=lambda p: p['price'])
            
            self.db.update_user_preference(self.user_id, category, chosen['brand'])
            self.user = self.db.get_user(self.user_id)  # Recharger les préférences
            print(f"   ✓ Préférence sauvegardée: {category} → {chosen['brand']}\n")
            return chosen
        except:
            return min(options, key=lambda p: p['price'])
    
    def run(self):
        print("\n" + "="*70)
        print("🛒 ASSISTANT COURSES".center(70))
        print("="*70)
        print(f"\n👋 Bonjour {self.user['name']}!")
        print("\n💡 Dites-moi ce que vous voulez.\n")
        
        while True:
            try:
                user_input = input("Vous: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quitter', 'exit', 'quit']:
                    print("\n👋 À bientôt!")
                    break
                
                self.process(user_input)
                print()
            except KeyboardInterrupt:
                print("\n\n👋 À bientôt!")
                break
            except Exception as e:
                print(f"⚠️  Erreur: {e}")
        
        self.db.close()


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <user_id> [--model MODEL_NAME]")
        print("\nUsers disponibles: user_alice, user_bob, user_clara")
        print("\nModèles recommandés (du meilleur au plus rapide):")
        print("  - mistral-nemo    (12B, excellent français + parsing)")
        print("  - qwen2.5:14b     (14B, excellent pour JSON structuré)")
        print("  - mistral         (7B, bon compromis)")
        print("  - mixtral         (47B, top tier mais lourd)")
        print("  - llama3.1        (8B, fallback solide)")
        print("  - llama3.2        (3B, rapide mais moins fiable)")
        print("\nExemple: python src/main.py user_alice --model mistral-nemo")
        sys.exit(1)
    
    user_id = sys.argv[1]
    model = "llama3.2"
    
    if "--model" in sys.argv:
        model_idx = sys.argv.index("--model")
        if model_idx + 1 < len(sys.argv):
            model = sys.argv[model_idx + 1]
            print(f"🤖 Modèle sélectionné: {model}")
    else:
        print(f"ℹ️  Modèle par défaut: {model} (utilisez --model pour changer)")
    
    db = GroceryDB()
    assistant = ShoppingAssistant(user_id, db, model=model)
    assistant.run()


if __name__ == "__main__":
    main()
