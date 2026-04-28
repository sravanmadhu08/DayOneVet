import json
import re

from django.core.exceptions import ValidationError

from .models import SPECIES_CHOICES, SYSTEM_CHOICES


SPECIES_VALUES = {value for value, _label in SPECIES_CHOICES}
SYSTEM_VALUES = {value for value, _label in SYSTEM_CHOICES}


def normalise_value(value):
    normalised = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if normalised in {
        "all_species",
        "all_systems",
        "all",
        "general_species",
        "general_system",
        "general_systems",
        "unknown",
        "unknown_system",
        "unknown_systems",
        "n/a",
        "n_a",
        "na",
        "none",
        "not_applicable",
        "not_specified",
        "mixed",
        "misc",
        "miscellaneous",
    }:
        return "general"
    return normalised


def load_questions_from_json_file(uploaded_file):
    try:
        data = json.load(uploaded_file)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc

    if isinstance(data, dict):
        data = data.get("questions")
    if not isinstance(data, list):
        raise ValidationError("JSON must be a list, or an object with a 'questions' list.")
    return data


def load_questions_from_docx_file(uploaded_file):
    try:
        from docx import Document
    except ImportError as exc:
        raise ValidationError("DOCX import requires python-docx. Run: pip install -r requirements.txt") from exc

    document = Document(uploaded_file)
    blocks = []
    current = []
    for paragraph in document.paragraphs:
        line = paragraph.text.strip()
        if not line:
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)

    return [parse_docx_block(block, index + 1) for index, block in enumerate(blocks)]


def parse_docx_block(block, number):
    item = {"choices": []}
    for line in block:
        lower = line.lower()
        choice_match = re.match(r"^([A-Z])[\).]\s+(.+)$", line)
        if lower.startswith("species:"):
            item["species"] = normalise_value(line.split(":", 1)[1])
        elif lower.startswith("system:") or lower.startswith("body system:") or lower.startswith("body_system:"):
            item["system"] = normalise_value(line.split(":", 1)[1])
        elif lower.startswith("question:"):
            item["text"] = line.split(":", 1)[1].strip()
        elif choice_match:
            item["choices"].append({"text": choice_match.group(2).strip(), "is_correct": False})
        elif lower.startswith("answer:"):
            item["answer"] = line.split(":", 1)[1].strip().upper().rstrip(".)")
        elif lower.startswith("explanation:"):
            item["explanation"] = line.split(":", 1)[1].strip()
        elif lower.startswith("exam tip:") or lower.startswith("tip:"):
            item["exam_tip"] = line.split(":", 1)[1].strip()
        else:
            raise ValidationError(f"DOCX block {number}: unrecognised line: {line}")

    answer_map = {chr(65 + index): index for index in range(26)}
    answer_index = answer_map.get(item.get("answer"))
    if answer_index is not None and answer_index < len(item["choices"]):
        item["choices"][answer_index]["is_correct"] = True
    return item


def validate_question_item(item, number):
    required_fields = ["text", "species", "system", "explanation", "choices"]
    for field in required_fields:
        if not item.get(field):
            raise ValidationError(f"Question {number}: missing '{field}'.")

    species = normalise_value(item["species"])
    system = normalise_value(item["system"])
    if species not in SPECIES_VALUES:
        raise ValidationError(f"Question {number}: invalid species '{species}'.")
    if system not in SYSTEM_VALUES:
        system = "general"

    choices = item["choices"]
    if len(choices) < 2:
        raise ValidationError(f"Question {number}: at least 2 choices are required.")

    normalised_choices = []
    correct_count = 0
    for choice in choices:
        if isinstance(choice, str):
            raise ValidationError(f"Question {number}: JSON choices must include text and is_correct.")
        text = choice.get("text", "").strip()
        is_correct = bool(choice.get("is_correct", False))
        if not text:
            raise ValidationError(f"Question {number}: choice text cannot be blank.")
        correct_count += 1 if is_correct else 0
        normalised_choices.append({"text": text, "is_correct": is_correct})

    if correct_count != 1:
        raise ValidationError(f"Question {number}: exactly one choice must be correct.")

    return {
        "text": item["text"].strip(),
        "species": species,
        "system": system,
        "explanation": item["explanation"].strip(),
        "exam_tip": item.get("exam_tip", "").strip(),
        "choices": normalised_choices,
    }


def load_and_validate_questions(uploaded_file, filename):
    suffix = filename.lower().rsplit(".", 1)[-1]
    if suffix == "json":
        questions = load_questions_from_json_file(uploaded_file)
    elif suffix == "docx":
        questions = load_questions_from_docx_file(uploaded_file)
    else:
        raise ValidationError("Only .json and .docx files are supported.")
    return [validate_question_item(item, index + 1) for index, item in enumerate(questions)]
