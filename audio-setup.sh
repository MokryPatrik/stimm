#!/bin/bash
# Script de configuration audio permanente pour WSL2
# À exécuter manuellement si l'audio ne fonctionne pas

set -e

echo "🔧 Configuration audio WSL2 permanente"

# 1. Configuration des variables d'environnement
echo "1. Configuration des variables d'environnement..."
cat > ~/.bashrc_audio_setup << 'EOF'
#!/bin/bash
# Configuration audio permanente pour WSL2
export PULSE_SERVER=unix:/mnt/wslg/PulseServer

check_audio() {
    if pactl info &>/dev/null; then
        echo "✅ Audio WSL2 fonctionnel"
        return 0
    else
        echo "❌ Audio WSL2 non accessible - exécutez ./audio-setup.sh"
        return 1
    fi
}

# Vérification au démarrage
if [ -n "$PS1" ]; then
    echo "Vérification de l'audio WSL2..."
    check_audio
fi
EOF

# 2. Ajout au .bashrc
echo "2. Configuration du .bashrc..."
if ! grep -q "bashrc_audio_setup" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Configuration audio WSL2" >> ~/.bashrc
    echo "source ~/.bashrc_audio_setup" >> ~/.bashrc
fi

# 3. Test de la configuration
echo "3. Test de la configuration..."
source ~/.bashrc_audio_setup

echo ""
echo "✅ Configuration permanente terminée !"
echo ""
echo "La configuration audio sera vérifiée à chaque démarrage de WSL2."
echo "Si l'audio ne fonctionne pas, exécutez simplement: ./audio-setup.sh"