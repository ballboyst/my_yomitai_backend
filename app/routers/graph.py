from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from ..database import get_db
from ..session_store import sessions
from ..models import Daily_log, My_book, User
from decimal import Decimal

router = APIRouter()

@router.get("/")

def get_reading_statistics(request: Request, period: str, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="未承認またはセッションが無効")

    user_id = sessions[session_id]
    start_date = 0
    japanese_time = datetime.now() + timedelta(hours=9)
    today = japanese_time.date()
    print(f"今日は{today}")


    # 期間の開始基準日を設定
    if period == "weekly":
        start_date = today - timedelta(days = 7)
        print(f"基準日は{start_date}")
    elif period == "monthly":
        start_date = today - timedelta(days = 30)
        print(f"基準日は{start_date}")
    elif period == "yearly":
        start_date = today - timedelta(days = 365)
        print(f"基準日は{start_date}")
    else:
        raise HTTPException(status_code=401,detail="リクエストが無効")


    # モデルを操作し読書日と読書ページのリストを作成する
    if period == "yearly":
        result = db.query(
            extract('year',Daily_log.date).label('year'),
            extract('month',Daily_log.date).label('month'),
            func.sum(Daily_log.page_read).label('total_pages')).join(
                My_book,
                Daily_log.my_book_id == My_book.id).filter(
                My_book.user_id == user_id,
                Daily_log.date >= start_date,
                Daily_log.date <= today).group_by(
                extract('year',Daily_log.date),
                extract('month',Daily_log.date)
                ).all()
        
        existing_date = {(year, month): total_pages for year, month, total_pages in result}
        current_date = start_date  # ここでstart_dateをそのまま使用
        all_month = []

        while current_date <= today:
            year = current_date.year
            month = current_date.month
            all_month.append((year, month))
            # 月を進める
            if month == 12:
                current_date = (datetime(year + 1, 1, 1)).date()  # date型を維持
            else:
                current_date = (datetime(year, month + 1, 1)).date()  # date型を維持

        final_data = []
        for year, month in all_month:
            total_pages = existing_date.get((year, month), Decimal('0'))
            final_data.append((year, month, total_pages))
        print(final_data)

        log_data = [{'date': f"{year}-{month:02}", 'pages': page_read} for year, month, page_read in final_data]
        return(log_data)

    else:
        result = db.query(
            Daily_log.date, func.sum(Daily_log.page_read).label('total_pages')).join(
                My_book,
                Daily_log.my_book_id == My_book.id).filter(
                My_book.user_id == user_id,
                Daily_log.date >= start_date,
                Daily_log.date <= today
                ).group_by(Daily_log.date)
        log_data=[{'date':date, 'pages':pages} for date, pages in result]
        # リスト内の読書日と対象期間を比較し、読書日がなければ読書日と０ページを追加する
        search = start_date
        while search <= today:
            if search not in [entry['date'] for entry in log_data]:
                push_date={'date':search, 'pages':0}
                log_data.append(push_date)
            else:
                pass
            search += timedelta(days = 1)

        # 日付と読書ページを連続データとなるよう整列
        graph_element = sorted(log_data, key=lambda x: x['date'])
        return(graph_element)
