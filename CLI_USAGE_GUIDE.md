# Guide d'Utilisation du CLI VoiceBot

## 📋 Vue d'Ensemble

Le CLI VoiceBot permet de tester les agents vocaux directement depuis le terminal, sans passer par l'interface web. Deux modes sont disponibles :

- **Mode Texte** (`--mode text`) : Interface conversationnelle texte uniquement
- **Mode Audio Complet** (`--mode full`) : Audio bidirectionnel via LiveKit WebRTC

**Important** : Le CLI s'exécute localement sur votre machine, pas dans Docker.

## 🚀 Installation et Démarrage

### 1. Prérequis

- **Python 3.9+** installé localement
- **UV** (recommandé) ou **pip** pour la gestion des dépendances
- **Docker** pour l'infrastructure backend

### 2. Installation avec UV (Recommandé)

```bash
# Installer uv si pas déjà installé
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances du CLI
uv sync

# Alternative : installer en mode développement
uv sync --dev
```

### 3. Démarrer l'Infrastructure Backend

```bash
# Démarrer tous les services (y compris LiveKit)
docker compose up -d

# Vérifier que tout fonctionne
docker compose ps
```

### 4. Utiliser le CLI

#### Mode Texte (Recommandé pour les tests rapides)

```bash
# Avec uv (recommandé)
uv run voicebot-cli --agent-name "etienne" --mode text

# Alternative avec python
python -m src.cli.main --agent-name "etienne" --mode text

# Avec logging détaillé
uv run voicebot-cli --agent-name "etienne" --mode text --verbose
```

#### Mode Audio Complet (LiveKit WebRTC)

```bash
# Tester avec audio via LiveKit
uv run voicebot-cli --agent-name "etienne" --mode full

# Avec nom de salle personnalisé
uv run voicebot-cli --agent-name "etienne" --mode full --room-name "test-conversation"
```

## 🎯 Commandes Disponibles

### Arguments Principaux

| Argument | Description | Valeurs | Défaut |
|----------|-------------|---------|---------|
| `--agent-name` | Nom de l'agent à tester | Chaîne de caractères | **Requis** |
| `--mode` | Mode d'exécution | `text`, `full` | `text` |
| `--room-name` | Nom de la salle LiveKit | Chaîne de caractères | Auto-généré |
| `--verbose` | Logging détaillé | Aucune valeur | `False` |

### Commandes dans le Mode Texte

Une fois dans le mode texte, vous pouvez utiliser :

- **Tapez votre message** et appuyez sur Entrée pour envoyer
- **`quit`**, **`exit`** ou **`q`** : Quitter la conversation
- **`clear`** : Effacer l'historique de conversation
- **Ctrl+C** : Interrompre immédiatement

## 🔧 Configuration Requise

### Dépendances Python

Le CLI utilise [`pyproject.toml`](pyproject.toml) pour gérer les dépendances :

**Dépendances principales :**
- `aiohttp` - Requêtes HTTP asynchrones
- `livekit-api` - SDK LiveKit Python (mode full)
- `sounddevice`/`pyaudio` - Capture audio (mode full)
- `numpy` - Traitement audio

**Installation automatique avec UV :**
```bash
# Installer toutes les dépendances
uv sync

# Installer avec dépendances audio
uv sync --with audio

# Installer avec LiveKit
uv sync --with livekit
```

### Variables d'Environnement

Le CLI utilise ces variables par défaut :

```bash
# Backend API (doit être accessible depuis votre machine locale)
AGENT_SERVICE_URL=http://localhost:8001

# LiveKit (mode full uniquement)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

**Important** : Le backend Docker doit être accessible depuis votre machine locale.

## 🎮 Exemples d'Utilisation

### Test Rapide d'Agent

```bash
# Test simple en mode texte
python -m src.cli.main --agent-name "assistant" --mode text

# Sortie attendue :
🤖 Text Interface for Agent: assistant
==================================================
Type your messages and press Enter
Type 'quit' or 'exit' to end the conversation
Type 'clear' to clear the conversation history
==================================================
✅ Agent 'assistant' found!

👤 You: Bonjour, comment vas-tu ?
🤖 Agent: Bonjour ! Je vais très bien, merci de demander. Comment puis-je vous aider aujourd'hui ?
```

### Test Audio Complet

```bash
# Test avec audio via LiveKit
python -m src.cli.main --agent-name "etienne" --mode full --verbose

# Sortie attendue :
🎙️  Full Audio Mode for Agent: etienne
==================================================
Room: cli-etienne-a1b2c3d4
LiveKit WebRTC audio connection
Press Ctrl+C to exit
==================================================
✅ LiveKit service is healthy
🔄 Creating LiveKit room...
✅ LiveKit room created
🔄 Notifying agent to join room...
✅ Agent notified
🔄 Connecting to LiveKit...
✅ LiveKit connection established
🎧 Audio connection active!
Speak into your microphone to interact with the agent
Press Ctrl+C to disconnect
```

## 🔍 Dépannage

### Problèmes Courants

#### Agent Non Trouvé
```bash
❌ Agent 'mon-agent' not found in the system!
```

**Solution :**
- Vérifier que le backend est démarré : `docker compose ps`
- Vérifier les agents disponibles : `curl http://localhost:8001/api/agents`

#### LiveKit Non Disponible
```bash
❌ LiveKit service is not available!
```

**Solution :**
- Vérifier que LiveKit est démarré : `docker compose ps | grep livekit`
- Vérifier la santé : `curl http://localhost:7880/health`

#### Erreur de Connexion
```bash
Network error: Cannot connect to host localhost:8001
```

**Solution :**
- Vérifier que tous les services sont démarrés
- Vérifier les logs : `docker compose logs voicebot-app`

### Logs et Debugging

```bash
# Activer les logs détaillés
python -m src.cli.main --agent-name "etienne" --mode text --verbose

# Voir les logs Docker
docker compose logs -f voicebot-app
docker compose logs -f livekit
```

## 📁 Structure des Fichiers

```
src/cli/
├── __init__.py          # Package initialization
├── main.py              # Point d'entrée principal
├── text_input.py        # Interface texte uniquement
└── agent_runner.py      # Runner mode audio complet
```

## 🎯 Bonnes Pratiques

1. **Commencez par le mode texte** pour tester rapidement la logique des agents
2. **Utilisez le mode audio** une fois que l'agent fonctionne correctement en texte
3. **Activez les logs détaillés** (`--verbose`) pour le debugging
4. **Testez avec différents agents** pour valider les configurations

## 🔄 Intégration avec le Développement

Le CLI peut être utilisé dans vos scripts de développement :

```bash
#!/bin/bash
# Script de test automatisé

echo "Testing agent functionality..."
python -m src.cli.main --agent-name "test-agent" --mode text << EOF
Bonjour
Comment vas-tu ?
quit
EOF

echo "Agent test completed!"
```

Cette approche permet un développement plus rapide et efficace des agents vocaux sans les allers-retours constants avec l'interface web.