#!/bin/bash

# Function to download a model from a given URL and save it to MODELS_DIR
download_model() {
    local url=$1
    local filename=$(basename "${url%%\?*}")  # Remove everything after and including '?'
    wget -O "./models/${filename}" "${url}"
}

# Check if .env file exists
if [ -f .env_model ]; then
    # Load environment variables from .env file
    export $(grep -v '^#' .env_model | xargs)
    
    # Check each environment variable for model URLs
    for var in ${!MODEL_*}; do
        model_url=${!var}
        if [ ! -z "${model_url}" ]; then
            echo "Downloading model from ${model_url}..."
            download_model "${model_url}"
            echo "Downloaded ${var} successfully."
        else
            echo "Skipping empty URL for ${var}."
        fi
    done
else
    echo ".env file not found. Please create a .env file with model URLs."
    exit 1
fi
