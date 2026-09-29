"""Persona YAML loader with schema validation and content hashing."""

import hashlib
from pathlib import Path
from typing import Tuple, Union
import yaml

from deep_persona.persona.schema import PersonaConfig


def compute_file_hash(file_path: Union[str, Path]) -> str:
    """Compute SHA256 hash of a file."""
    path = Path(file_path)
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_persona(file_path: Union[str, Path]) -> Tuple[PersonaConfig, str]:
    """
    Load and validate a Persona YAML file.
    
    Returns:
        Tuple of (PersonaConfig, sha256_hash)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    raw_data = yaml.safe_load(content)
    if not isinstance(raw_data, dict):
        raise ValueError(f"Invalid YAML structure in {path}: expected dict at root")

    config = PersonaConfig.model_validate(raw_data)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return config, content_hash
