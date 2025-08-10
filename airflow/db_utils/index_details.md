
### stock_ideas
create one time manually:
```
db.stock_ideas.createIndex(
    { title: 1, publish_date: 1, author: 1 },
    { unique: true, name: "unique_title_date_author" }
)
```

### news
**dedup_key**: automatically created in function merge_news_batch at `airflow/db_utils/push_news.py`
