#!/bin/bash
# ============================================================
# 海南「社会调查类」公告 · 周采集全链路
# ------------------------------------------------------------
# 采集（站群 SSI 44 站点 + 站群外独立县市 6 站）
#   → 合并过滤（组合短语判定，剔除新闻/补贴公示/工程检测）
#   → 入库（source_url 幂等，追加 sector='社会调查'）
#   → 刷新汇总表（前台 /projects/list?sector=社会调查 依赖 stats_group）
#
# 挂载：crontab  0 7 * * 1   （每周一 07:00）
#   ⚠️ 时段选择依据（2026-09-17 实测 crontab）：该服务器 cron 极密集，
#      collect_region 全天 24 小时每 20 分钟（21 省轮转）写一次 hndcw 库，
#      另有 21:10 clean_winner / 21:20+22:45 collect_details / 10:15 collect_incremental
#      / 09:00+13:00+19:00+23:30 refresh_stats 等写入任务 —— **不存在完全空闲时段**。
#      故：时段只是"相对较轻"（选周一 07:00），真正的并发安全靠
#      SQLite WAL + import_survey 的 busy_timeout=30s（与既有 collect_incremental
#      并发场景相同）；下面的等待逻辑仅作轻量避让，不作为正确性依赖。
# 手动跑：cd /www/wwwroot/hndcw.com && bash tools/survey_weekly.sh
# 日志：  logs/survey_weekly.log
# ============================================================
set -u
cd /www/wwwroot/hndcw.com || exit 1

LOG=logs/survey_weekly.log
PY=/usr/bin/python3
NODE=/usr/bin/node
WEEK=$(date +%Y%m%d)
ARC=data/survey_weekly

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

mkdir -p "$ARC" logs
log "========== 周采集开始（$WEEK）=========="

# 轻量避让：若恰好撞上 region 采集（每 20 分钟一轮），稍等再开工
for i in 1 2 3; do
    pgrep -f collect_region.py >/dev/null 2>&1 || break
    log "检测到 collect_region.py 正在运行，等待 60s（第 $i 次）"
    sleep 60
done

# 0) 归档清理：filtered 产物保留 28 天
find "$ARC" -name 'filtered_*.jsonl' -mtime +28 -delete 2>/dev/null

# 1) 站群 SSI（44 站点：12 市县 + 省厅局）
log "--- 1/5 站群 SSI 采集 ---"
MAX_PAGE=2 PAGE_SIZE=50 SLEEP=0.6 WORKERS=4 $PY -u tools/collect_survey_gov.py >> "$LOG" 2>&1
log "    -> 退出码 $?  累计 $(wc -l < data/survey_gov_raw.jsonl 2>/dev/null) 条"

# 2) 站群外独立系统县市（文昌/五指山/乐东/昌江/三亚/海口）
log "--- 2/5 独立县市采集 ---"
MAX_PAGE=2 PAGE_SIZE=50 SLEEP=0.45 WORKERS=3 $PY -u tools/collect_survey_indep.py >> "$LOG" 2>&1
log "    -> 退出码 $?  累计 $(wc -l < data/survey_indep_raw.jsonl 2>/dev/null) 条"

# 3) 合并过滤（两来源一起过滤，跨源 url 去重）
log "--- 3/5 合并过滤 ---"
RAW=data/survey_gov_raw.jsonl,data/survey_indep_raw.jsonl \
OUT="$ARC/filtered_$WEEK.jsonl" \
$PY -u tools/survey_filter.py >> "$LOG" 2>&1
log "    -> 退出码 $?  产出 $(wc -l < "$ARC/filtered_$WEEK.jsonl" 2>/dev/null) 条"

# 4) 入库（--no-backup：整库 600MB+ 不适合每周备份）
log "--- 4/5 入库 ---"
SRC="$ARC/filtered_$WEEK.jsonl" $PY -u tools/import_survey.py --no-backup >> "$LOG" 2>&1
log "    -> 退出码 $?"

# 5) 刷新汇总表
log "--- 5/5 刷新汇总表 ---"
$NODE tools/refresh_stats.mjs >> "$LOG" 2>&1
log "    -> 退出码 $?"

log "库内 sector=社会调查 共 $(sqlite3 data/hndcw.db "SELECT count(*) FROM projects WHERE sector='社会调查';" 2>/dev/null) 条"
log "========== 周采集结束 =========="
