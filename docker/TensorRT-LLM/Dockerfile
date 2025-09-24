# ./Dockerfile

FROM nvcr.io/nvidia/tensorrt-llm/release:latest

WORKDIR /app/tensorrt_llm

# Installer les dépendances
RUN apt-get update && apt-get install -y git git-lfs && rm -rf /var/lib/apt/lists/*

# Copier le script d'entrée et le rendre exécutable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Définir le script comme point d'entrée
ENTRYPOINT ["./entrypoint.sh"]

# Commande par défaut (dynamique via entrypoint)
CMD ["trtllm-serve"]
