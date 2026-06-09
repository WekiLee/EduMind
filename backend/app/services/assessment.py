"""评估引擎 —— 出题、判卷、掌握度计算"""

import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.adapter import LLMAdapter
from app.models.quiz import QuizAttempt


class AssessmentService:
    """评估引擎：题目生成 + 答案评判 + 掌握度模型"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMAdapter()

    # ── 出题 ──

    async def generate_quiz(self, node: dict, domain_profile: dict) -> dict:
        """生成测验"""
        return await self.llm.generate_quiz(node, domain_profile)

    # ── 判卷 ──

    @staticmethod
    def grade_quiz(questions: list[dict], answers: list[dict]) -> dict:
        """
        判卷。
        questions: [{"id": "q1", "answer": "C", "options": ["A. ...", ...]}, ...]
        answers:   [{"question_id": "q1", "selected": "A. ..."}, ...]

        注意：前端提交的是完整选项文本（"A. xxx"），后端存储的答案可能是
        字母（"A"）或完整文本，需要兼容比较。
        """
        answer_map = {}
        for a in answers:
            qid = a.get("question_id", "")
            if qid:
                answer_map[qid] = a.get("selected", "")
        results = []
        correct_count = 0

        for q in questions:
            qid = q.get("id", "")
            if not qid:
                continue
            selected = (answer_map.get(qid, "") or "").strip()
            correct = (q.get("answer", "") or "").strip()

            # 兼容比较：支持 "A" == "A"、"A. xxx" == "A"、"A" == "A. xxx"
            selected_letter = selected[0] if selected and selected[0].isalpha() else selected
            correct_letter = correct[0] if correct and correct[0].isalpha() else correct

            is_correct = selected == correct or selected_letter == correct_letter

            if is_correct:
                correct_count += 1
            results.append(
                {
                    "question_id": qid,
                    "correct": is_correct,
                    "correct_answer": correct,
                }
            )

        total = len(questions)
        score = correct_count / total if total > 0 else 0

        return {
            "score": round(score, 2),
            "total": total,
            "correct": correct_count,
            "passed": score >= 0.6,
            "results": results,
        }

    # ── 掌握度计算 ──

    @staticmethod
    def calculate_mastery(
        quiz_scores: list[float],
        current_mastery: float = 0.0,
        decay_days: float = 0.0,
    ) -> float:
        """
        基于艾宾浩斯遗忘曲线 + 加权平均计算掌握度。

        公式：
        - 新掌握度 = 加权平均(最近 N 次测验成绩)
        - 每次新测验权重递增（最近一次权重最高）
        - 如果不复习，掌握度按指数衰减：mastery * e^(-decay_days / 30)

        Args:
            quiz_scores: 历次测验得分 [0.8, 0.6, 0.9]
            current_mastery: 当前掌握度
            decay_days: 距离上次复习的天数

        Returns:
            0.0 ~ 1.0 的掌握度
        """
        if not quiz_scores:
            return current_mastery * math.exp(-decay_days / 30)

        # 加权平均（最近权重越高）
        n = len(quiz_scores)
        weights = [i + 1 for i in range(n)]
        weighted_avg = sum(s * w for s, w in zip(quiz_scores, weights, strict=False)) / sum(weights)

        # 与旧掌握度融合（新成绩占 60%，旧掌握度占 40%）
        new_mastery = 0.6 * weighted_avg + 0.4 * current_mastery

        # 衰减
        decayed = new_mastery * math.exp(-decay_days / 30)

        return round(min(max(decayed, 0.0), 1.0), 2)

    # ── 进度计算 ──

    @staticmethod
    def calculate_overall_progress(
        node_progress_list: list[dict],
    ) -> dict:
        """
        计算路径整体进度。
        node_progress_list: [{"status": "completed", "mastery": 0.8}, ...]
        """
        total = len(node_progress_list)
        if total == 0:
            return {
                "total_nodes": 0,
                "completed_nodes": 0,
                "progress_pct": 0,
                "overall_mastery": 0.0,
            }

        completed = sum(1 for np in node_progress_list if np.get("status") == "completed")
        total_mastery = sum(np.get("mastery", 0.0) or 0.0 for np in node_progress_list)

        return {
            "total_nodes": total,
            "completed_nodes": completed,
            "progress_pct": round(completed / total * 100, 1),
            "overall_mastery": round(total_mastery / total, 2),
        }

    # ── 间隔重复 ──

    @staticmethod
    def compute_next_review(mastery: float, review_count: int) -> float:
        """
        计算下次复习的间隔天数。
        - mastery 越高 → 间隔越长
        - review_count 越多 → 间隔越长
        """
        base_days = 1
        if mastery >= 0.9:
            multiplier = 30
        elif mastery >= 0.8:
            multiplier = 14
        elif mastery >= 0.7:
            multiplier = 7
        elif mastery >= 0.6:
            multiplier = 3
        else:
            multiplier = 1

        # 复习次数加成
        count_bonus = 1 + review_count * 0.5
        return base_days * multiplier * count_bonus

    # ── 数据库操作 ──

    async def save_attempt(
        self,
        user_id: str,
        path_id: str,
        node_id: str,
        score: float,
        total: int,
        correct: int,
        answers: list[dict],
    ) -> QuizAttempt:
        """保存测验记录"""
        attempt = QuizAttempt(
            user_id=user_id,
            path_id=path_id,
            node_id=node_id,
            score=score,
            total_questions=total,
            correct_count=correct,
            answers=answers,
        )
        self.db.add(attempt)
        await self.db.flush()
        return attempt

    # ── 掌握度快照 ──

    @staticmethod
    async def take_mastery_snapshot(
        db: AsyncSession,
        user_id: str,
        path_id: str,
    ):
        """记录当前路径的掌握度快照（用于趋势分析）"""
        try:
            from sqlalchemy import select

            from app.models.progress import NodeProgress
            from app.models.snapshot import MasterySnapshot

            result = await db.execute(
                select(NodeProgress).where(
                    NodeProgress.user_id == user_id,
                    NodeProgress.path_id == path_id,
                )
            )
            progress_list = [np.to_dict() for np in result.scalars().all()]

            # 构建快照：按节点粒度记录 mastery，同时计算模块聚合
            snapshot = {
                "overall_mastery": 0.0,
                "completed_nodes": 0,
                "total_nodes": len(progress_list),
                "nodes": [],
            }
            if progress_list:
                total_mastery = 0
                for p in progress_list:
                    m = p.get("mastery", 0) or 0
                    total_mastery += m
                    snapshot["nodes"].append({
                        "node_id": p.get("node_id", ""),
                        "mastery": m,
                        "status": p.get("status", ""),
                    })
                    if p.get("status") == "completed":
                        snapshot["completed_nodes"] += 1
                snapshot["overall_mastery"] = round(total_mastery / len(progress_list), 2)

            snap = MasterySnapshot(
                user_id=user_id,
                path_id=path_id,
                snapshot=snapshot,
            )
            db.add(snap)
            await db.flush()
        except Exception as e:
            print(f"  ⚠️  掌握度快照记录跳过: {e}")

