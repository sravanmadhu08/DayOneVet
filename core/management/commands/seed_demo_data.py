from django.core.management.base import BaseCommand

from core.models import Choice, Flashcard, Question, StudyResource


class Command(BaseCommand):
    help = "Create sample RCVS-style questions, flashcards, and study resources."

    def handle(self, *args, **options):
        questions = [
            {
                "text": "A 7-year-old Cavalier King Charles Spaniel has a left apical systolic murmur and exercise intolerance. Which condition is most likely?",
                "species": "dog",
                "system": "cardiology",
                "choices": ["Myxomatous mitral valve disease", "Dilated cardiomyopathy", "Pulmonic stenosis", "Patent ductus arteriosus"],
                "correct": 0,
                "explanation": "Small breed older dogs commonly develop myxomatous degeneration of the mitral valve, producing a left apical systolic murmur.",
                "exam_tip": "Breed, age, and murmur location often identify the most likely cardiac diagnosis.",
            },
            {
                "text": "A cat presents with acute hindlimb paralysis, absent femoral pulses, and painful cold paws. What is the priority diagnosis?",
                "species": "cat",
                "system": "emergency_critical_care",
                "choices": ["Aortic thromboembolism", "Intervertebral disc extrusion", "Pelvic fracture", "Hypokalaemic myopathy"],
                "correct": 0,
                "explanation": "Feline aortic thromboembolism classically causes sudden painful paresis or paralysis with reduced or absent pulses.",
                "exam_tip": "Pain plus absent pulses should push vascular disease high on the list.",
            },
            {
                "text": "A horse has recurrent airway obstruction. Which management change is most appropriate long term?",
                "species": "horse",
                "system": "respiratory",
                "choices": ["Reduce dust exposure and improve ventilation", "Increase cereal concentrate", "Strict box rest in a closed stable", "Long-term antibiotics as sole therapy"],
                "correct": 0,
                "explanation": "Environmental dust and mould control are central to managing equine asthma and recurrent airway obstruction.",
                "exam_tip": "For chronic equine respiratory disease, management often matters as much as medication.",
            },
            {
                "text": "A dairy cow develops left-sided abdominal distension and a high-pitched ping after calving. What is the likely diagnosis?",
                "species": "cow",
                "system": "gastrointestinal",
                "choices": ["Left displaced abomasum", "Rumen acidosis", "Caecal torsion", "Traumatic reticuloperitonitis"],
                "correct": 0,
                "explanation": "Left displaced abomasum is common in high-producing dairy cows after calving and produces a left-sided ping.",
                "exam_tip": "Post-parturient dairy cow plus left ping is a classic exam pairing.",
            },
            {
                "text": "A lamb has sudden death, pulpy kidneys on post-mortem, and a history of high concentrate feeding. Which prevention is indicated?",
                "species": "sheep",
                "system": "infectious_disease",
                "choices": ["Clostridial vaccination", "Copper supplementation", "Coccidiostat only", "Footbath programme"],
                "correct": 0,
                "explanation": "Pulpy kidney is enterotoxaemia associated with Clostridium perfringens type D and is prevented by clostridial vaccination.",
                "exam_tip": "Sudden death in fast-growing lambs should trigger clostridial disease differentials.",
            },
            {
                "text": "A goat has pruritus, alopecia, and crusting around the ears and face. Which first-line diagnostic test is most useful?",
                "species": "goat",
                "system": "dermatology",
                "choices": ["Skin scrape for mites", "Thoracic radiography", "Serum bile acids", "Schirmer tear test"],
                "correct": 0,
                "explanation": "Ectoparasites are common causes of pruritic crusting skin disease and skin scraping is a practical initial test.",
                "exam_tip": "Match the test to the lesion and likely body system.",
            },
            {
                "text": "A pig herd has coughing, poor growth, and cranioventral lung consolidation at slaughter. Which pathogen is classically involved?",
                "species": "pig",
                "system": "respiratory",
                "choices": ["Mycoplasma hyopneumoniae", "Erysipelothrix rhusiopathiae", "Lawsonia intracellularis", "Brachyspira hyodysenteriae"],
                "correct": 0,
                "explanation": "Enzootic pneumonia of pigs is strongly associated with Mycoplasma hyopneumoniae and causes chronic coughing and poor growth.",
                "exam_tip": "Herd-level patterns are often more important than individual signs in pig questions.",
            },
            {
                "text": "A backyard hen has respiratory noise, facial swelling, and reduced egg production. Which biosecurity advice is most appropriate?",
                "species": "poultry",
                "system": "public_health",
                "choices": ["Isolate affected birds and prevent contact with other flocks", "Move birds to shared pasture immediately", "Stop cleaning drinkers", "Mix with new birds to build immunity"],
                "correct": 0,
                "explanation": "Respiratory disease in poultry can spread rapidly; isolation and flock biosecurity reduce transmission risk.",
                "exam_tip": "For flock disease, think population control before individual treatment alone.",
            },
            {
                "text": "A rabbit stops eating and produces very few faecal pellets. What is the most appropriate concern?",
                "species": "exotic",
                "system": "gastrointestinal",
                "choices": ["Gastrointestinal stasis requiring urgent care", "Normal fasting behaviour", "Primary diabetes mellitus", "Routine moulting"],
                "correct": 0,
                "explanation": "Anorexia and reduced faecal output in rabbits suggest gastrointestinal stasis, which can become life-threatening quickly.",
                "exam_tip": "Rabbits should not be treated like dogs or cats when anorexic.",
            },
            {
                "text": "A rescued hedgehog is weak, underweight, and has heavy tick burden. What is the best initial approach?",
                "species": "wildlife",
                "system": "emergency_critical_care",
                "choices": ["Stabilise, warm, assess hydration, and treat parasites appropriately", "Release immediately without examination", "Feed cow's milk", "Delay all treatment for several days"],
                "correct": 0,
                "explanation": "Wildlife casualties require stabilisation and supportive care before definitive treatment or release decisions.",
                "exam_tip": "Initial emergency priorities still apply in wildlife: warmth, hydration, pain, and stress reduction.",
            },
        ]

        created_questions = 0
        for item in questions:
            question, created = Question.objects.get_or_create(
                text=item["text"],
                defaults={
                    "species": item["species"],
                    "system": item["system"],
                    "explanation": item["explanation"],
                    "exam_tip": item["exam_tip"],
                },
            )
            if created:
                created_questions += 1
                for index, choice_text in enumerate(item["choices"]):
                    Choice.objects.create(
                        question=question,
                        text=choice_text,
                        is_correct=index == item["correct"],
                    )

        flashcards = [
            ("Mitral murmur location in dogs", "Typically left apical for mitral valve disease.", "dog", "cardiology"),
            ("Feline aortic thromboembolism clue", "Painful hindlimb paresis with absent femoral pulses.", "cat", "emergency_critical_care"),
            ("Rabbit anorexia", "Treat as urgent because gastrointestinal stasis can progress rapidly.", "exotic", "gastrointestinal"),
            ("LDA timing", "Often occurs in dairy cows soon after calving.", "cow", "gastrointestinal"),
        ]
        for front, back, species, system in flashcards:
            Flashcard.objects.get_or_create(front=front, defaults={"back": back, "species": species, "system": system})

        resources = [
            ("Cardiology essentials", "A concise checklist for murmurs, pulse quality, and emergency cardiac presentations.", "", "cardiology"),
            ("Ruminant gastrointestinal review", "Key differentials for displacement, bloat, acidosis, and parasitic disease.", "cow", "gastrointestinal"),
            ("Exam technique notes", "How to read stems, identify distractors, and prioritise welfare and public health.", "", ""),
        ]
        for title, description, species, system in resources:
            StudyResource.objects.get_or_create(
                title=title,
                defaults={"description": description, "species": species, "system": system},
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded demo data. New questions created: {created_questions}"))
