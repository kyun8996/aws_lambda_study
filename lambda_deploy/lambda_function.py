import os
import csv
import io
import json
import time
import random
import boto3
import requests
from datetime import datetime, timedelta

# ✅ Slack Webhook URL (환경 변수로 관리)
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]

s3 = boto3.client("s3")


# ---------------------------------------------------
# 📘 1. Slack 메시지 전송 함수
# ---------------------------------------------------
def send_slack(message: str, blocks: list | None = None):
    """Slack Webhook으로 메시지 전송"""
    payload = {"text": message}
    if blocks:
        payload["blocks"] = blocks

    resp = requests.post(
        WEBHOOK_URL,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return True


# ---------------------------------------------------
# 📘 2. 환율 데이터 수집 함수
# ---------------------------------------------------
def collect_exchange_rate(start_date_str: str, end_date_str: str):
    """Frankfurter API를 통해 USD→KRW 환율 데이터 수집"""
    records = []
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    current_date = start_date

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        url = f"https://api.frankfurter.dev/v1/{date_str}?base=USD&symbols=KRW"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("date") == date_str:
                records.append({
                    "요청시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "환율 날짜": data["date"],
                    "환율": data["rates"]["KRW"]
                })
                time.sleep(random.uniform(1, 2))

        except requests.exceptions.RequestException as e:
            print(f"⚠️ {date_str} 데이터 수집 오류: {e}")
            send_slack(f"⚠️ {date_str} 데이터 수집 오류: {e}")

        current_date += timedelta(days=1)

    return records


# ---------------------------------------------------
# 📘 3. CSV를 버퍼에 저장 후 S3 업로드
# ---------------------------------------------------
def save_to_s3(records, start_date_str, end_date_str):
    """수집된 환율 데이터를 CSV로 변환 후 S3에 업로드"""
    if not records:
        raise ValueError("수집된 데이터가 없습니다.")

    # CSV 버퍼 생성
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=["요청시간", "환율 날짜", "환율"])
    writer.writeheader()
    writer.writerows(records)

    # 파일명 및 경로
    file_name = f"{start_date_str}__{end_date_str}_fxdata.csv"
    s3_path = f"exchange_rate/{file_name}"

    # 업로드
    s3.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_path,
        Body=csv_buffer.getvalue(),
        ContentType="text/csv"
    )

    send_slack(f"✅ 환율 CSV 업로드 완료: s3://{S3_BUCKET_NAME}/{s3_path}")
    return s3_path


# ---------------------------------------------------
# 📘 4. Lambda 메인 핸들러
# ---------------------------------------------------
def lambda_handler(event, context):
    """Lambda 엔트리 포인트"""
    try:
        start_date_str = event.get("start_date", "2025-10-01")
        end_date_str = event.get("end_date", "2025-10-05")

        send_slack("🚀 Lambda 환율 수집 작업을 시작합니다.")

        records = collect_exchange_rate(start_date_str, end_date_str)
        s3_path = save_to_s3(records, start_date_str, end_date_str)

        send_slack(f"🎯 Lambda 작업 완료: {len(records)}건 수집됨")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Lambda 실행 완료",
                "s3_path": s3_path,
                "record_count": len(records)
            })
        }

    except Exception as e:
        send_slack(f"❌ Lambda 실행 오류: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
