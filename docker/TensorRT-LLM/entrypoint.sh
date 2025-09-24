#!/bin/bash
set -e # Arrête le script si une commande échoue

# ---------------------------------------------------------------------------
# Model selection & derived paths
# ---------------------------------------------------------------------------
LLM_MODEL_REPO=${LLM_HF_MODEL:-nvidia/Llama-3.1-8B-Instruct-FP8}
MODEL_NAME=$(basename "$LLM_MODEL_REPO")
MODELS_ROOT=${LLM_MODELS_ROOT:-/models}
MODEL_HF_DIR="${MODELS_ROOT}/${MODEL_NAME}"
MODEL_CKPT_DIR="${MODELS_ROOT}/${MODEL_NAME}_trtllm_ckpt"
ENGINE_DIR="${MODELS_ROOT}/${MODEL_NAME}_engine"
ENGINE_FILE="${ENGINE_DIR}/rank0.engine"

mkdir -p "$MODEL_CKPT_DIR" "$ENGINE_DIR"

CONVERT_SCRIPT=${LLM_CONVERT_SCRIPT:-}
CONVERT_ARGS_DEFAULT="--use_fp8 --fp8_kv_cache"
if [ -n "${LLM_CONVERT_ARGS+x}" ]; then
    if [ -n "$LLM_CONVERT_ARGS" ]; then
        read -r -a CONVERT_ARGS <<< "$LLM_CONVERT_ARGS"
    else
        CONVERT_ARGS=()
    fi
else
    read -r -a CONVERT_ARGS <<< "$CONVERT_ARGS_DEFAULT"
fi

if [ -z "$CONVERT_SCRIPT" ]; then
    CONVERT_ARGS=()
fi

MAX_BATCH_SIZE=${LLM_MAX_BATCH_SIZE:-1}
MAX_INPUT_LEN=${LLM_MAX_INPUT_LEN:-512}
MAX_SEQ_LEN=${LLM_MAX_SEQ_LEN:-768}
MAX_NUM_TOKENS=${LLM_MAX_NUM_TOKENS:-$MAX_SEQ_LEN}

BUILD_ARGS_DEFAULT="--gemm_plugin auto --gpt_attention_plugin auto"
if [ -n "${LLM_BUILD_ARGS+x}" ]; then
    if [ -n "$LLM_BUILD_ARGS" ]; then
        read -r -a BUILD_ARGS <<< "$LLM_BUILD_ARGS"
    else
        BUILD_ARGS=()
    fi
else
    read -r -a BUILD_ARGS <<< "$BUILD_ARGS_DEFAULT"
fi

QUANTIZE_SCRIPT=${LLM_QUANTIZE_SCRIPT:-}
QUANTIZE_OUTPUT_DIR=${LLM_QUANTIZE_OUTPUT_DIR:-${MODEL_HF_DIR}_quantized}
QUANTIZE_EXTRA_ARGS=()
if [ -n "${LLM_QUANTIZE_EXTRA_ARGS+x}" ] && [ -n "$LLM_QUANTIZE_EXTRA_ARGS" ]; then
    read -r -a QUANTIZE_EXTRA_ARGS <<< "$LLM_QUANTIZE_EXTRA_ARGS"
fi

CONVERT_INPUT_DIR=$MODEL_HF_DIR

# Vérifier si le moteur est déjà construit
echo "Fichier moteur recherché: $ENGINE_FILE"
if [ ! -f "$ENGINE_FILE" ]; then
    echo "Moteur TensorRT non trouvé. Démarrage du processus de construction..."

    # Étape 1: Télécharger le modèle (s'il n'est pas déjà là)
    if [ ! -d "$MODEL_HF_DIR" ]; then
        echo "Téléchargement du modèle depuis Hugging Face..."
        git clone "https://huggingface.co/${LLM_MODEL_REPO}" "$MODEL_HF_DIR"
    else
        echo "Répertoire du modèle déjà présent, pas de téléchargement."
    fi

    # Étape 2: Quantifier le modèle si demandé
    if [ -n "$QUANTIZE_SCRIPT" ]; then
        echo "Quantification du modèle en cours..."
        mkdir -p "$QUANTIZE_OUTPUT_DIR"
        QUANTIZE_CMD=(
            python3
            "$QUANTIZE_SCRIPT"
            --model_dir "$MODEL_HF_DIR/"
            --output_dir "$QUANTIZE_OUTPUT_DIR"
        )
        QUANTIZE_CMD+=("${QUANTIZE_EXTRA_ARGS[@]}")
        "${QUANTIZE_CMD[@]}"
        if [ -d "$QUANTIZE_OUTPUT_DIR" ]; then
            CONVERT_INPUT_DIR=${LLM_CONVERT_INPUT_DIR:-$QUANTIZE_OUTPUT_DIR}
        fi
    fi

    if [ -n "${LLM_CONVERT_INPUT_DIR}" ]; then
        CONVERT_INPUT_DIR=${LLM_CONVERT_INPUT_DIR}
    fi

    # Étape 3: Convertir le modèle si un convertisseur est défini
    if [ -n "$CONVERT_SCRIPT" ]; then
        echo "Conversion du modèle au format checkpoint..."
        CONVERT_CMD=(
            python3
            "$CONVERT_SCRIPT"
            --model_dir "$CONVERT_INPUT_DIR/"
            --output_dir "$MODEL_CKPT_DIR/"
        )
        CONVERT_CMD+=("${CONVERT_ARGS[@]}")
        "${CONVERT_CMD[@]}"
    else
        echo "Aucun script de conversion défini, le build utilisera directement '$CONVERT_INPUT_DIR'"
        MODEL_CKPT_DIR="$CONVERT_INPUT_DIR"
    fi

    # Étape 4: Construire le moteur
    echo "Construction du moteur TensorRT... (Cette étape peut être très longue)"
    BUILD_CMD=(
        trtllm-build
        --checkpoint_dir "$MODEL_CKPT_DIR/"
        --output_dir "$ENGINE_DIR"
        --max_batch_size "$MAX_BATCH_SIZE"
        --max_input_len "$MAX_INPUT_LEN"
        --max_seq_len "$MAX_SEQ_LEN"
        --max_num_tokens "$MAX_NUM_TOKENS"
    )
    BUILD_CMD+=("${BUILD_ARGS[@]}")
    echo "Commande build: ${BUILD_CMD[*]}"
    "${BUILD_CMD[@]}"

    echo "Construction du moteur terminée."

else
    echo "Moteur TensorRT trouvé. Démarrage direct du serveur."
fi

# ---------------------------------------------------------------------------
# Lancement du serveur
# ---------------------------------------------------------------------------
LLM_ENGINE_NAME="${MODEL_NAME}_engine"
export LLM_ENGINE_NAME
export LLM_ENGINE_DIR="$ENGINE_DIR"
export LLM_TOKENIZER_DIR="$MODEL_HF_DIR"

SERVER_HOST=${LLM_SERVER_HOST:-0.0.0.0}
SERVER_PORT=${LLM_SERVER_PORT:-8000}
SERVER_EXTRA_ARGS=()
if [ -n "${LLM_SERVER_EXTRA_ARGS+x}" ]; then
    if [ -n "$LLM_SERVER_EXTRA_ARGS" ]; then
        read -r -a SERVER_EXTRA_ARGS <<< "$LLM_SERVER_EXTRA_ARGS"
    fi
fi

DEFAULT_CMD=(
    trtllm-serve
    serve
    "$ENGINE_DIR"
    --tokenizer
    "$MODEL_HF_DIR"
    --host
    "$SERVER_HOST"
    --port
    "$SERVER_PORT"
    --max_seq_len
    "$MAX_SEQ_LEN"
    --max_batch_size
    "$MAX_BATCH_SIZE"
    --max_num_tokens
    "$MAX_NUM_TOKENS"
)
DEFAULT_CMD+=("${SERVER_EXTRA_ARGS[@]}")

if [ "$#" -eq 0 ] || [ "$1" = "trtllm-serve" ]; then
    echo "Lancement du serveur TensorRT-LLM avec la configuration dérivée pour ${LLM_MODEL_REPO}"
    set -- "${DEFAULT_CMD[@]}"
fi

exec "$@"
