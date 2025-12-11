# Notes de Développement

## Timeline

**Lundi soir** : Réflexion sur l'implémentation, analyse des problèmes utilisateurs  
**Mardi soir** : Premier essai - vibe coding, exploration des techs (ChromaDB, Ollama, multi-agents)  
**Mercredi soir** : Remise à zéro complète, implémentation finale, tests modèles  

Total : ~3 soirées de dev

## Itération 1 : UI-First (échec)

**Ce que j'ai fait** : Interface graphique d'abord, IA comme feature secondaire

**Pourquoi ça a foiré** :
- Trop de temps sur des détails visuels
- Impossible de tester les agents rapidement
- Code couplé, difficile à modifier

**Leçon** : Toujours valider le core technique avant de faire joli.

## Itération 2 : CLI + Multi-Agent (actuel)

Remise à zéro complète avec une base solide.

### Architecture

```
User Input → ActionAgent (LLM) → IngredientAgent (LLM) → Orchestrator (Python) → DB
```

**Choix clés** :
- **2 LLM spécialisés** : chacun fait une tâche simple (parse action OU parse ingrédients)
- **Orchestrateur Python** : pas besoin d'IA pour la logique métier
- **ChromaDB** : recherche sémantique = anti-hallucination ("pates" trouve "Pâtes Barilla")
- **SQLite** : données structurées (prix, préférences)

### Problèmes résolus

**Hallucinations LLM**
- Problème : "je veux des pates" → le LLM ajoute "du lait" de nulle part
- Solution 1 : Prompts avec règles strictes ("N'invente RIEN")
- Solution 2 : Validation Python (vérifie que les mots-clés sont dans l'input)
- **Solution 3 : Changer de modèle** → `llama3.2` hallucine beaucoup, `mistral-nemo` quasi zéro hallucination

**Produits inventés**
- Le LLM ne nomme jamais les produits, il cherche juste dans la DB
- Recherche sémantique trouve le bon produit même avec fautes/synonymes

**Préférences**
- Bug initial : sauvegardées en DB mais pas rechargées
- Fix : `self.user = self.db.get_user()` après chaque update
- Résultat : 1ère fois = questions, 2ème fois = automatique

### Impact du choix de modèle

**Tests réalisés** :
- `llama3.2` (3B) : Rapide mais hallucine énormément
- `llama3.1` (8B) : Mieux mais pas stable
- **`mistral-nemo` (12B)** : Quasi parfait, excellent français
- `qwen2.5:14b` : Très bon aussi pour parsing JSON

**Différence concrète** :
```
llama3.2  : "je veux des pates" → ajoute pates + lait (???)
mistral   : "je veux des pates" → ajoute pates uniquement ✓
```

Le modèle fait toute la différence. Avec un bon modèle, le système fonctionne presque parfaitement.

## Résultat final

**Ce qui marche** :
- Décomposition naturelle : "pâtes bolognaise" → 4 ingrédients
- Recherche sémantique robuste
- Apprentissage progressif des préférences
- Zéro hallucination avec `mistral-nemo`

**Limitations** :
- Pas d'API réelles (DB mockée)
- Pas de patterns d'achat ("chips → guacamole")
- CLI uniquement

**Améliorations court terme** :
- LangChain pour structurer les agents
- Pydantic pour valider outputs LLM
- Cache embeddings
- Interface web (Streamlit)

## Réflexion

**Pourquoi CLI** : Feedback immédiat, facile à débugger, pas de distractions

**Multi-agent** : Simple à tester, facile d'ajouter des agents, mais plus d'appels LLM

**ChromaDB** : Game changer pour éviter les hallucinations produits

**Le truc important** : Le choix du modèle LLM impacte plus que n'importe quelle optimisation de code. Un bon modèle (Mistral) > 100 lignes de validation Python.

## Conclusion

POC fonctionnel en 3 soirées. L'architecture multi-agent + recherche sémantique fonctionne. Le gros apprentissage : **tester plusieurs modèles LLM avant d'optimiser le code**.