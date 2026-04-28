import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Choice, Question, SPECIES_CHOICES, SYSTEM_CHOICES


SPECIES_VALUES = {value for value, _label in SPECIES_CHOICES}
SYSTEM_VALUES = {value for value, _label in SYSTEM_CHOICES}


class Command(BaseCommand):
    help = "Import MCQs from a JSON or DOCX file."

    def add_arguments(self, parser):
        parser.add_argument("file_path", help="Path to .json or .docx file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and preview the import without saving anything.",
        )
        parser.add_argument(
            "--skip-duplicates",
            action="store_true",
            help="Skip questions with identical text instead of creating duplicates.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file_path"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        if file_path.suffix.lower() == ".json":
            questions = self.load_json(file_path)
        elif file_path.suffix.lower() == ".docx":
            questions = self.load_docx(file_path)
        else:
            raise CommandError("Only .json and .docx files are supported.")

        validated = [self.validate_question(item, index + 1) for index, item in enumerate(questions)]

        existing_count = 0
        if options["skip_duplicates"]:
            existing_texts = set(Question.objects.filter(text__in=[item["text"] for item in validated]).values_list("text", flat=True))
            existing_count = len(existing_texts)
            validated = [item for item in validated if item["text"] not in existing_texts]

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run only. No questions saved."))
            self.stdout.write(f"Valid questions found: {len(validated)}")
            if existing_count:
                self.stdout.write(f"Duplicates skipped: {existing_count}")
            return

        with transaction.atomic():
            for item in validated:
                question = Question.objects.create(
                    text=item["text"],
                    species=item["species"],
                    system=item["system"],
                    explanation=item["explanation"],
                    exam_tip=item.get("exam_tip", ""),
                )
                for choice in item["choices"]:
                    Choice.objects.create(
                        question=question,
                        text=choice["text"],
                        is_correct=choice["is_correct"],
                    )

        self.stdout.write(self.style.SUCCESS(f"Imported {len(validated)} questions."))
        if existing_count:
            self.stdout.write(f"Duplicates skipped: {existing_count}")

    def load_json(self, file_path):
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON: {exc}") from exc

        if isinstance(data, dict):
            data = data.get("questions")
        if not isinstance(data, list):
            raise CommandError("JSON must be a list, or an object with a 'questions' list.")
        return data

    def load_docx(self, file_path):
        try:
            from docx import Document
        except ImportError as exc:
            raise CommandError("DOCX import requires python-docx. Run: pip install -r requirements.txt") from exc

        document = Document(file_path)
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

        return [self.parse_docx_block(block, index + 1) for index, block in enumerate(blocks)]

    def parse_docx_block(self, block, number):
        item = {"choices": []}
        for line in block:
            lower = line.lower()
            choice_match = re.match(r"^([A-Z])[\).]\s+(.+)$", line)
            if lower.startswith("species:"):
                item["species"] = self.normalise_value(line.split(":", 1)[1])
            elif lower.startswith("system:") or lower.startswith("body system:") or lower.startswith("body_system:"):
                item["system"] = self.normalise_value(line.split(":", 1)[1])
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
                raise CommandError(f"DOCX block {number}: unrecognised line: {line}")

        answer_map = {chr(65 + index): index for index in range(26)}
        answer_index = answer_map.get(item.get("answer"))
        if answer_index is not None and answer_index < len(item["choices"]):
            item["choices"][answer_index]["is_correct"] = True
        return item

    def validate_question(self, item, number):
        required_fields = ["text", "species", "system", "explanation", "choices"]
        for field in required_fields:
            if not item.get(field):
                raise CommandError(f"Question {number}: missing '{field}'.")

        item["species"] = self.normalise_value(item["species"])
        item["system"] = self.normalise_value(item["system"])
        if item["species"] not in SPECIES_VALUES:
            raise CommandError(f"Question {number}: invalid species '{item['species']}'.")
        if item["system"] not in SYSTEM_VALUES:
            item["system"] = "general"

        choices = item["choices"]
        if len(choices) < 2:
            raise CommandError(f"Question {number}: at least 2 choices are required.")

        normalised_choices = []
        correct_count = 0
        for choice in choices:
            if isinstance(choice, str):
                raise CommandError(f"Question {number}: JSON choices must include text and is_correct.")
            text = choice.get("text", "").strip()
            is_correct = bool(choice.get("is_correct", False))
            if not text:
                raise CommandError(f"Question {number}: choice text cannot be blank.")
            correct_count += 1 if is_correct else 0
            normalised_choices.append({"text": text, "is_correct": is_correct})

        if correct_count != 1:
            raise CommandError(f"Question {number}: exactly one choice must be correct.")

        return {
            "text": item["text"].strip(),
            "species": item["species"],
            "system": item["system"],
            "explanation": item["explanation"].strip(),
            "exam_tip": item.get("exam_tip", "").strip(),
            "choices": normalised_choices,
        }

    def normalise_value(self, value):
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
