#!/usr/bin/env python3

import json
from typing import List, Dict, Optional
from dataclasses import dataclass
import ollama


@dataclass
class Action:
    type: str
    target: str


@dataclass
class Ingredient:
    name: str
    quantity: int
    category: str


@dataclass
class CartItem:
    product_id: str
    name: str
    quantity: int
    brand: str
    price: float
    category: str


class ActionAgent:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
    
    def parse(self, user_input: str) -> List[Action]:
        prompt = f"""Tu es un parser d'actions pour un assistant de courses.

TYPES D'ACTIONS: add, remove, view, validate, clear

RÈGLES STRICTES:
1. Le "target" doit être EXACTEMENT le texte mentionné par l'utilisateur, sans correction
2. N'invente AUCUN produit qui n'est pas explicitement demandé
3. Si l'utilisateur dit "je veux X", crée UNE SEULE action pour X
4. Ne rajoute JAMAIS d'actions non demandées

Retourne UNIQUEMENT un JSON array, rien d'autre.

EXEMPLES:
"je veux du lait" → [{{"type": "add", "target": "du lait"}}]
"enlève le chocolat" → [{{"type": "remove", "target": "le chocolat"}}]
"retire les pates" → [{{"type": "remove", "target": "les pates"}}]
"des pates et du lait" → [{{"type": "add", "target": "des pates"}}, {{"type": "add", "target": "du lait"}}]
"montre mon panier" → [{{"type": "view", "target": ""}}]

INPUT: "{user_input}"

JSON:"""

        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            text = response['response'].strip()
            
            start = text.find('[')
            end = text.rfind(']') + 1
            if start == -1 or end <= start:
                return []
            
            json_text = text[start:end].replace('\n', ' ')
            actions_data = json.loads(json_text)
            
            if not isinstance(actions_data, list):
                return []
            
            return [Action(type=a.get('type', 'add'), target=a.get('target', ''))
                   for a in actions_data if isinstance(a, dict)]
        except:
            return []


class IngredientAgent:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
    
    def parse(self, text: str) -> List[Ingredient]:
        prompt = f"""Tu extrais les ingrédients d'une demande de courses.

RÈGLES STRICTES:
1. Extrait UNIQUEMENT ce qui est mentionné dans le texte
2. N'invente RIEN
3. Si c'est une recette, décompose en ingrédients de base
4. Utilise quantity=1 si non spécifié

CATÉGORIES: pates, riz, lait, yaourt, fromage, viande, poisson, legume_frais, 
fruit_frais, sauce, chocolat, chips, biscuit, pain

Retourne UNIQUEMENT un JSON array valide, rien d'autre.

EXEMPLES:
"du lait" → [{{"name": "lait", "quantity": 1, "category": "lait"}}]
"2 bouteilles de lait" → [{{"name": "lait", "quantity": 2, "category": "lait"}}]
"des pates" → [{{"name": "pâtes", "quantity": 1, "category": "pates"}}]
"pâtes bolognaise" → [
  {{"name": "pâtes", "quantity": 1, "category": "pates"}},
  {{"name": "sauce tomate", "quantity": 1, "category": "sauce"}},
  {{"name": "viande hachée", "quantity": 1, "category": "viande"}}
]

INPUT: "{text}"

JSON:"""

        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            text = response['response'].strip()
            
            start = text.find('[')
            end = text.rfind(']') + 1
            if start == -1 or end <= start:
                return []
            
            json_text = text[start:end].replace('\n', ' ')
            ingredients_data = json.loads(json_text)
            
            if not isinstance(ingredients_data, list):
                return []
            
            return [Ingredient(
                name=i.get('name', ''),
                quantity=int(i.get('quantity', 1)),
                category=i.get('category', 'autres')
            ) for i in ingredients_data if isinstance(i, dict) and i.get('name')]
        except:
            return []
