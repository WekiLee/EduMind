"""Assessment 服务单元测试 —— 判卷 + 掌握度计算"""

import pytest
from app.services.assessment import AssessmentService


class TestGradeQuiz:
    """判卷测试"""

    def test_all_correct(self):
        questions = [
            {"id": "q1", "answer": "A"},
            {"id": "q2", "answer": "C"},
        ]
        answers = [
            {"question_id": "q1", "selected": "A"},
            {"question_id": "q2", "selected": "C"},
        ]
        result = AssessmentService.grade_quiz(questions, answers)
        assert result["score"] == 1.0
        assert result["correct"] == 2
        assert result["total"] == 2
        assert result["passed"] is True

    def test_all_wrong(self):
        questions = [
            {"id": "q1", "answer": "A"},
            {"id": "q2", "answer": "C"},
        ]
        answers = [
            {"question_id": "q1", "selected": "B"},
            {"question_id": "q2", "selected": "D"},
        ]
        result = AssessmentService.grade_quiz(questions, answers)
        assert result["score"] == 0.0
        assert result["correct"] == 0
        assert result["passed"] is False

    def test_partial_correct(self):
        questions = [
            {"id": "q1", "answer": "A"},
            {"id": "q2", "answer": "C"},
            {"id": "q3", "answer": "B"},
            {"id": "q4", "answer": "D"},
        ]
        answers = [
            {"question_id": "q1", "selected": "A"},
            {"question_id": "q2", "selected": "D"},
            {"question_id": "q3", "selected": "B"},
            {"question_id": "q4", "selected": "C"},
        ]
        result = AssessmentService.grade_quiz(questions, answers)
        assert result["score"] == 0.5
        assert result["correct"] == 2
        assert result["passed"] is False  # 0.5 < 0.6

    def test_empty(self):
        """空题目"""
        result = AssessmentService.grade_quiz([], [])
        assert result["score"] == 0.0
        assert result["total"] == 0

    def test_none_answer(self):
        """未作答"""
        questions = [{"id": "q1", "answer": "A"}]
        answers = [{"question_id": "q1", "selected": ""}]
        result = AssessmentService.grade_quiz(questions, answers)
        assert result["correct"] == 0
        assert result["passed"] is False

    def test_full_text_answer(self):
        """前端提交完整选项文本（A. xxx）vs 后端存字母（A）"""
        questions = [
            {"id": "q1", "answer": "B", "options": ["A. Dennis Ritchie", "B. Bjarne Stroustrup", "C. Ken Thompson"]},
            {"id": "q2", "answer": "C", "options": ["A. 自动管理", "B. 跨平台", "C. 效率灵活", "D. 仅面向对象"]},
        ]
        answers = [
            {"question_id": "q1", "selected": "B. Bjarne Stroustrup"},
            {"question_id": "q2", "selected": "D. 仅面向对象"},
        ]
        result = AssessmentService.grade_quiz(questions, answers)
        assert result["correct"] == 1  # 第1题正确，第2题错误
        assert result["score"] == 0.5


class TestCalculateMastery:
    """掌握度计算测试"""

    def test_first_attempt(self):
        mastery = AssessmentService.calculate_mastery([0.8], 0.0)
        assert 0.3 <= mastery <= 0.6  # 加权后应有提升

    def test_multiple_attempts(self):
        mastery = AssessmentService.calculate_mastery([0.6, 0.8, 0.9], 0.5)
        assert 0.5 <= mastery <= 1.0

    def test_decay(self):
        """随时间衰减"""
        fresh = AssessmentService.calculate_mastery([1.0], 1.0, decay_days=0)
        decayed = AssessmentService.calculate_mastery([1.0], 1.0, decay_days=30)
        assert decayed < fresh

    def test_no_scores(self):
        mastery = AssessmentService.calculate_mastery([], 0.8, decay_days=30)
        assert mastery < 0.8  # 衰减

    def test_clamp_bounds(self):
        mastery = AssessmentService.calculate_mastery([1.0] * 10, 1.0)
        assert mastery <= 1.0

        mastery = AssessmentService.calculate_mastery([0.0] * 10, 0.0)
        assert mastery >= 0.0


class TestOverallProgress:
    """进度计算测试"""

    def test_all_completed(self):
        progresses = [
            {"status": "completed", "mastery": 0.9},
            {"status": "completed", "mastery": 0.8},
        ]
        result = AssessmentService.calculate_overall_progress(progresses)
        assert result["total_nodes"] == 2
        assert result["completed_nodes"] == 2
        assert result["progress_pct"] == 100.0

    def test_partial_progress(self):
        progresses = [
            {"status": "completed", "mastery": 0.8},
            {"status": "learning", "mastery": 0.3},
            {"status": "not_started", "mastery": 0.0},
        ]
        result = AssessmentService.calculate_overall_progress(progresses)
        assert result["total_nodes"] == 3
        assert result["completed_nodes"] == 1
        assert result["progress_pct"] == pytest.approx(33.3, rel=0.1)

    def test_empty(self):
        result = AssessmentService.calculate_overall_progress([])
        assert result["total_nodes"] == 0


class TestNextReview:
    """间隔重复测试"""

    def test_high_mastery_long_interval(self):
        interval = AssessmentService.compute_next_review(0.95, 3)
        assert interval > 30

    def test_low_mastery_short_interval(self):
        interval = AssessmentService.compute_next_review(0.5, 0)
        assert interval <= 3

    def test_review_count_bonus(self):
        first = AssessmentService.compute_next_review(0.8, 0)
        fifth = AssessmentService.compute_next_review(0.8, 5)
        assert fifth > first
