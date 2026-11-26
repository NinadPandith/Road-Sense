"""The one place where the model's class index maps to damage_class (docs/backend-schema.md).

RDD2022 order: D00 (longitudinal), D10 (transverse), D20 (alligator), D40 (pothole).
"""

from app.models.enums import DamageClass

INDEX_TO_CLASS: tuple[DamageClass, ...] = (
    DamageClass.crack_along,  # 0 = D00 longitudinal crack
    DamageClass.crack_across,  # 1 = D10 transverse crack
    DamageClass.alligator_crack,  # 2 = D20 alligator crack
    DamageClass.pothole,  # 3 = D40 pothole
)

RDD_CODE_TO_CLASS: dict[str, DamageClass] = {
    "D00": DamageClass.crack_along,
    "D10": DamageClass.crack_across,
    "D20": DamageClass.alligator_crack,
    "D40": DamageClass.pothole,
}


def class_from_index(index: int) -> DamageClass:
    if not 0 <= index < len(INDEX_TO_CLASS):
        raise ValueError(f"unknown class index {index}")
    return INDEX_TO_CLASS[index]


def confidence_label(confidence: float) -> str:
    """Content Guidelines: Very likely (>= 0.80), Likely (0.50-0.79), Possible (0.35-0.49)."""
    if confidence >= 0.80:
        return "very_likely"
    if confidence >= 0.50:
        return "likely"
    return "possible"
