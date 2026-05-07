"""
Test script for Creator Experiment Log API
Lost Fauna用テストスクリプト
"""

import asyncio
import json
from datetime import datetime
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_lost_fauna_experiment():
    """Lost Faunaの実験作成テスト"""
    print("=== Lost Fauna実験作成テスト ===")

    # Lost Faunaのタイトル変更実験をテスト
    experiment_data = {
        "shop": "lost_fauna",
        "platform": "etsy",
        "change_type": "title",
        "before": {
            "title": "Cute Animal Art Print",
            "views": 120,
            "sales": 2
        },
        "after": {
            "title": "Lost Fauna - Mystical Forest Creature Art Print",
            "views": 0,  # 実験開始時点
            "sales": 0
        },
        "date": "2024-03-15T10:00:00"
    }

    response = client.post("/api/experiment/create", json=experiment_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        return response.json()["experiment_id"]
    return None

def test_record_experiment_result(experiment_id):
    """実験結果記録テスト"""
    print("\n=== 実験結果記録テスト ===")

    # 1週間後の結果を記録
    result_data = {
        "experiment_id": experiment_id,
        "metric": "views",
        "before_value": 120.0,
        "after_value": 180.0,
        "measurement_date": "2024-03-22T10:00:00"
    }

    response = client.post("/api/experiment/result", json=result_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    # sales結果も記録
    sales_result = {
        "experiment_id": experiment_id,
        "metric": "sales",
        "before_value": 2.0,
        "after_value": 5.0,
        "measurement_date": "2024-03-22T10:00:00"
    }

    response2 = client.post("/api/experiment/result", json=sales_result)
    print(f"Sales Result - Status Code: {response2.status_code}")
    print(f"Sales Response: {response2.json()}")

def test_get_history():
    """実験履歴取得テスト"""
    print("\n=== 実験履歴取得テスト ===")

    # lost_faunaの履歴を取得
    response = client.get("/api/experiment/history?shop=lost_fauna")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"実験数: {data['total_count']}")

        for i, exp in enumerate(data['experiments'][:2]):  # 最初の2つを表示
            print(f"\n実験 {i+1}:")
            print(f"  ID: {exp['experiment_id']}")
            print(f"  Shop: {exp['shop']}")
            print(f"  Platform: {exp['platform']}")
            print(f"  Change: {exp['change_type']}")
            print(f"  Results: {len(exp['results'])}件")

def test_health_check():
    """ヘルスチェックテスト"""
    print("\n=== ヘルスチェックテスト ===")

    response = client.get("/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_multiple_platform_experiments():
    """複数プラットフォーム実験テスト"""
    print("\n=== 複数プラットフォーム実験テスト ===")

    # Suzuriでの画像変更実験
    suzuri_exp = {
        "shop": "lost_fauna",
        "platform": "suzuri",
        "change_type": "image",
        "before": {"image_style": "simple", "colors": 3},
        "after": {"image_style": "detailed", "colors": 5},
        "date": "2024-03-20T12:00:00"
    }

    response = client.post("/api/experiment/create", json=suzuri_exp)
    print(f"Suzuri実験 - Status: {response.status_code}")

    # Pinterestでのタグ変更実験
    pinterest_exp = {
        "shop": "lost_fauna",
        "platform": "pinterest",
        "change_type": "tags",
        "before": {"tags": ["art", "animal", "cute"]},
        "after": {"tags": ["mystical", "forest", "creature", "art", "nature", "fantasy"]},
        "date": "2024-03-21T14:00:00"
    }

    response2 = client.post("/api/experiment/create", json=pinterest_exp)
    print(f"Pinterest実験 - Status: {response2.status_code}")

def main():
    """メインテスト実行"""
    print("Creator Experiment Log API テスト開始")
    print("=" * 50)

    # ヘルスチェック
    test_health_check()

    # Lost Fauna実験作成
    experiment_id = test_create_lost_fauna_experiment()

    if experiment_id:
        # 結果記録
        test_record_experiment_result(experiment_id)

    # 複数プラットフォーム実験
    test_multiple_platform_experiments()

    # 履歴取得
    test_get_history()

    print("\n" + "=" * 50)
    print("テスト完了!")

if __name__ == "__main__":
    main()