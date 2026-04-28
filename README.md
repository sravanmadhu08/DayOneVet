# RC

A minimal Django web app for RCVS exam preparation, built with SQLite, Django templates, built-in authentication, and light JavaScript.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_data
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

## Main Routes

- `/`
- `/register/`
- `/login/`
- `/logout/`
- `/home/`
- `/quiz/start/`
- `/study/`
- `/flashcards/`
- `/forum/`
- `/admin/`

## Bulk Import MCQs

Import from JSON:

```bash
python manage.py import_questions questions.json --dry-run
python manage.py import_questions questions.json --skip-duplicates
```

JSON format:

```json
[
  {
    "text": "A dog presents with a left apical systolic murmur. What is most likely?",
    "species": "dog",
    "system": "cardiology",
    "explanation": "Older small-breed dogs commonly develop myxomatous mitral valve disease.",
    "exam_tip": "Use breed, age, and murmur location.",
    "choices": [
      {"text": "Myxomatous mitral valve disease", "is_correct": true},
      {"text": "Pulmonic stenosis", "is_correct": false},
      {"text": "Aortic thromboembolism", "is_correct": false},
      {"text": "Patent ductus arteriosus", "is_correct": false},
      {"text": "Another option if needed", "is_correct": false}
    ]
  }
]
```

Import from Word `.docx`:

```bash
python manage.py import_questions questions.docx --dry-run
python manage.py import_questions questions.docx --skip-duplicates
```

DOCX format: separate each question block with a blank line.

```text
Species: dog
System: cardiology
Question: A dog presents with a left apical systolic murmur. What is most likely?
A) Myxomatous mitral valve disease
B) Pulmonic stenosis
C) Aortic thromboembolism
D) Patent ductus arteriosus
E) Another option if needed
Answer: A
Explanation: Older small-breed dogs commonly develop myxomatous mitral valve disease.
Exam tip: Use breed, age, and murmur location.
```

Valid species values: `general`, `dog`, `cat`, `horse`, `cow`, `sheep`, `goat`, `pig`, `poultry`, `exotic`, `wildlife`. Use `general` for all-species questions.

Valid system values: `general`, `respiratory`, `neurology`, `cardiology`, `gastrointestinal`, `musculoskeletal`, `reproductive`, `urinary`, `dermatology`, `ophthalmology`, `endocrine`, `infectious_disease`, `pharmacology`, `surgery`, `anaesthesia`, `emergency_critical_care`, `public_health`. Use `general` for all-system or unknown-system questions.

Questions can have any number of choices from 2 upward, but exactly one choice must be marked correct.
