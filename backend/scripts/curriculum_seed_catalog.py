"""Curated Python curriculum seed catalog: 6 DAG topics, 54 resources, and 42 questions."""

from typing import TypedDict

from app.core.enums import AnswerOption, ContentType, DifficultyLevel, SupportedLanguage


class TopicSeed(TypedDict):
    slug: str
    name: str
    description: str
    display_order: int
    prereqs: list[str]


class ResourceSeed(TypedDict):
    topic_slug: str
    title: str
    description: str
    external_url: str
    content_type: ContentType
    difficulty: DifficultyLevel
    language: SupportedLanguage
    estimated_minutes: int


class QuestionSeed(TypedDict):
    topic_slug: str
    question_text: str
    code_snippet: str | None
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: AnswerOption
    explanation: str
    difficulty: DifficultyLevel


TOPICS_DATA: list[TopicSeed] = [
    {
        "slug": "variables",
        "name": "Variables & Data Types",
        "description": (
            "Variable assignment, dynamic typing, object references, strings, integers, "
            "floating-point numbers, booleans, and explicit type casting in Python."
        ),
        "display_order": 1,
        "prereqs": [],
    },
    {
        "slug": "operators",
        "name": "Operators & Expressions",
        "description": (
            "Arithmetic, floor/modulo division, comparison, short-circuit boolean logic, "
            "identity vs equality, membership checks, and operator precedence."
        ),
        "display_order": 2,
        "prereqs": ["variables"],
    },
    {
        "slug": "conditionals",
        "name": "Conditionals & Branching",
        "description": (
            "Control branching with if, elif, and else blocks, truthy/falsy evaluation, "
            "guard clauses, conditional expressions, and structural pattern matching."
        ),
        "display_order": 3,
        "prereqs": ["operators"],
    },
    {
        "slug": "loops",
        "name": "Loops & Control Flow",
        "description": (
            "Definite and indefinite iteration with for and while loops, range(), enumerate(), "
            "zip(), break, continue, loop-else clauses, and preventing infinite loops."
        ),
        "display_order": 4,
        "prereqs": ["conditionals"],
    },
    {
        "slug": "functions",
        "name": "Functions & Scope",
        "description": (
            "Defining modular functions, positional and keyword parameters, safe default arguments, "
            "*args/**kwargs, return tuples, LEGB variable scope, and docstrings."
        ),
        "display_order": 5,
        "prereqs": ["loops"],
    },
    {
        "slug": "data-structures",
        "name": "Core Data Structures",
        "description": (
            "Lists, tuples, dictionaries, and sets: indexing, slicing, hashability, mutability "
            "pitfalls, comprehension expressions, and algorithmic lookup complexity."
        ),
        "display_order": 6,
        "prereqs": ["loops", "functions"],
    },
]


def _build_resources() -> list[ResourceSeed]:
    """Builds 54 curated resources (9 per topic: 7 English + 2 Turkish across formats/levels)."""
    catalog: list[ResourceSeed] = [
        # --- 1. VARIABLES & DATA TYPES (9) ---
        {
            "topic_slug": "variables",
            "title": "Python Variables, Names, and Dynamic Typing Visual Guide",
            "description": (
                "Beginner video walkthrough showing how Python binds variable names to objects in "
                "memory, covering int, float, str, bool, and type() inspection for fundamentals."
            ),
            "external_url": "https://learnpath.example.org/resources/variables-dynamic-typing-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 16,
        },
        {
            "topic_slug": "variables",
            "title": "Official Python Tutorial: Numbers, Text Strings, and Formatting",
            "description": (
                "Foundational article explaining numeric literals, string indexing, f-strings, "
                "escape sequences, and immutability of Python strings for beginners."
            ),
            "external_url": "https://docs.python.org/3/tutorial/introduction.html#using-python-as-a-calculator",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 22,
        },
        {
            "topic_slug": "variables",
            "title": "Hands-On Type Conversion and Input Parsing Drills",
            "description": (
                "Interactive beginner coding exercises practicing int(), float(), str(), bool() "
                "casting, handling ValueError edge cases, and formatting console output."
            ),
            "external_url": "https://learnpath.example.org/resources/variables-type-casting-exercises",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 25,
        },
        {
            "topic_slug": "variables",
            "title": "String Slicing, f-String Specifiers, and Data Cleaning Basics",
            "description": (
                "Intermediate article tailored for data science preparation: string methods, "
                "strip/split workflows, numeric precision specifiers, and clean tabular formatting."
            ),
            "external_url": "https://learnpath.example.org/resources/variables-fstrings-data-cleaning",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 20,
        },
        {
            "topic_slug": "variables",
            "title": "Object References, Aliasing, and id() Deep Dive",
            "description": (
                "Intermediate video illustrating Python's object model, reference assignment vs "
                "copying, None singletons, and memory aliasing pitfalls."
            ),
            "external_url": "https://learnpath.example.org/resources/variables-object-references-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 19,
        },
        {
            "topic_slug": "variables",
            "title": "Floating-Point Representation, Decimal, and Numeric Precision Lab",
            "description": (
                "Advanced exercise set exploring IEEE 754 binary floating-point rounding, "
                "decimal.Decimal arithmetic, and exact financial/scientific calculations."
            ),
            "external_url": "https://docs.python.org/3/tutorial/floatingpoint.html",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 30,
        },
        {
            "topic_slug": "variables",
            "title": "Unicode Encodings, Bytes vs Str, and Serialization Internals",
            "description": (
                "Advanced backend engineering article covering UTF-8 encoding, bytes literals, "
                "encode/decode error handlers, and safe network payload handling."
            ),
            "external_url": "https://docs.python.org/3/howto/unicode.html",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 28,
        },
        {
            "topic_slug": "variables",
            "title": "Python Değişkenler ve Temel Veri Tipleri Görsel Rehberi",
            "description": (
                "Python'da değişken tanımlama, int, float, str, bool veri tipleri ve f-string "
                "kullanımını adım adım anlatan başlangıç seviyesi Türkçe video ders."
            ),
            "external_url": "https://learnpath.example.org/tr/degiskenler-veri-tipleri-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 18,
        },
        {
            "topic_slug": "variables",
            "title": "Tip Dönüşümleri ve Metin İşleme Uygulama Alıştırmaları",
            "description": (
                "Kullanıcı girdilerini sayısal tiplere dönüştürme ve metin dilimleme üzerine "
                "etkileşimli Türkçe Python kodlama egzersizleri."
            ),
            "external_url": "https://learnpath.example.org/tr/tip-donusumleri-alistirma",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 22,
        },
        # --- 2. OPERATORS & EXPRESSIONS (9) ---
        {
            "topic_slug": "operators",
            "title": "Arithmetic, Floor Division, and Modulo Operators Explained",
            "description": (
                "Beginner video comparing true division (/), floor division (//), modulo (%), "
                "and exponentiation (**) with visual clock and pagination examples."
            ),
            "external_url": "https://learnpath.example.org/resources/operators-division-modulo-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 15,
        },
        {
            "topic_slug": "operators",
            "title": "Boolean Logic, Short-Circuit Evaluation, and Chained Comparisons",
            "description": (
                "Beginner article detailing and, or, not, chained range comparisons like "
                "0 <= score <= 100, and how Python short-circuits boolean expressions."
            ),
            "external_url": "https://learnpath.example.org/resources/operators-boolean-short-circuit",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 18,
        },
        {
            "topic_slug": "operators",
            "title": "Operator Precedence and Expression Evaluation Practice",
            "description": (
                "Beginner interactive drills predicting expression outcomes, placing parentheses "
                "for clarity, and debugging precedence bugs in arithmetic and boolean code."
            ),
            "external_url": "https://learnpath.example.org/resources/operators-precedence-drills",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 20,
        },
        {
            "topic_slug": "operators",
            "title": "Identity (`is`) vs Equality (`==`) and Membership (`in`) Pitfalls",
            "description": (
                "Intermediate video explaining why None checks must use `is None`, how `==` "
                "invokes __eq__, and fast vs slow membership checks across sequences."
            ),
            "external_url": "https://learnpath.example.org/resources/operators-identity-vs-equality",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 17,
        },
        {
            "topic_slug": "operators",
            "title": "Assignment Expressions (Walrus Operator `:=`) in Practice",
            "description": (
                "Intermediate article showing clean use cases for PEP 572 assignment expressions "
                "in regex matching, stream chunking, and data filtering."
            ),
            "external_url": "https://learnpath.example.org/resources/operators-walrus-pep572",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 16,
        },
        {
            "topic_slug": "operators",
            "title": "Bitwise Masks, Shifts, and Flag Manipulation Exercises",
            "description": (
                "Advanced hands-on exercises using &, |, ^, ~, <<, and >> operators to pack "
                "permissions, parse binary headers, and optimize flag checks."
            ),
            "external_url": "https://learnpath.example.org/resources/operators-bitwise-flags-lab",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 28,
        },
        {
            "topic_slug": "operators",
            "title": "Python Data Model: Precedence Table and Augmented Assignment Semantics",
            "description": (
                "Advanced reference article analyzing += in-place mutation (`__iadd__`) vs "
                "rebinding (`__add__`) on mutable lists versus immutable tuples."
            ),
            "external_url": "https://docs.python.org/3/reference/expressions.html#operator-precedence",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 26,
        },
        {
            "topic_slug": "operators",
            "title": "Python Operatörler, Kısa Devre Mantığı ve İşlem Önceliği",
            "description": (
                "Aritmetik, karşılaştırma ve mantıksal operatörlerin çalışma sırasını örneklerle "
                "açıklayan Türkçe makale."
            ),
            "external_url": "https://learnpath.example.org/tr/operatorler-islem-onceligi-makale",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 17,
        },
        {
            "topic_slug": "operators",
            "title": "Mantıksal İfadeler ve Modül Aritmetiği Kodlama Pratiği",
            "description": (
                "Bölünebilme, aralık kontrolü ve `is`/`==` farkı üzerine Türkçe uygulama soruları."
            ),
            "external_url": "https://learnpath.example.org/tr/operatorler-alistirma",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 20,
        },
        # --- 3. CONDITIONALS & BRANCHING (9) ---
        {
            "topic_slug": "conditionals",
            "title": "Writing Clear `if`, `elif`, and `else` Decision Trees",
            "description": (
                "Beginner video tutorial illustrating indentation blocks, mutually exclusive "
                "branches, and step-by-step execution tracing of conditional logic."
            ),
            "external_url": "https://learnpath.example.org/resources/conditionals-if-elif-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 16,
        },
        {
            "topic_slug": "conditionals",
            "title": "Truthiness Rules in Python: Empty Containers, Zero, and `None`",
            "description": (
                "Beginner article explaining idiomatic Python truth value testing (`if items:` "
                "vs `if len(items) > 0`) and avoiding subtle bugs when `0` is a valid input."
            ),
            "external_url": "https://docs.python.org/3/library/stdtypes.html#truth-value-testing",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 15,
        },
        {
            "topic_slug": "conditionals",
            "title": "Branching Logic and Boundary Condition Coding Challenges",
            "description": (
                "Beginner interactive exercises covering grade classifiers, leap-year rules, "
                "shipping tiers, and off-by-one boundary validation."
            ),
            "external_url": "https://learnpath.example.org/resources/conditionals-boundary-exercises",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 24,
        },
        {
            "topic_slug": "conditionals",
            "title": "Refactoring Deeply Nested `if` Blocks with Guard Clauses",
            "description": (
                "Intermediate backend code-quality article demonstrating early returns, flat "
                "validation pipelines, and readable ternary conditional expressions."
            ),
            "external_url": "https://learnpath.example.org/resources/conditionals-guard-clauses",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 19,
        },
        {
            "topic_slug": "conditionals",
            "title": "Structural Pattern Matching (`match` / `case`) Walkthrough",
            "description": (
                "Intermediate video introducing Python 3.10+ `match`/`case` syntax, sequence and "
                "mapping patterns, wildcards, and `if` guards for API payload routing."
            ),
            "external_url": "https://learnpath.example.org/resources/conditionals-match-case-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 23,
        },
        {
            "topic_slug": "conditionals",
            "title": "Pattern Matching & State Machine Refactoring Lab",
            "description": (
                "Advanced coding lab refactoring brittle `elif` chains into exhaustive structural "
                "pattern matchers and dispatch tables for automation parsers."
            ),
            "external_url": "https://peps.python.org/pep-0636/",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 32,
        },
        {
            "topic_slug": "conditionals",
            "title": "Decision Tables and Rule Validation Patterns for Clean Architecture",
            "description": (
                "Advanced article comparing polymorphic handlers, dictionary dispatch, and "
                "declarative rule predicates in testable Python services."
            ),
            "external_url": "https://learnpath.example.org/resources/conditionals-decision-tables",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 25,
        },
        {
            "topic_slug": "conditionals",
            "title": "Python Koşullu İfadeler (`if-elif-else`) ve Doğruluk Değerleri",
            "description": (
                "Karar yapıları, girintileme kuralları ve boş koleksiyonların boolean "
                "değerlendirmesini anlatan Türkçe başlangıç videosu."
            ),
            "external_url": "https://learnpath.example.org/tr/kosullu-ifadeler-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 17,
        },
        {
            "topic_slug": "conditionals",
            "title": "Koruma Cümlecikleri (Guard Clauses) ve `match-case` Egzersizleri",
            "description": (
                "İç içe geçmiş koşul bloklarını sadeleştirme üzerine orta seviye Türkçe "
                "uygulama alıştırmaları."
            ),
            "external_url": "https://learnpath.example.org/tr/kosullar-match-case-alistirma",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 24,
        },
        # --- 4. LOOPS & CONTROL FLOW (9) ---
        {
            "topic_slug": "loops",
            "title": "Master Python `while` & `for` Loops Step by Step",
            "description": (
                "Beginner visual video guide on loop counters, `range(start, stop, step)`, "
                "accumulators, sentinel conditions, and preventing infinite `while` loops."
            ),
            "external_url": "https://learnpath.example.org/resources/loops-for-while-mastery-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 18,
        },
        {
            "topic_slug": "loops",
            "title": "Python Control Flow Docs: `for` Statements, `range()`, and `break`/`continue`",
            "description": (
                "Essential beginner article explaining iterable traversal, early termination "
                "with `break`, skipping iterations with `continue`, and the loop `else` clause."
            ),
            "external_url": "https://docs.python.org/3/tutorial/controlflow.html#for-statements",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 20,
        },
        {
            "topic_slug": "loops",
            "title": "Loop Tracing, Accumulators, and Nested Iteration Practice",
            "description": (
                "Beginner coding drills building frequency counters, running totals, search "
                "loops, and 2D grid traversal patterns."
            ),
            "external_url": "https://learnpath.example.org/resources/loops-accumulator-drills",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 25,
        },
        {
            "topic_slug": "loops",
            "title": "Pythonic Iteration with `enumerate()`, `zip()`, and `reversed()`",
            "description": (
                "Intermediate article replacing manual index counters (`range(len(x))`) with "
                "clean parallel and indexed iteration idioms for data processing."
            ),
            "external_url": "https://learnpath.example.org/resources/loops-enumerate-zip-idioms",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 18,
        },
        {
            "topic_slug": "loops",
            "title": "Debugging Off-by-One Errors and Mutating Lists While Iterating",
            "description": (
                "Intermediate video demonstrating why removing items from a list during a `for` "
                "loop skips elements and how to fix it safely with copies or comprehensions."
            ),
            "external_url": "https://learnpath.example.org/resources/loops-mutation-bugs-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 16,
        },
        {
            "topic_slug": "loops",
            "title": "Lazy Iteration and Combinatoric Pipelines with `itertools`",
            "description": (
                "Advanced exercise lab solving streaming windowing, `islice`, `chain`, `groupby`, "
                "and memory-efficient log processing challenges."
            ),
            "external_url": "https://docs.python.org/3/library/itertools.html",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 35,
        },
        {
            "topic_slug": "loops",
            "title": "Iterator Protocol (`__iter__` / `__next__`) and `StopIteration` Internals",
            "description": (
                "Advanced article dissecting how Python compiles `for` loops into iterator calls "
                "and how lazy streams keep memory usage constant on large datasets."
            ),
            "external_url": "https://learnpath.example.org/resources/loops-iterator-protocol",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 24,
        },
        {
            "topic_slug": "loops",
            "title": "Python `for` ve `while` Döngüleri, `break` ve `continue` Rehberi",
            "description": (
                "Sayaçlar, `range()`, sonsuz döngüleri önleme ve `enumerate()` kullanımını "
                "anlatan Türkçe başlangıç makalesi."
            ),
            "external_url": "https://learnpath.example.org/tr/donguler-rehberi-makale",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 19,
        },
        {
            "topic_slug": "loops",
            "title": "Döngülerle Veri Tarama ve Algoritma Kurma Egzersizleri",
            "description": (
                "Toplam bulma, filtreleme ve iç içe döngü izleme üzerine etkileşimli Türkçe "
                "kodlama pratikleri."
            ),
            "external_url": "https://learnpath.example.org/tr/donguler-alistirma",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 25,
        },
        # --- 5. FUNCTIONS & SCOPE (9) ---
        {
            "topic_slug": "functions",
            "title": "Defining Reusable Functions, Parameters, and `return` Values",
            "description": (
                "Beginner video contrasting `print()` vs `return`, positional vs keyword "
                "arguments, and decomposing scripts into testable functions."
            ),
            "external_url": "https://learnpath.example.org/resources/functions-basics-return-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 19,
        },
        {
            "topic_slug": "functions",
            "title": "Python Tutorial: Defining Functions, Default Arguments, and Docstrings",
            "description": (
                "Official beginner article covering function signatures, keyword-only arguments, "
                "docstrings, and why mutable default arguments (`def f(x=[]):`) cause bugs."
            ),
            "external_url": "https://docs.python.org/3/tutorial/controlflow.html#defining-functions",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 22,
        },
        {
            "topic_slug": "functions",
            "title": "Function Design, Pure Helpers, and Parameter Passing Exercises",
            "description": (
                "Beginner hands-on coding exercises writing pure helper functions, tuple "
                "unpacking returns, and fixing mutable default parameter traps."
            ),
            "external_url": "https://learnpath.example.org/resources/functions-parameter-drills",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 26,
        },
        {
            "topic_slug": "functions",
            "title": "Flexible Signatures with `*args`, `**kwargs`, and Type Hints",
            "description": (
                "Intermediate article teaching variadic argument forwarding, `/` positional-only "
                "and `*` keyword-only markers, and modern Python type annotations."
            ),
            "external_url": "https://learnpath.example.org/resources/functions-args-kwargs-typing",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 21,
        },
        {
            "topic_slug": "functions",
            "title": "LEGB Scope Rule, Closures, and `global` / `nonlocal` Explained",
            "description": (
                "Intermediate video tracing Local, Enclosing, Global, and Built-in namespaces, "
                "`UnboundLocalError`, and stateful function closures."
            ),
            "external_url": "https://learnpath.example.org/resources/functions-legb-closures-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 20,
        },
        {
            "topic_slug": "functions",
            "title": "Higher-Order Functions, Decorators, and `functools.wraps` Lab",
            "description": (
                "Advanced coding exercises building timing, retry, and memoization (`lru_cache`) "
                "decorators while preserving function metadata."
            ),
            "external_url": "https://learnpath.example.org/resources/functions-decorators-lab",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 34,
        },
        {
            "topic_slug": "functions",
            "title": "Generators (`yield`) and Composable Data Transformation Pipelines",
            "description": (
                "Advanced data engineering article showing how generator functions stream "
                "records lazily with minimal memory footprint compared to eager lists."
            ),
            "external_url": "https://learnpath.example.org/resources/functions-generators-pipelines",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 27,
        },
        {
            "topic_slug": "functions",
            "title": "Python Fonksiyonlar, Parametreler ve Kapsam (LEGB) Kuralları",
            "description": (
                "Fonksiyon tanımlama, varsayılan argüman tuzakları ve değişken kapsamını "
                "örneklerle anlatan Türkçe video ders."
            ),
            "external_url": "https://learnpath.example.org/tr/fonksiyonlar-legb-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 21,
        },
        {
            "topic_slug": "functions",
            "title": "Modüler Fonksiyon Yazımı ve `*args`/`**kwargs` Alıştırmaları",
            "description": (
                "Temiz fonksiyon imzaları ve esnek argüman yapıları üzerine Türkçe pratik "
                "kodlama soruları."
            ),
            "external_url": "https://learnpath.example.org/tr/fonksiyonlar-alistirma",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 25,
        },
        # --- 6. CORE DATA STRUCTURES (9) ---
        {
            "topic_slug": "data-structures",
            "title": "Choosing Between Python Lists, Tuples, Dictionaries, and Sets",
            "description": (
                "Beginner visual video comparing ordered sequences vs hash maps/sets, mutability, "
                "and everyday CRUD operations on core Python collections."
            ),
            "external_url": "https://learnpath.example.org/resources/data-structures-overview-video",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 20,
        },
        {
            "topic_slug": "data-structures",
            "title": "Official Python Tutorial: Lists, Tuples, Sets, and Dictionaries",
            "description": (
                "Comprehensive article covering list methods, slicing, tuple unpacking, set "
                "operations (union, intersection, difference), and dict key/value iteration."
            ),
            "external_url": "https://docs.python.org/3/tutorial/datastructures.html",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 28,
        },
        {
            "topic_slug": "data-structures",
            "title": "Dictionary Aggregation and List Slicing Practice Problems",
            "description": (
                "Beginner coding drills grouping records with `.get()`, deduplicating items "
                "with sets, and slicing nested sequences."
            ),
            "external_url": "https://learnpath.example.org/resources/data-structures-dict-list-drills",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.BEGINNER,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 26,
        },
        {
            "topic_slug": "data-structures",
            "title": "List, Dict, and Set Comprehensions Without Readability Loss",
            "description": (
                "Intermediate article demonstrating idiomatic comprehensions, filtering clauses, "
                "and when to switch back to explicit loops or generator expressions."
            ),
            "external_url": "https://learnpath.example.org/resources/data-structures-comprehensions",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 19,
        },
        {
            "topic_slug": "data-structures",
            "title": "Shallow vs Deep Copy, Nested List Aliasing (`[[0]*3]*3`), and Hashability",
            "description": (
                "Intermediate video uncovering shared inner-list bugs, `copy.deepcopy`, and why "
                "only immutable hashable objects can serve as dictionary keys."
            ),
            "external_url": "https://learnpath.example.org/resources/data-structures-shallow-deep-copy",
            "content_type": ContentType.VIDEO,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 18,
        },
        {
            "topic_slug": "data-structures",
            "title": "Specialized Collections Lab: `defaultdict`, `Counter`, and `deque`",
            "description": (
                "Advanced exercises using `collections` primitives and Big-O O(1) hash lookups "
                "vs O(n) list scans to speed up data pipelines."
            ),
            "external_url": "https://docs.python.org/3/library/collections.html",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 32,
        },
        {
            "topic_slug": "data-structures",
            "title": "Time Complexity and Hash Table Mechanics in CPython",
            "description": (
                "Advanced article analyzing amortized O(1) list append vs O(n) `pop(0)`, "
                "insertion-ordered compact dicts, and memory-efficient modeling."
            ),
            "external_url": "https://wiki.python.org/moin/TimeComplexity",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.ADVANCED,
            "language": SupportedLanguage.EN,
            "estimated_minutes": 24,
        },
        {
            "topic_slug": "data-structures",
            "title": "Python Liste, Demet, Sözlük ve Küme Yapıları Karşılaştırmalı Rehber",
            "description": (
                "Temel veri yapılarının değiştirilebilirlik (mutability), erişim hızı ve "
                "comprehension kullanımını açıklayan Türkçe makale."
            ),
            "external_url": "https://learnpath.example.org/tr/veri-yapilari-rehberi",
            "content_type": ContentType.ARTICLE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 22,
        },
        {
            "topic_slug": "data-structures",
            "title": "Sözlük Gruplama ve Liste Üreteçleri (Comprehensions) Egzersizleri",
            "description": (
                "Frekans sayımı, küme kesişimleri ve iç içe veri yapıları üzerine Türkçe "
                "kodlama alıştırmaları."
            ),
            "external_url": "https://learnpath.example.org/tr/veri-yapilari-alistirma",
            "content_type": ContentType.EXERCISE,
            "difficulty": DifficultyLevel.INTERMEDIATE,
            "language": SupportedLanguage.TR,
            "estimated_minutes": 28,
        },
    ]
    return catalog


def _build_questions() -> list[QuestionSeed]:
    """Builds 36 multiple-choice questions (6 per topic across BEGINNER/INTERMEDIATE/ADVANCED)."""
    return [
        # --- 1. VARIABLES (6) ---
        {
            "topic_slug": "variables",
            "question_text": "What is the data type of `result` after executing the Python code below?",
            "code_snippet": "x = 8\ny = 2\nresult = x / y",
            "option_a": "int",
            "option_b": "float",
            "option_c": "str",
            "option_d": "bool",
            "correct_option": AnswerOption.B,
            "explanation": "In Python 3, true division (`/`) always produces a `float` (`4.0`), even when `x` is evenly divisible by `y`.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "variables",
            "question_text": "What is printed by the following string slicing expression?",
            "code_snippet": "word = 'LearnPath'\nprint(word[0:5])",
            "option_a": "Learn",
            "option_b": "LearnP",
            "option_c": "earnP",
            "option_d": "Path",
            "correct_option": AnswerOption.A,
            "explanation": "Slice stop indices are exclusive in Python: `word[0:5]` extracts indices 0, 1, 2, 3, and 4 (`'Learn'`).",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "variables",
            "question_text": "What happens when the following type conversion runs?",
            "code_snippet": "raw = '42.5'\nvalue = int(raw)",
            "option_a": "`value` becomes `42`",
            "option_b": "`value` becomes `43`",
            "option_c": "Raises `ValueError`",
            "option_d": "Raises `TypeError`",
            "correct_option": AnswerOption.C,
            "explanation": "`int('42.5')` raises `ValueError` because `'42.5'` is not a base-10 integer literal; convert via `int(float(raw))` if truncation is intended.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "variables",
            "question_text": "What will `print(greeting)` output?",
            "code_snippet": "score = 87.456\ngreeting = f'Score: {score:.1f}%'\nprint(greeting)",
            "option_a": "Score: 87.4%",
            "option_b": "Score: 87.5%",
            "option_c": "Score: 87.456%",
            "option_d": "Score: {score:.1f}%",
            "correct_option": AnswerOption.B,
            "explanation": "The format specifier `:.1f` formats the float rounded to 1 decimal place (`87.5`).",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "variables",
            "question_text": "What happens when attempting to modify a character in a Python `str`?",
            "code_snippet": "label = 'python'\nlabel[0] = 'P'",
            "option_a": "`label` becomes `'Python'`",
            "option_b": "Raises `IndexError`",
            "option_c": "Raises `TypeError` because strings are immutable",
            "option_d": "Silently ignores the assignment",
            "correct_option": AnswerOption.C,
            "explanation": "Python strings (`str`) are immutable sequences; item assignment raises `TypeError: 'str' object does not support item assignment`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        {
            "topic_slug": "variables",
            "question_text": "What does `bool('False')` evaluate to in Python?",
            "code_snippet": "flag = bool('False')\nprint(flag)",
            "option_a": "False",
            "option_b": "True",
            "option_c": "None",
            "option_d": "Raises `ValueError`",
            "correct_option": AnswerOption.B,
            "explanation": "Any non-empty `str` is truthy in Python; only the empty string `''` converts to `False`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        # --- 2. OPERATORS (6) ---
        {
            "topic_slug": "operators",
            "question_text": "What are the values of `q` and `r` after running this snippet?",
            "code_snippet": "q = 17 // 5\nr = 17 % 5",
            "option_a": "q = 3.4, r = 2",
            "option_b": "q = 3, r = 2",
            "option_c": "q = 4, r = 3",
            "option_d": "q = 2, r = 3",
            "correct_option": AnswerOption.B,
            "explanation": "`17 // 5` computes floor quotient `3`, and `17 % 5` computes remainder `2` (`3 * 5 + 2 == 17`).",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "operators",
            "question_text": "What is the result of `2 + 3 * 4 ** 2` according to Python operator precedence?",
            "code_snippet": "print(2 + 3 * 4 ** 2)",
            "option_a": "100",
            "option_b": "146",
            "option_c": "50",
            "option_d": "400",
            "correct_option": AnswerOption.C,
            "explanation": "Exponentiation (`**`) binds tighter than `*`, which binds tighter than `+`: `4 ** 2 = 16`, `3 * 16 = 48`, and `2 + 48 = 50`.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "operators",
            "question_text": "What value is assigned to `display` by short-circuit evaluation?",
            "code_snippet": "nickname = ''\ndisplay = nickname or 'Anonymous'\nprint(display)",
            "option_a": "''",
            "option_b": "True",
            "option_c": "Anonymous",
            "option_d": "False",
            "correct_option": AnswerOption.C,
            "explanation": "Python's `or` returns the first truthy operand or the last operand if the first is falsy. Since `''` is falsy, `'Anonymous'` is returned.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "operators",
            "question_text": "What does the following comparison print?",
            "code_snippet": "a = [1, 2, 3]\nb = [1, 2, 3]\nprint(a == b, a is b)",
            "option_a": "True True",
            "option_b": "True False",
            "option_c": "False True",
            "option_d": "False False",
            "correct_option": AnswerOption.B,
            "explanation": "`a == b` compares element equality (`True`), whereas `a is b` checks whether both variables point to the exact same list object in memory (`False`).",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "operators",
            "question_text": "How does Python evaluate chained comparisons like `1 < x < 10` when `x = 5`?",
            "code_snippet": "x = 5\nprint(1 < x < 3)",
            "option_a": "Equivalent to `(1 < x) and (x < 3)` -> `False`",
            "option_b": "Equivalent to `(1 < x) < 3`, which evaluates `True < 3` -> `True`",
            "option_c": "Raises `SyntaxError`",
            "option_d": "Returns `5`",
            "correct_option": AnswerOption.A,
            "explanation": "Python expands chained comparisons `a < b < c` to `(a < b) and (b < c)` (evaluating `b` once), yielding `True and False` -> `False`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        {
            "topic_slug": "operators",
            "question_text": "What does `-7 // 2` evaluate to in Python?",
            "code_snippet": "print(-7 // 2)",
            "option_a": "-3",
            "option_b": "-4",
            "option_c": "-3.5",
            "option_d": "3",
            "correct_option": AnswerOption.B,
            "explanation": "`//` performs floor division (rounding toward negative infinity), so `floor(-3.5)` is `-4`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        # --- 3. CONDITIONALS (6) ---
        {
            "topic_slug": "conditionals",
            "question_text": "Which label is printed when `score = 75`?",
            "code_snippet": "score = 75\nif score >= 85:\n    print('A')\nelif score >= 70:\n    print('B')\nelif score >= 50:\n    print('C')\nelse:\n    print('F')",
            "option_a": "A",
            "option_b": "B",
            "option_c": "B and C",
            "option_d": "C",
            "correct_option": AnswerOption.B,
            "explanation": "Once `elif score >= 70` matches (`75 >= 70`), Python executes that branch (`'B'`) and skips all remaining `elif`/`else` branches.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "conditionals",
            "question_text": "What is printed when `items = []`?",
            "code_snippet": "items = []\nif items:\n    print('Non-empty')\nelse:\n    print('Empty')",
            "option_a": "Non-empty",
            "option_b": "Empty",
            "option_c": "[]",
            "option_d": "Raises `TypeError`",
            "correct_option": AnswerOption.B,
            "explanation": "Empty collections (`[]`, `{}`, `set()`, `()`) are falsy in boolean contexts, so execution enters the `else` block.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "conditionals",
            "question_text": "Why does the function below misbehave when `discount_percent = 0`?",
            "code_snippet": "def format_discount(discount_percent=None):\n    if not discount_percent:\n        return 'Not provided'\n    return f'{discount_percent}%'",
            "option_a": "`0` is falsy, so `not 0` is `True` and returns `'Not provided'` instead of `'0%'`",
            "option_b": "`None` raises `TypeError` inside `not`",
            "option_c": "`0` is truthy in Python",
            "option_d": "Default parameters cannot be `None`",
            "correct_option": AnswerOption.A,
            "explanation": "When `0` is a valid numeric value, check `if discount_percent is None:` explicitly rather than `if not discount_percent:`.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "conditionals",
            "question_text": "What is the value of `status` in this conditional expression?",
            "code_snippet": "temp = 18\nstatus = 'warm' if temp >= 20 else 'cool'",
            "option_a": "'warm'",
            "option_b": "'cool'",
            "option_c": "False",
            "option_d": "None",
            "correct_option": AnswerOption.B,
            "explanation": "Because `temp >= 20` is `False` (`18 < 20`), the conditional expression evaluates to the `else` value `'cool'`.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "conditionals",
            "question_text": "What does this Python `match` statement print?",
            "code_snippet": "command = ('move', 0, 5)\nmatch command:\n    case ('move', 0, 0):\n        print('origin')\n    case ('move', x, y) if y > 0:\n        print(f'up {y}')\n    case _:\n        print('other')",
            "option_a": "origin",
            "option_b": "up 5",
            "option_c": "other",
            "option_d": "Raises `SyntaxError`",
            "correct_option": AnswerOption.B,
            "explanation": "The second pattern destructures `('move', x, y)` with `x=0, y=5` and satisfies the guard `if y > 0`, printing `'up 5'`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        {
            "topic_slug": "conditionals",
            "question_text": "What is printed when nested conditional expressions are evaluated without parentheses?",
            "code_snippet": "n = 0\nlabel = 'pos' if n > 0 else 'neg' if n < 0 else 'zero'\nprint(label)",
            "option_a": "pos",
            "option_b": "neg",
            "option_c": "zero",
            "option_d": "Raises `SyntaxError`",
            "correct_option": AnswerOption.C,
            "explanation": "Conditional expressions associate right-to-left: `'pos' if n > 0 else ('neg' if n < 0 else 'zero')`, yielding `'zero'` for `n = 0`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        # --- 4. LOOPS (6) ---
        {
            "topic_slug": "loops",
            "question_text": "What will be the output of the following `while` loop?",
            "code_snippet": "count = 0\nwhile count < 3:\n    print(count, end=' ')\n    count += 1",
            "option_a": "0 1 2 3",
            "option_b": "0 1 2",
            "option_c": "1 2 3",
            "option_d": "The loop runs forever",
            "correct_option": AnswerOption.B,
            "explanation": "`count` takes values `0`, `1`, and `2`. When `count` reaches `3`, `count < 3` is `False` and the loop exits.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "loops",
            "question_text": "Which sequence of numbers does `list(range(2, 9, 3))` produce?",
            "code_snippet": "print(list(range(2, 9, 3)))",
            "option_a": "[2, 5, 8]",
            "option_b": "[2, 5, 8, 11]",
            "option_c": "[2, 3, 9]",
            "option_d": "[3, 6, 9]",
            "correct_option": AnswerOption.A,
            "explanation": "`range(2, 9, 3)` starts at `2` and increments by `3` while strictly less than `9`, producing `2, 5, 8`.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "loops",
            "question_text": "When does the `else` block attached to a Python `for` loop execute?",
            "code_snippet": "for n in [2, 4, 6]:\n    if n % 2 != 0:\n        print('Found odd')\n        break\nelse:\n    print('All even')",
            "option_a": "Only when the iterable is empty",
            "option_b": "Whenever the loop finishes normally without hitting a `break` statement",
            "option_c": "Whenever a `break` statement terminates the loop",
            "option_d": "After every iteration",
            "correct_option": AnswerOption.B,
            "explanation": "A `for ... else` block executes if and only if the loop completes without encountering `break`—printing `'All even'` here.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "loops",
            "question_text": "What does `enumerate(['a', 'b'], start=1)` yield on its first iteration?",
            "code_snippet": "first = next(enumerate(['a', 'b'], start=1))\nprint(first)",
            "option_a": "('a', 1)",
            "option_b": "(0, 'a')",
            "option_c": "(1, 'a')",
            "option_d": "[1, 'a']",
            "correct_option": AnswerOption.C,
            "explanation": "`enumerate(iterable, start=1)` yields `(index, element)` tuples starting at `1`, so the first item is `(1, 'a')`.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "loops",
            "question_text": "Why does mutating `nums` in-place inside this `for` loop leave `2` in the list?",
            "code_snippet": "nums = [1, 2, 2, 3]\nfor x in nums:\n    if x == 2:\n        nums.remove(x)\nprint(nums)",
            "option_a": "`list.remove()` deletes from the end of the list",
            "option_b": "Removing index 1 shifts the second `2` into index 1 while the loop iterator advances to index 2",
            "option_c": "`remove()` only works once per program",
            "option_d": "`nums` is copied automatically by `for`",
            "correct_option": AnswerOption.B,
            "explanation": "List iterators track positional indices; deleting an element shifts subsequent items left, causing the next element to be skipped.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        {
            "topic_slug": "loops",
            "question_text": "What is the length of `list(zip([1, 2, 3], ['x', 'y']))`?",
            "code_snippet": "pairs = list(zip([1, 2, 3], ['x', 'y']))\nprint(len(pairs))",
            "option_a": "3",
            "option_b": "2",
            "option_c": "5",
            "option_d": "Raises `ValueError` unless `strict=True`",
            "correct_option": AnswerOption.B,
            "explanation": "By default (when `strict=False`), `zip()` stops as soon as the shortest input iterable is exhausted, producing 2 tuples.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        # --- 5. FUNCTIONS (6) ---
        {
            "topic_slug": "functions",
            "question_text": "What value does a Python function return if execution reaches the end without a `return` statement?",
            "code_snippet": "def log_msg(msg):\n    _ = msg\n\nprint(log_msg('hello'))",
            "option_a": "''",
            "option_b": "0",
            "option_c": "None",
            "option_d": "Raises `SyntaxError`",
            "correct_option": AnswerOption.C,
            "explanation": "Functions without an explicit `return` value implicitly return `None`.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "functions",
            "question_text": "What is printed by calling `greet('Ada')` and `greet('Ada', 'Hi')`?",
            "code_snippet": "def greet(name, prefix='Hello'):\n    return f'{prefix}, {name}'\n\nprint(greet('Ada'), '|', greet('Ada', 'Hi'))",
            "option_a": "Hello, Ada | Hi, Ada",
            "option_b": "Ada, Hello | Ada, Hi",
            "option_c": "Raises `TypeError`",
            "option_d": "Hello, Ada | Hello, Ada",
            "correct_option": AnswerOption.A,
            "explanation": "When `prefix` is omitted, its default `'Hello'` is used; passing `'Hi'` overrides the default.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "functions",
            "question_text": "What is printed by the two calls to `append_tag` below?",
            "code_snippet": "def append_tag(tag, bucket=[]):\n    bucket.append(tag)\n    return bucket\n\nprint(append_tag('py'), append_tag('ml'))",
            "option_a": "['py'] ['ml']",
            "option_b": "['py', 'ml'] ['py', 'ml']",
            "option_c": "['py'] ['py', 'ml'] (printed as separate snapshots)",
            "option_d": "Raises `TypeError`",
            "correct_option": AnswerOption.B,
            "explanation": "Default argument values are evaluated once at function definition time. Both calls mutate and return the exact same shared list `['py', 'ml']`!",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "functions",
            "question_text": "Why does calling `increment()` raise `UnboundLocalError`?",
            "code_snippet": "total = 10\ndef increment():\n    total += 1\n    return total\n\nincrement()",
            "option_a": "Integers cannot be incremented with `+=`",
            "option_b": "Assigning to `total` inside `increment` makes `total` a local variable, which is read before assignment",
            "option_c": "`total` must be declared `nonlocal` at module level",
            "option_d": "Functions cannot read module-level variables",
            "correct_option": AnswerOption.B,
            "explanation": "Under Python's LEGB compile-time scoping, `total += 1` marks `total` as local to `increment`, so reading `total` fails before assignment.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "functions",
            "question_text": "What types do `args` and `kwargs` have inside `collect(1, 2, mode='fast')`?",
            "code_snippet": "def collect(*args, **kwargs):\n    return type(args).__name__, type(kwargs).__name__\n\nprint(collect(1, 2, mode='fast'))",
            "option_a": "('list', 'dict')",
            "option_b": "('tuple', 'dict')",
            "option_c": "('tuple', 'tuple')",
            "option_d": "('set', 'dict')",
            "correct_option": AnswerOption.B,
            "explanation": "`*args` packs extra positional arguments into a `tuple`, while `**kwargs` packs extra keyword arguments into a `dict`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        {
            "topic_slug": "functions",
            "question_text": "What happens when `gen = count_up()` is called without calling `next(gen)`?",
            "code_snippet": "def count_up():\n    print('start')\n    yield 1\n\ngen = count_up()",
            "option_a": "Prints `'start'` immediately and returns `1`",
            "option_b": "Prints nothing yet and returns a generator object",
            "option_c": "Prints `'start'` and returns `None`",
            "option_d": "Raises `StopIteration`",
            "correct_option": AnswerOption.B,
            "explanation": "Calling a generator function returns a lazy generator iterator without executing the function body until `next()` is invoked.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        # --- 6. DATA STRUCTURES (6) ---
        {
            "topic_slug": "data-structures",
            "question_text": "What does `scores.get('math', 0)` return when `'math'` is not in `scores`?",
            "code_snippet": "scores = {'python': 95}\nprint(scores.get('math', 0))",
            "option_a": "Raises `KeyError`",
            "option_b": "None",
            "option_c": "0",
            "option_d": "95",
            "correct_option": AnswerOption.C,
            "explanation": "`dict.get(key, default)` safely returns `default` (`0`) instead of raising `KeyError` when `key` is missing.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "data-structures",
            "question_text": "What is the length of `unique_tags` after creating a `set` from duplicates?",
            "code_snippet": "unique_tags = set(['sql', 'python', 'sql', 'ml', 'python'])\nprint(len(unique_tags))",
            "option_a": "5",
            "option_b": "3",
            "option_c": "2",
            "option_d": "Raises `TypeError`",
            "correct_option": AnswerOption.B,
            "explanation": "Sets store unique hashable elements only, deduplicating `'sql'` and `'python'` down to `{'sql', 'python', 'ml'}` (length `3`).",
            "difficulty": DifficultyLevel.BEGINNER,
        },
        {
            "topic_slug": "data-structures",
            "question_text": "What does the list comprehension below evaluate to?",
            "code_snippet": "squares = [n * n for n in range(5) if n % 2 == 1]\nprint(squares)",
            "option_a": "[0, 4, 16]",
            "option_b": "[1, 9]",
            "option_c": "[1, 9, 25]",
            "option_d": "[1, 3]",
            "correct_option": AnswerOption.B,
            "explanation": "Among `0..4`, only `1` and `3` satisfy `n % 2 == 1`; squaring them produces `[1, 9]`.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "data-structures",
            "question_text": "Why does modifying `grid[0][0] = 9` change every row in `grid`?",
            "code_snippet": "grid = [[0, 0]] * 3\ngrid[0][0] = 9\nprint(grid)",
            "option_a": "Lists in Python are column-major",
            "option_b": "`* 3` duplicates references to the exact same inner list rather than cloning inner lists",
            "option_c": "`0` is mutable in Python",
            "option_d": "`grid` is a tuple",
            "correct_option": AnswerOption.B,
            "explanation": "`[[0, 0]] * 3` creates 3 references to a single inner list. Use `[[0, 0] for _ in range(3)]` to allocate independent rows.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "data-structures",
            "question_text": "Which of the following objects CANNOT be used as a key in a Python `dict`?",
            "code_snippet": "# Candidate dictionary keys:\n# A: (1, 2)\n# B: 'topic'\n# C: [1, 2]\n# D: frozenset({1, 2})",
            "option_a": "(1, 2)",
            "option_b": "'topic'",
            "option_c": "[1, 2]",
            "option_d": "frozenset({1, 2})",
            "correct_option": AnswerOption.C,
            "explanation": "Dictionary keys must be hashable. Mutable `list` objects (`[1, 2]`) are unhashable and raise `TypeError: unhashable type: 'list'`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        {
            "topic_slug": "data-structures",
            "question_text": "What is the average-case time complexity of checking `x in collection` when `collection` is a `set` vs a `list` of `n` items?",
            "code_snippet": "# Compare membership lookup:\n# x in my_set   vs   x in my_list",
            "option_a": "`O(1)` for `set`, `O(n)` for `list`",
            "option_b": "`O(n)` for `set`, `O(1)` for `list`",
            "option_c": "`O(log n)` for both `set` and `list`",
            "option_d": "`O(1)` for both `set` and `list`",
            "correct_option": AnswerOption.A,
            "explanation": "Python sets are hash tables (`O(1)` average lookup), whereas lists require a sequential scan (`O(n)` average lookup).",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        # --- ADDITIONAL CURATED QUESTIONS FOR 40+ QUESTION BANK PARITY (42 TOTAL, 7/TOPIC) ---
        {
            "topic_slug": "variables",
            "question_text": "What is printed after unpacking the tuple with a starred target `*middle`?",
            "code_snippet": "first, *middle, last = (10, 20, 30, 40)\nprint(middle)",
            "option_a": "(20, 30)",
            "option_b": "[20, 30]",
            "option_c": "20",
            "option_d": "Raises `ValueError`",
            "correct_option": AnswerOption.B,
            "explanation": "Extended iterable unpacking (`*middle`) always binds the captured slice as a `list` (`[20, 30]`), even when unpacking a tuple.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "operators",
            "question_text": "What does the walrus assignment expression `:=` output in the snippet below?",
            "code_snippet": "data = [1, 2, 3, 4]\nif (n := len(data)) > 2:\n    print(n)",
            "option_a": "True",
            "option_b": "4",
            "option_c": "2",
            "option_d": "Raises `SyntaxError`",
            "correct_option": AnswerOption.B,
            "explanation": "`n := len(data)` binds `n` to `4` and evaluates to `4`, which is `> 2`, so `print(n)` outputs `4`.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "conditionals",
            "question_text": "Which branch executes in this `match / case` structural pattern matching block?",
            "code_snippet": "point = (0, 5)\nmatch point:\n    case (0, 0):\n        label = 'origin'\n    case (0, y):\n        label = f'y={y}'\n    case _:\n        label = 'other'\nprint(label)",
            "option_a": "origin",
            "option_b": "y=5",
            "option_c": "other",
            "option_d": "Raises `MatchError`",
            "correct_option": AnswerOption.B,
            "explanation": "`(0, 5)` fails `(0, 0)` and matches `(0, y)`, binding `y = 5` and producing `'y=5'`.",
            "difficulty": DifficultyLevel.ADVANCED,
        },
        {
            "topic_slug": "loops",
            "question_text": "What is printed when iterating with `zip()` over lists of unequal length?",
            "code_snippet": "keys = ['a', 'b', 'c']\nvals = [1, 2]\nprint(list(zip(keys, vals)))",
            "option_a": "[('a', 1), ('b', 2), ('c', None)]",
            "option_b": "[('a', 1), ('b', 2)]",
            "option_c": "Raises `ValueError`",
            "option_d": "[('a', 1)]",
            "correct_option": AnswerOption.B,
            "explanation": "By default (without `strict=True`), `zip()` stops as soon as the shortest input iterable (`vals`, length 2) is exhausted.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "functions",
            "question_text": "What happens when `area(10, 5)` is called on a function using keyword-only `*` syntax?",
            "code_snippet": "def area(width, *, height):\n    return width * height\n\nprint(area(10, 5))",
            "option_a": "50",
            "option_b": "15",
            "option_c": "Raises `TypeError` because `height` must be passed as a keyword argument",
            "option_d": "Returns `None`",
            "correct_option": AnswerOption.C,
            "explanation": "Parameters placed after bare `*` are keyword-only (`area(10, height=5)`); passing a second positional argument raises `TypeError`.",
            "difficulty": DifficultyLevel.INTERMEDIATE,
        },
        {
            "topic_slug": "data-structures",
            "question_text": "What does `merged` contain after combining two dictionaries with the `|` union operator?",
            "code_snippet": "defaults = {'host': 'localhost', 'port': 5432}\noverride = {'port': 5433}\nmerged = defaults | override\nprint(merged['port'])",
            "option_a": "5432",
            "option_b": "5433",
            "option_c": "[5432, 5433]",
            "option_d": "Raises `TypeError`",
            "correct_option": AnswerOption.B,
            "explanation": "In `d1 | d2` (Python 3.9+), right-hand keys take precedence on collisions, so `'port'` resolves to `5433`.",
            "difficulty": DifficultyLevel.BEGINNER,
        },
    ]


RESOURCES_DATA: list[ResourceSeed] = _build_resources()
QUESTIONS_DATA: list[QuestionSeed] = _build_questions()
