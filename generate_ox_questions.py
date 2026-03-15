"""
문제 생성 에이전트 - OX 문제 생성기
====================================
지식 베이스를 분석하여 다음 4가지 유형의 문제를 생성합니다:
  1. "보상하는 것은?"
  2. "보상하지 않는 것은?"
  3. "옳은 것은?"
  4. "옳지 않은 것은?"

사용법: python generate_ox_questions.py
"""

import random
import json
import os
import glob
import re

# ============================================================
# Configuration
# ============================================================
OUTPUT_FILE = "questions_ox.json"
NUM_QUESTIONS = 100
KB_DIR = "knowledge_base"

# 문제 유형별 비율 (합계 = 1.0)
QUESTION_TYPE_WEIGHTS = {
    "compensated": 0.25,       # "보상하는 것은?"
    "not_compensated": 0.25,   # "보상하지 않는 것은?"
    "correct": 0.25,           # "옳은 것은?"
    "incorrect": 0.25,         # "옳지 않은 것은?"
}

# ============================================================
# 보상/비보상 분류 패턴
# ============================================================
# 보상하는 것으로 분류하는 키워드 패턴
COMPENSATED_PATTERNS = [
    r"보상한다",
    r"보상할\s*수\s*있다",
    r"담보한다",
    r"보상\s*가능",
    r"보상하여\s*준다",
    r"보상해\s*준다",
    r"보험금.*지급",
    r"손해를\s*보상",
    r"손해도\s*보상",
    r"손해를\s*담보",
    r"비용.*보상",
    r"비용을\s*보상",
    r"전액.*보상",
    r"실손보상",
    r"비례보상",
]

# 보상하지 않는 것으로 분류하는 키워드 패턴
NOT_COMPENSATED_PATTERNS = [
    r"보상하지\s*않",
    r"보상.*않는다",
    r"보상.*않는\s*손해",
    r"면책",
    r"제외[된되]",
    r"보상\s*불가",
    r"담보하지\s*않",
    r"보상에서\s*제외",
    r"보험금.*지급하지\s*않",
    r"보상.*제외",
    r"부보\s*제외",
]


# ============================================================
# 지식 베이스 로더
# ============================================================
def load_knowledge_base():
    """
    knowledge_base 디렉토리의 모든 .txt 파일을 파싱합니다.
    반환: { "주제명": [사실 문장 리스트] }
    """
    topics = {}
    current_topic = None

    if not os.path.exists(KB_DIR):
        print(f"Error: {KB_DIR} directory not found.")
        return {}

    files = glob.glob(os.path.join(KB_DIR, "*.txt"))
    print(f"📂 {KB_DIR}에서 {len(files)}개 파일 로딩 중...")

    for file_path in files:
        if "README" in file_path:
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("[") and line.endswith("]"):
                current_topic = line[1:-1]
                if current_topic not in topics:
                    topics[current_topic] = []
            elif current_topic:
                topics[current_topic].append(line)

    print(f"✅ {len(topics)}개 주제, 총 {sum(len(v) for v in topics.values())}개 사실 로딩 완료")
    return topics


# ============================================================
# 사실 문장 분류기
# ============================================================
def classify_fact(fact):
    """
    사실 문장을 보상/비보상/일반으로 분류합니다.
    비보상 패턴이 먼저 검사됩니다 (더 구체적이므로 우선 적용).

    반환: "compensated" | "not_compensated" | "general"
    """
    # 비보상 패턴 먼저 검사 (더 구체적)
    for pattern in NOT_COMPENSATED_PATTERNS:
        if re.search(pattern, fact):
            return "not_compensated"

    # 보상 패턴 검사
    for pattern in COMPENSATED_PATTERNS:
        if re.search(pattern, fact):
            return "compensated"

    return "general"


def build_classified_db(topics):
    """
    모든 주제의 사실을 분류하여 구조화된 데이터베이스를 구축합니다.

    반환: {
        "주제명": {
            "compensated": [보상 사실 리스트],
            "not_compensated": [비보상 사실 리스트],
            "general": [일반 사실 리스트],
            "all": [전체 사실 리스트]
        }
    }
    """
    db = {}
    stats = {"compensated": 0, "not_compensated": 0, "general": 0}

    for topic, facts in topics.items():
        db[topic] = {
            "compensated": [],
            "not_compensated": [],
            "general": [],
            "all": facts
        }

        for fact in facts:
            category = classify_fact(fact)
            db[topic][category].append(fact)
            stats[category] += 1

    print(f"📊 분류 결과: 보상={stats['compensated']}, 비보상={stats['not_compensated']}, 일반={stats['general']}")
    return db


# ============================================================
# 문제 생성기들
# ============================================================
def generate_compensated_question(db, index):
    """
    "보상하는 것은?" 유형 문제 생성.
    정답: 보상 사실 1개, 오답: 비보상 사실 3개
    """
    # 보상 사실이 있는 주제 찾기
    topics_with_comp = [
        t for t, data in db.items()
        if len(data["compensated"]) >= 1
    ]

    # 비보상 사실 풀 (전체 주제에서)
    all_not_comp = []
    for t, data in db.items():
        for fact in data["not_compensated"]:
            all_not_comp.append((t, fact))

    if not topics_with_comp or len(all_not_comp) < 3:
        return None

    # 주제 선택 및 정답 선택
    topic = random.choice(topics_with_comp)
    correct_fact = random.choice(db[topic]["compensated"])

    # 오답 선택 (비보상 사실에서 3개, 가능하면 같은 주제 우선)
    same_topic_not_comp = [(t, f) for t, f in all_not_comp if t == topic]
    other_topic_not_comp = [(t, f) for t, f in all_not_comp if t != topic]

    distractors = []
    # 같은 주제에서 먼저
    if same_topic_not_comp:
        sample_count = min(2, len(same_topic_not_comp))
        sampled = random.sample(same_topic_not_comp, sample_count)
        distractors.extend([f for _, f in sampled])

    # 부족하면 다른 주제에서 채우기
    remaining = 3 - len(distractors)
    if remaining > 0 and other_topic_not_comp:
        sampled = random.sample(other_topic_not_comp, min(remaining, len(other_topic_not_comp)))
        distractors.extend([f for _, f in sampled])

    if len(distractors) < 3:
        return None

    distractors = distractors[:3]

    # 보기 조합 및 셔플
    options = distractors + [correct_fact]
    random.shuffle(options)
    answer_idx = options.index(correct_fact) + 1

    explanation_parts = [
        f"정답은 {answer_idx}번입니다.",
        f"<br><b>[정답 해설]</b> {correct_fact}",
        f"<br><b>[오답 분석]</b> 나머지 보기는 보상하지 않는 손해(면책)에 해당합니다."
    ]

    return {
        "id": f"ox-comp-{index:03d}",
        "concept": topic,
        "question": f"다음 중 '{topic}'에서 보상하는 것은?",
        "options": options,
        "answer": answer_idx,
        "explanation": "".join(explanation_parts)
    }


def generate_not_compensated_question(db, index):
    """
    "보상하지 않는 것은?" 유형 문제 생성.
    정답: 비보상 사실 1개, 오답: 보상 사실 3개
    """
    # 비보상 사실이 있는 주제 찾기
    topics_with_not_comp = [
        t for t, data in db.items()
        if len(data["not_compensated"]) >= 1
    ]

    # 보상 사실 풀 (전체 주제에서)
    all_comp = []
    for t, data in db.items():
        for fact in data["compensated"]:
            all_comp.append((t, fact))

    if not topics_with_not_comp or len(all_comp) < 3:
        return None

    # 주제 선택 및 정답 선택
    topic = random.choice(topics_with_not_comp)
    correct_fact = random.choice(db[topic]["not_compensated"])

    # 오답 선택 (보상 사실에서 3개, 가능하면 같은 주제 우선)
    same_topic_comp = [(t, f) for t, f in all_comp if t == topic]
    other_topic_comp = [(t, f) for t, f in all_comp if t != topic]

    distractors = []
    if same_topic_comp:
        sample_count = min(2, len(same_topic_comp))
        sampled = random.sample(same_topic_comp, sample_count)
        distractors.extend([f for _, f in sampled])

    remaining = 3 - len(distractors)
    if remaining > 0 and other_topic_comp:
        sampled = random.sample(other_topic_comp, min(remaining, len(other_topic_comp)))
        distractors.extend([f for _, f in sampled])

    if len(distractors) < 3:
        return None

    distractors = distractors[:3]

    options = distractors + [correct_fact]
    random.shuffle(options)
    answer_idx = options.index(correct_fact) + 1

    explanation_parts = [
        f"정답은 {answer_idx}번입니다.",
        f"<br><b>[정답 해설]</b> {correct_fact}",
        f"<br><b>[오답 분석]</b> 나머지 보기는 보상하는 손해에 해당합니다."
    ]

    return {
        "id": f"ox-ncomp-{index:03d}",
        "concept": topic,
        "question": f"다음 중 '{topic}'에서 보상하지 않는 것은?",
        "options": options,
        "answer": answer_idx,
        "explanation": "".join(explanation_parts)
    }


def generate_correct_question(db, index):
    """
    "옳은 것은?" 유형 문제 생성.
    정답: 해당 주제의 올바른 사실, 오답: 다른 주제의 사실 3개
    """
    topic_keys = list(db.keys())
    if len(topic_keys) < 2:
        return None

    # 사실이 충분한 주제 선택
    valid_topics = [t for t in topic_keys if len(db[t]["all"]) >= 1]
    if not valid_topics:
        return None

    topic = random.choice(valid_topics)
    correct_fact = random.choice(db[topic]["all"])

    # 다른 주제에서 오답 선택
    other_topics = [t for t in topic_keys if t != topic and len(db[t]["all"]) >= 1]
    if len(other_topics) < 3:
        # 중복 허용해서라도 3개 채우기
        other_facts_pool = []
        for t in other_topics:
            for f in db[t]["all"]:
                other_facts_pool.append(f)
        if len(other_facts_pool) < 3:
            return None
        distractors = random.sample(other_facts_pool, 3)
    else:
        selected_topics = random.sample(other_topics, 3)
        distractors = [random.choice(db[t]["all"]) for t in selected_topics]

    options = distractors + [correct_fact]
    random.shuffle(options)
    answer_idx = options.index(correct_fact) + 1

    explanation_parts = [
        f"정답은 {answer_idx}번입니다.",
        f"<br><b>[해설]</b> 해당 지문은 '{topic}'에 대한 올바른 설명입니다.",
        f"<br><b>[오답 분석]</b> 나머지 보기는 다른 주제에 대한 설명이거나 '{topic}'과 관계없는 내용입니다."
    ]

    return {
        "id": f"ox-correct-{index:03d}",
        "concept": topic,
        "question": f"다음 중 '{topic}'에 대한 설명으로 가장 옳은 것은?",
        "options": options,
        "answer": answer_idx,
        "explanation": "".join(explanation_parts)
    }


def generate_incorrect_question(db, index):
    """
    "옳지 않은 것은?" 유형 문제 생성.
    정답(옳지 않은 것): 다른 주제의 사실, 오답(옳은 것): 해당 주제의 사실 3개
    """
    topic_keys = list(db.keys())
    if len(topic_keys) < 2:
        return None

    # 사실이 3개 이상인 주제 선택 (오답으로 3개 필요)
    valid_topics = [t for t in topic_keys if len(db[t]["all"]) >= 3]
    if not valid_topics:
        return None

    topic = random.choice(valid_topics)

    # 다른 주제에서 "옳지 않은" 정답 선택
    other_topics = [t for t in topic_keys if t != topic and len(db[t]["all"]) >= 1]
    if not other_topics:
        return None

    wrong_topic = random.choice(other_topics)
    incorrect_fact = random.choice(db[wrong_topic]["all"])

    # 해당 주제에서 올바른 사실 3개 (오답)
    distractors = random.sample(db[topic]["all"], 3)

    options = distractors + [incorrect_fact]
    random.shuffle(options)
    answer_idx = options.index(incorrect_fact) + 1

    explanation_parts = [
        f"정답은 {answer_idx}번입니다.",
        f"<br><b>[해설]</b> '{incorrect_fact}'은(는) '{topic}'이 아닌 '{wrong_topic}'에 대한 설명입니다.",
        f"<br><b>[나머지 보기]</b> 모두 '{topic}'에 대한 올바른 설명입니다."
    ]

    return {
        "id": f"ox-incorr-{index:03d}",
        "concept": topic,
        "question": f"다음 중 '{topic}'에 대한 설명으로 가장 옳지 않은 것은?",
        "options": options,
        "answer": answer_idx,
        "explanation": "".join(explanation_parts)
    }


# ============================================================
# 메인 실행
# ============================================================
def main():
    print("=" * 60)
    print("  문제 생성 에이전트 - OX 문제 생성기")
    print("=" * 60)

    # 1. 지식 베이스 로드
    topics = load_knowledge_base()
    if not topics:
        print("❌ 지식 베이스에서 주제를 찾을 수 없습니다.")
        return

    # 2. 사실 분류
    db = build_classified_db(topics)

    # 3. 문제 생성
    generators = {
        "compensated": generate_compensated_question,
        "not_compensated": generate_not_compensated_question,
        "correct": generate_correct_question,
        "incorrect": generate_incorrect_question,
    }

    # 가중치 기반 타입 선택 리스트 생성
    type_choices = []
    for q_type, weight in QUESTION_TYPE_WEIGHTS.items():
        type_choices.extend([q_type] * int(weight * 100))

    questions = []
    generated_hashes = set()
    type_counts = {k: 0 for k in generators.keys()}

    count = 0
    max_retries = NUM_QUESTIONS * 30  # 충분한 재시도 횟수

    print(f"\n🎯 {NUM_QUESTIONS}개 문제 생성 시작...")

    while len(questions) < NUM_QUESTIONS and count < max_retries:
        count += 1

        # 문제 유형 선택
        q_type = random.choice(type_choices)

        # 문제 생성
        q_data = generators[q_type](db, len(questions))

        if q_data is None:
            continue

        # 중복 검사 (질문 텍스트 + 정답 텍스트)
        answer_text = q_data["options"][q_data["answer"] - 1]
        q_hash = (q_data["question"], answer_text)

        if q_hash in generated_hashes:
            continue

        generated_hashes.add(q_hash)
        questions.append(q_data)
        type_counts[q_type] += 1

    # 4. 결과 출력
    print(f"\n{'=' * 60}")
    print(f"  생성 완료!")
    print(f"{'=' * 60}")
    print(f"  총 문제 수: {len(questions)}/{NUM_QUESTIONS}")
    print(f"  - 보상하는 것은?     : {type_counts['compensated']}문항")
    print(f"  - 보상하지 않는 것은? : {type_counts['not_compensated']}문항")
    print(f"  - 옳은 것은?         : {type_counts['correct']}문항")
    print(f"  - 옳지 않은 것은?    : {type_counts['incorrect']}문항")

    if len(questions) < NUM_QUESTIONS:
        print(f"\n⚠️  경고: 지식 베이스 데이터가 부족하여 {len(questions)}개만 생성되었습니다.")
        print(f"    더 많은 문제를 생성하려면 knowledge_base/ 폴더에 데이터를 추가하세요.")

    # 5. JSON 저장
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"\n📄 '{OUTPUT_FILE}' 파일 저장 완료!")


if __name__ == "__main__":
    main()
