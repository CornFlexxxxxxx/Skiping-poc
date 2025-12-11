#!/usr/bin/env python3

import json
import sqlite3
from typing import List, Dict, Optional
from pathlib import Path

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️  ChromaDB non installé. Recherche sémantique désactivée.")


class GroceryDB:
    def __init__(self, db_path: str = "grocery.db", use_semantic: bool = True):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self.use_semantic = use_semantic and CHROMADB_AVAILABLE
        if self.use_semantic:
            self._init_chromadb()
        
    def _init_chromadb(self):
        try:
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
            self.products_collection = self.chroma_client.get_or_create_collection(name="products")
            print("✓ ChromaDB initialisé")
        except Exception as e:
            print(f"⚠️  Erreur ChromaDB: {e}")
            self.use_semantic = False
    
    def initialize_from_json(self, products_json: str, users_json: str):
        self._create_tables()
        
        with open(products_json, 'r', encoding='utf-8') as f:
            products = json.load(f)
        self._insert_products(products)
        
        with open(users_json, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        self._insert_users(users_data['users'])
        
        if self.use_semantic:
            self._build_semantic_index(products)
        
        print(f"✓ Base initialisée: {len(products)} produits, {len(users_data['users'])} utilisateurs")
    
    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                is_bio BOOLEAN,
                is_vegan BOOLEAN,
                is_available BOOLEAN
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                bio_preference BOOLEAN,
                vegan_preference BOOLEAN
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT,
                category TEXT,
                brand TEXT,
                PRIMARY KEY (user_id, category)
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_dislikes (
                user_id TEXT,
                brand TEXT,
                PRIMARY KEY (user_id, brand)
            )
        """)
        
        self.conn.commit()
    
    def _insert_products(self, products: List[Dict]):
        for p in products:
            self.cursor.execute("""
                INSERT OR REPLACE INTO products 
                (id, name, brand, category, price, is_bio, is_vegan, is_available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (p['id'], p['name'], p['brand'], p['category'], p['price'],
                  p.get('is_bio', False), p.get('is_vegan', False), p.get('is_available', True)))
        self.conn.commit()
    
    def _build_semantic_index(self, products: List[Dict]):
        if self.products_collection.count() > 0:
            print(f"✓ Index sémantique déjà présent")
            return
        
        print("Construction de l'index sémantique...")
        documents = []
        metadatas = []
        ids = []
        
        for p in products:
            doc = f"{p['name']} {p['brand']} {p['category']}"
            if p.get('is_bio'):
                doc += " bio biologique"
            if p.get('is_vegan'):
                doc += " vegan végétalien"
            
            documents.append(doc)
            metadatas.append({"product_id": p['id'], "category": p['category']})
            ids.append(p['id'])
        
        self.products_collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"✓ Index créé avec {len(products)} produits")
    
    def _insert_users(self, users: List[Dict]):
        for u in users:
            prefs = u['preferences']
            
            self.cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, name, bio_preference, vegan_preference)
                VALUES (?, ?, ?, ?)
            """, (u['user_id'], u['name'], prefs.get('bio', False), prefs.get('vegan', False)))
            
            for category, brand in u.get('favorite_brands', {}).items():
                self.cursor.execute("""
                    INSERT OR REPLACE INTO user_preferences (user_id, category, brand)
                    VALUES (?, ?, ?)
                """, (u['user_id'], category, brand))
            
            for brand in u.get('dislikes', []):
                self.cursor.execute("""
                    INSERT OR REPLACE INTO user_dislikes (user_id, brand)
                    VALUES (?, ?)
                """, (u['user_id'], brand))
        
        self.conn.commit()
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = self.cursor.fetchone()
        
        if not user_row:
            return None
        
        user = dict(user_row)
        
        self.cursor.execute("SELECT category, brand FROM user_preferences WHERE user_id = ?", (user_id,))
        user['favorite_brands'] = {row['category']: row['brand'] for row in self.cursor.fetchall()}
        
        self.cursor.execute("SELECT brand FROM user_dislikes WHERE user_id = ?", (user_id,))
        user['dislikes'] = [row['brand'] for row in self.cursor.fetchall()]
        
        return user
    
    def update_user_preference(self, user_id: str, category: str, brand: str):
        self.cursor.execute("""
            INSERT OR REPLACE INTO user_preferences (user_id, category, brand)
            VALUES (?, ?, ?)
        """, (user_id, category, brand))
        self.conn.commit()
    
    def semantic_search(self, query: str, user_id: Optional[str] = None, 
                       category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        if not self.use_semantic:
            return self._basic_search(query, user_id, category, limit)
        
        where = {"category": category} if category else None
        results = self.products_collection.query(
            query_texts=[query],
            n_results=min(limit * 3, 50),
            where=where
        )
        
        if not results['ids'] or not results['ids'][0]:
            return []
        
        products = [self._get_product_by_id(pid) for pid in results['ids'][0]]
        products = [p for p in products if p]
        
        if user_id:
            products = self._filter_by_user_prefs(products, user_id)
        
        return products[:limit]
    
    def _basic_search(self, query: str, user_id: Optional[str] = None,
                     category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        sql = "SELECT * FROM products WHERE is_available = 1"
        params = []
        
        if query:
            sql += " AND (name LIKE ? OR brand LIKE ? OR category LIKE ?)"
            search = f"%{query}%"
            params.extend([search, search, search])
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        user = self.get_user(user_id) if user_id else None
        if user:
            if user['dislikes']:
                placeholders = ','.join('?' * len(user['dislikes']))
                sql += f" AND brand NOT IN ({placeholders})"
                params.extend(user['dislikes'])
            
            if user.get('vegan_preference'):
                sql += " AND is_vegan = 1"
        
        sql += " ORDER BY price ASC LIMIT ?"
        params.append(limit)
        
        self.cursor.execute(sql, params)
        return [dict(row) for row in self.cursor.fetchall()]
    
    def _filter_by_user_prefs(self, products: List[Dict], user_id: str) -> List[Dict]:
        user = self.get_user(user_id)
        if not user:
            return products
        
        if user['dislikes']:
            products = [p for p in products if p['brand'] not in user['dislikes']]
        
        if user.get('vegan_preference'):
            products = [p for p in products if p.get('is_vegan')]
        
        favorite_brands = user.get('favorite_brands', {})
        
        def sort_key(p):
            is_preferred = p['brand'] == favorite_brands.get(p['category'])
            return (not is_preferred, p['price'])
        
        products.sort(key=sort_key)
        return products
    
    def semantic_search_cart(self, query: str, cart_items: List) -> List:
        if not cart_items:
            return []
        
        if not self.use_semantic:
            query_lower = query.lower()
            return [item for item in cart_items 
                   if query_lower in item.name.lower() or 
                      query_lower in item.category.lower() or 
                      query_lower in item.brand.lower()]
        
        temp_collection = self.chroma_client.get_or_create_collection(name="temp_cart")
        
        try:
            if temp_collection.count() > 0:
                all_ids = temp_collection.get()['ids']
                if all_ids:
                    temp_collection.delete(ids=all_ids)
        except:
            pass
        
        documents = [f"{item.name} {item.brand} {item.category}" for item in cart_items]
        temp_collection.add(
            documents=documents,
            ids=[f"cart_{i}" for i in range(len(cart_items))],
            metadatas=[{"index": i} for i in range(len(cart_items))]
        )
        
        results = temp_collection.query(query_texts=[query], n_results=min(5, len(cart_items)))
        
        matches = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata in results['metadatas'][0]:
                matches.append(cart_items[metadata['index']])
        
        return matches
    
    def _get_product_by_id(self, product_id: str) -> Optional[Dict]:
        self.cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def close(self):
        self.conn.close()


def main():
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python database.py <products.json> <users.json>")
        sys.exit(1)
    
    db = GroceryDB()
    db.initialize_from_json(sys.argv[1], sys.argv[2])
    db.close()


if __name__ == "__main__":
    main()
