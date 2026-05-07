"""
Creator Experiment Engine
クリエイター実験データの記録・分析エンジン
Lost Fauna等のクリエイター向け実験管理システム
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

class Platform(str, Enum):
    ETSY = "etsy"
    SUZURI = "suzuri"
    PINTEREST = "pinterest"
    X = "x"

class ChangeType(str, Enum):
    TITLE = "title"
    DESCRIPTION = "description"
    TAGS = "tags"
    PRICE = "price"
    IMAGE = "image"

class Metric(str, Enum):
    VIEWS = "views"
    SALES = "sales"
    CLICKS = "clicks"
    FOLLOWERS = "followers"

class Verdict(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class ExperimentEngine:
    """Creator experiment management and analysis engine"""

    def __init__(self):
        self.experiments = []
        self.results = []

    def create_experiment(self,
                         shop: str,
                         platform: Platform,
                         change_type: ChangeType,
                         before: Dict[str, Any],
                         after: Dict[str, Any],
                         date: str = None) -> str:
        """Create a new experiment record"""

        experiment_id = str(uuid.uuid4())
        experiment_date = datetime.fromisoformat(date) if date else datetime.now()

        experiment = {
            "experiment_id": experiment_id,
            "shop": shop,
            "platform": platform.value,
            "change_type": change_type.value,
            "before": before,
            "after": after,
            "date": experiment_date.isoformat(),
            "created_at": datetime.now().isoformat()
        }

        self.experiments.append(experiment)
        return experiment_id

    def record_result(self,
                     experiment_id: str,
                     metric: Metric,
                     before_value: float,
                     after_value: float,
                     measurement_date: str = None) -> Dict[str, Any]:
        """Record experiment result and calculate improvement"""

        improvement = after_value - before_value
        improvement_percent = (improvement / before_value * 100) if before_value > 0 else 0

        # Determine verdict based on improvement
        if improvement_percent >= 10:
            verdict = Verdict.POSITIVE
        elif improvement_percent <= -10:
            verdict = Verdict.NEGATIVE
        else:
            verdict = Verdict.NEUTRAL

        measure_date = datetime.fromisoformat(measurement_date) if measurement_date else datetime.now()

        result = {
            "experiment_id": experiment_id,
            "metric": metric.value,
            "before_value": before_value,
            "after_value": after_value,
            "improvement_percent": round(improvement_percent, 2),
            "verdict": verdict.value,
            "measurement_date": measure_date.isoformat()
        }

        self.results.append(result)
        return result

    def get_experiment_history(self, shop: str = None, platform: str = None) -> List[Dict[str, Any]]:
        """Get experiment history with optional filtering"""

        filtered_experiments = self.experiments

        if shop:
            filtered_experiments = [exp for exp in filtered_experiments if exp["shop"] == shop]

        if platform:
            filtered_experiments = [exp for exp in filtered_experiments if exp["platform"] == platform]

        # Add results to each experiment
        for experiment in filtered_experiments:
            exp_id = experiment["experiment_id"]
            experiment["results"] = [r for r in self.results if r["experiment_id"] == exp_id]

        return filtered_experiments

    def analyze_patterns(self, shop: str = None) -> Dict[str, Any]:
        """Analyze success patterns from experiment data"""

        experiments = self.get_experiment_history(shop=shop)

        if not experiments:
            return {"message": "No experiments found", "patterns": []}

        # Analyze by platform
        platform_analysis = {}
        change_type_analysis = {}

        for exp in experiments:
            platform = exp["platform"]
            change_type = exp["change_type"]

            if platform not in platform_analysis:
                platform_analysis[platform] = {"total": 0, "positive": 0, "negative": 0, "neutral": 0}

            if change_type not in change_type_analysis:
                change_type_analysis[change_type] = {"total": 0, "positive": 0, "negative": 0, "neutral": 0}

            for result in exp.get("results", []):
                verdict = result["verdict"]

                platform_analysis[platform]["total"] += 1
                platform_analysis[platform][verdict] += 1

                change_type_analysis[change_type]["total"] += 1
                change_type_analysis[change_type][verdict] += 1

        # Calculate success rates
        for platform_data in platform_analysis.values():
            if platform_data["total"] > 0:
                platform_data["success_rate"] = platform_data["positive"] / platform_data["total"] * 100

        for change_data in change_type_analysis.values():
            if change_data["total"] > 0:
                change_data["success_rate"] = change_data["positive"] / change_data["total"] * 100

        return {
            "platform_patterns": platform_analysis,
            "change_type_patterns": change_type_analysis,
            "total_experiments": len(experiments),
            "analysis_date": datetime.now().isoformat()
        }

    def get_recommendations(self, shop: str) -> List[Dict[str, Any]]:
        """Get personalized recommendations based on experiment history"""

        patterns = self.analyze_patterns(shop=shop)
        recommendations = []

        # Platform recommendations
        platform_patterns = patterns.get("platform_patterns", {})
        best_platform = max(platform_patterns.keys(),
                          key=lambda x: platform_patterns[x].get("success_rate", 0)) if platform_patterns else None

        if best_platform:
            recommendations.append({
                "type": "platform_focus",
                "recommendation": f"{best_platform}での実験継続を推奨",
                "reason": f"成功率{platform_patterns[best_platform].get('success_rate', 0):.1f}%",
                "priority": 1
            })

        # Change type recommendations
        change_patterns = patterns.get("change_type_patterns", {})
        best_change = max(change_patterns.keys(),
                         key=lambda x: change_patterns[x].get("success_rate", 0)) if change_patterns else None

        if best_change:
            recommendations.append({
                "type": "change_focus",
                "recommendation": f"{best_change}の改善に集中することを推奨",
                "reason": f"成功率{change_patterns[best_change].get('success_rate', 0):.1f}%",
                "priority": 2
            })

        # Lost Fauna specific recommendations
        if shop.lower() == "lost_fauna":
            recommendations.extend([
                {
                    "type": "niche_art_strategy",
                    "recommendation": "ニッチアート向け季節限定作品の実験",
                    "reason": "アート系クリエイター向けの季節性活用",
                    "priority": 3
                },
                {
                    "type": "community_building",
                    "recommendation": "Xでの制作過程共有実験",
                    "reason": "ファンとのエンゲージメント向上",
                    "priority": 4
                }
            ])

        return recommendations

    def simulate_experiment(self,
                          shop: str,
                          platform: Platform,
                          change_type: ChangeType,
                          current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Simulate potential experiment outcomes based on historical data"""

        # Get historical success rates for this combination
        patterns = self.analyze_patterns(shop=shop)

        platform_success = patterns.get("platform_patterns", {}).get(platform.value, {}).get("success_rate", 50.0)
        change_success = patterns.get("change_type_patterns", {}).get(change_type.value, {}).get("success_rate", 50.0)

        # Combined probability
        combined_success_rate = (platform_success + change_success) / 2

        # Simulate potential outcomes
        simulation = {
            "experiment_config": {
                "shop": shop,
                "platform": platform.value,
                "change_type": change_type.value
            },
            "success_probability": round(combined_success_rate, 1),
            "estimated_outcomes": {}
        }

        # Estimate improvements for each metric
        for metric, current_value in current_metrics.items():
            if combined_success_rate >= 60:
                # High success probability
                min_improvement = current_value * 0.15
                max_improvement = current_value * 0.40
            elif combined_success_rate >= 40:
                # Medium success probability
                min_improvement = current_value * 0.05
                max_improvement = current_value * 0.25
            else:
                # Low success probability
                min_improvement = current_value * -0.10
                max_improvement = current_value * 0.15

            simulation["estimated_outcomes"][metric] = {
                "current": current_value,
                "min_expected": round(current_value + min_improvement),
                "max_expected": round(current_value + max_improvement),
                "improvement_range": f"{min_improvement/current_value*100:.1f}% - {max_improvement/current_value*100:.1f}%"
            }

        return simulation

    def export_data(self, shop: str = None) -> Dict[str, Any]:
        """Export experiment data for analysis"""

        experiments = self.get_experiment_history(shop=shop)

        return {
            "experiments": experiments,
            "summary": {
                "total_experiments": len(experiments),
                "total_results": len(self.results),
                "shop_filter": shop,
                "exported_at": datetime.now().isoformat()
            },
            "patterns": self.analyze_patterns(shop=shop)
        }