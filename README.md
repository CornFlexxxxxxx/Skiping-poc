# Skiping POC - Assistant de Courses Multi-Agent

## Qu'est-ce que c'est ?

Un prototype d'assistant de courses utilisant plusieurs LLM spécialisés pour transformer une demande en langage naturel en panier de courses personnalisé.

## Architecture

```
┌─────────────────┐
│  Utilisateur    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ActionAgent    │  Parse l'intention (ajouter, retirer, voir...)
│   (LLM 1)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ IngredientAgent │  Décompose en ingrédients + quantités
│   (LLM 2)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Orchestrator  │  Recherche les produits, applique les préférences
│  (Python pur)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Database       │  SQLite + ChromaDB (recherche sémantique)
└─────────────────┘
```

## Ce que ça fait

### ✅ Fonctionnalités implémentées

**Compréhension du langage naturel**
- "je veux du lait" → Ajoute du lait au panier
- "enlève le chocolat" → Retire le chocolat du panier
- "pâtes bolognaise" → Décompose en pâtes + sauce tomate + viande hachée

**Recherche sémantique**
- Utilise ChromaDB pour comprendre les synonymes et variations
- "enlève le lait" trouve "Lait Écrémé Carrefour 1L"
- Pas besoin de mots-clés exacts

**Gestion des préférences utilisateur**
- Mémorise les marques préférées par catégorie
- **Apprentissage automatique** : 
  - 1ère fois : pose des questions pour choisir les marques
  - 2ème fois : utilise directement tes préférences (zéro question)
  - Sauvegarde à la validation du panier
- Exclut les marques non désirées
- Respecte les régimes (vegan, bio)

**Interface CLI conversationnelle**
- Interaction en français naturel
- Affichage clair du panier
- Actions : ajouter, retirer, voir, valider, vider

### ⚠️ Limitations actuelles

- **Pas d'API réelles** : Base de données mockée
- **Pas de patterns d'achat** : "chips → guacamole" non implémenté
- **CLI uniquement** : Pas d'interface graphique

## Installation

### Prérequis
- Python 3.10+
- Ollama installé
- **Modèle LLM recommandé** :
  - `mistral-nemo` (12B) - **RECOMMANDÉ** pour français + parsing JSON
  - `qwen2.5:14b` (14B) - Excellent pour tâches structurées
  - `mistral` (7B) - Bon compromis vitesse/qualité
  - `mixtral` (47B) - Meilleur mais nécessite >32GB RAM
  - `llama3.1` (8B) - Fallback solide
  - `llama3.2` (3B) - Rapide mais hallucinations fréquentes ⚠️

### Setup

```bash
# Installer les dépendances
pip install -r requirements.txt

# Télécharger le modèle (RECOMMANDÉ)
ollama pull mistral-nemo

# Initialiser la base de données
python src/database.py data/products.json data/users.json

# Lancer l'assistant
python src/main.py user_alice --model mistral-nemo
```

**Note importante** : `llama3.2` (modèle par défaut) a tendance à halluciner. Utilisez `mistral-nemo` ou `qwen2.5:14b` pour de meilleurs résultats.

## Utilisation

```bash
# Avec le meilleur modèle (recommandé)
$ ollama pull mistral-nemo
$ python src/main.py user_alice --model mistral-nemo

# Ou avec qwen si mistral n'est pas disponible
$ ollama pull qwen2.5:14b
$ python src/main.py user_alice --model qwen2.5:14b

# Voir tous les modèles disponibles
$ python src/main.py
```

## Exemple réel (sur mon pc):

```bash
~/gabrielmonteillard/skiping-poc ❯ python src/main.py user_alice --model mistral-nemo

🤖 Modèle sélectionné: mistral-nemo
✓ ChromaDB initialisé

======================================================================
                         🛒 ASSISTANT COURSES                          
======================================================================

👋 Bonjour Alice!

💡 Dites-moi ce que vous voulez.

Vous: pâtes bolognaise

🧠 Analyse...
⚠️  Je n'ai pas compris. Reformulez ?

Vous: pates bolognaise

🧠 Analyse...
🎯 Actions: 1
   - ADD: pates bolognaise
   🔍 Parse: 'pates bolognaise'
   📝 3 ingrédient(s):
      - pâtes (x1) [pates]
      - sauce tomate (x1) [sauce]
      - viande hachée (x1) [viande]
      💡 Utilisation de votre marque préférée: Carrefour
      ✓ Ajouté: Coquillettes Carrefour 500g (Carrefour) x1

   ❓ Pas de préférence pour sauce. Quelle marque ?
      1. Carrefour - Mayonnaise Carrefour 235g (1.29€)
      2. Panzani - Tomate Panzani 400g (1.49€)
      3. Barilla - Tomate Barilla 400g (1.89€)
      4. Amora - Ketchup Amora 300g (1.99€)
      0. Peu importe (moins cher)
   Votre choix: 3
   ✓ Préférence sauvegardée: sauce → Barilla

      ✓ Ajouté: Tomate Barilla 400g (Barilla) x1

   ❓ Pas de préférence pour viande. Quelle marque ?
      1. Carrefour - Lardons Carrefour 200g (1.79€)
      2. Herta - Lardons Herta 200g (2.49€)
      3. Fleury Michon - Jambon Fleury Michon x4 (3.29€)
      4. Charal - Boeuf Hache Charal 350g (5.99€)
      0. Peu importe (moins cher)
   Votre choix: 4
   ✓ Préférence sauvegardée: viande → Charal

      ✓ Ajouté: Boeuf Hache Charal 350g (Charal) x1

======================================================================
                               🛒 PANIER                               
======================================================================
1. Coquillettes Carrefour 500g (Carrefour)
   Quantité: 1 | Prix: 0.79€ | Sous-total: 0.79€
2. Tomate Barilla 400g (Barilla)
   Quantité: 1 | Prix: 1.89€ | Sous-total: 1.89€
3. Boeuf Hache Charal 350g (Charal)
   Quantité: 1 | Prix: 5.99€ | Sous-total: 5.99€
----------------------------------------------------------------------
                                                          TOTAL: 8.67€
======================================================================

Vous: valide

🧠 Analyse...
🎯 Actions: 1
   - VALIDATE: 
   ✓ Commande validée!
   💰 Total: 8.67€
   📦 3 article(s)

Vous: pate bolognaise

🧠 Analyse...
🎯 Actions: 1
   - ADD: pâte bolognaise
   🔍 Parse: 'pâte bolognaise'
   📝 3 ingrédient(s):
      - pâtes (x1) [pates]
      - sauce tomate (x1) [sauce]
      - viande hachée (x1) [viande]
      💡 Utilisation de votre marque préférée: Carrefour
      ✓ Ajouté: Coquillettes Carrefour 500g (Carrefour) x1
      💡 Utilisation de votre marque préférée: Barilla
      ✓ Ajouté: Tomate Barilla 400g (Barilla) x1
      💡 Utilisation de votre marque préférée: Charal
      ✓ Ajouté: Boeuf Hache Charal 350g (Charal) x1

======================================================================
                               🛒 PANIER                               
======================================================================
1. Coquillettes Carrefour 500g (Carrefour)
   Quantité: 1 | Prix: 0.79€ | Sous-total: 0.79€
2. Tomate Barilla 400g (Barilla)
   Quantité: 1 | Prix: 1.89€ | Sous-total: 1.89€
3. Boeuf Hache Charal 350g (Charal)
   Quantité: 1 | Prix: 5.99€ | Sous-total: 5.99€
----------------------------------------------------------------------
                                                          TOTAL: 8.67€
======================================================================

Vous: ^C

👋 À bientôt!
```

## Fichiers

```
skiping-poc/
├── data/
│   ├── products.json    # Base de produits mockée
│   └── users.json       # Utilisateurs avec préférences
├── src/
│   ├── database.py          # Gestion DB (SQLite + ChromaDB)
│   └── agents.py            # LLM agents (action + ingrédients)
│   └── main.py              # Orchestrateur principal
├── NOTES_DEVELOPPEMENT.md
└── README.md
```

## Améliorations court terme

**Technique**
- Utiliser LangChain pour mieux structurer les agents
- Ajouter un cache pour les embeddings
- Implémenter un système de retries pour les LLM
- Parser les réponses avec Pydantic pour plus de robustesse

**Fonctionnel**
- Détecter les patterns d'achat (chips → guacamole)
- Mode vocal (speech-to-text)
- Suggestions proactives ("Tu as oublié le beurre")
- Comparaison de prix entre enseignes
- Interface web (Streamlit ou React)

**Data**
- Connecter aux vraies API Drive (Carrefour, Leclerc...)
- Enrichir la base produits
- Historique des achats pour mieux apprendre

## Approche de développement

### V1 - UI First (abandonnée)
Premier essai trop axé sur l'interface avant d'avoir un système fonctionnel. Code couplé, difficile à modifier.

### V2 - CLI + Multi-Agent (actuelle)
Reprise à zéro avec focus sur :
- **CLI simple** pour tester rapidement
- **Architecture multi-agent** : chaque LLM a un rôle précis
- **Recherche sémantique** pour éviter les hallucinations produits
- **Base de données mockée** mais structure réaliste

**Choix techniques**
- **2 LLM spécialisés** plutôt qu'un seul généraliste
  - ActionAgent : parse l'intention utilisateur
  - IngredientAgent : décompose en ingrédients
- **Orchestrateur en Python pur** : pas besoin d'IA pour la logique métier
- **ChromaDB** : recherche sémantique sans avoir à gérer les embeddings manuellement
- **SQLite** : stockage simple, pas de serveur

**Défis rencontrés**
- Faire sortir du JSON propre des LLM (parsing fragile)
- Équilibrer entre "demander les préférences" et "deviner intelligemment"
- Gérer les produits non trouvés sans inventer

**Ce qui marche bien**
- Décomposition "pâtes bolognaise" en ingrédients
- Recherche sémantique robuste
- Mémorisation des marques préférées
- CLI rapide pour tester
