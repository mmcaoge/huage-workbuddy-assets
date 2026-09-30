import sqlite3, time, sys
c = sqlite3.connect('/www/wwwroot/hndcw.com/data/hndcw.db', timeout=60)
c.row_factory = sqlite3.Row

def t(label, sql, args=()):
    t0 = time.time()
    try:
        rows = c.execute(sql, args).fetchall()
        print(f'{label}: {(time.time()-t0)*1000:.0f}ms rows={len(rows)}')
    except Exception as e:
        print(f'{label}: ERR {e}')
    return rows

kw = '%湖南广鑫人力资源服务有限公司%'
print('--- 当前路由用到的查询 ---')
t('① investor LIKE 聚合(带计算列)', """
SELECT CASE WHEN investor LIKE '%公司' THEN rtrim(substr(investor,1,length(investor)-2)) ELSE investor END as nm,
       count(*) c, coalesce(sum(budget_amount),0) s
FROM projects WHERE status=1 AND investor LIKE ? GROUP BY nm ORDER BY c DESC LIMIT 40""", (kw,))
t('② owner_unit LIKE 聚合', "SELECT owner_unit as nm, count(*) c, coalesce(sum(budget_amount),0) s FROM projects WHERE status=1 AND owner_unit LIKE ? GROUP BY nm ORDER BY c DESC LIMIT 40", (kw,))
t('③ 精确匹配 owner_unit', "SELECT * FROM projects WHERE status=1 AND owner_unit = ? ORDER BY publish_date DESC LIMIT 5", ('湖南广鑫人力资源服务有限公司',))

print('\n--- 试算「先查名字、再按名字聚合」是否更快 ---')
t('④ 先取匹配名字(仅索引列)', "SELECT DISTINCT owner_unit FROM projects WHERE status=1 AND owner_unit LIKE ? LIMIT 50", (kw,))
t('⑤ 纯索引扫描计数', "SELECT count(*) FROM projects WHERE status=1 AND owner_unit LIKE ?", (kw,))
t('⑥ 全表 count(*)', "SELECT count(*) FROM projects")

print('\n--- EXPLAIN 计划 ---')
for label, sql, args in [
    ('①', "SELECT CASE WHEN investor LIKE '%公司' THEN rtrim(substr(investor,1,length(investor)-2)) ELSE investor END as nm, count(*) c FROM projects WHERE status=1 AND investor LIKE ? GROUP BY nm ORDER BY c DESC LIMIT 40", (kw,)),
    ('②', "SELECT owner_unit as nm, count(*) c FROM projects WHERE status=1 AND owner_unit LIKE ? GROUP BY nm ORDER BY c DESC LIMIT 40", (kw,)),
]:
    print(label, [dict(r) if hasattr(r, 'keys') else tuple(r) for r in c.execute('EXPLAIN QUERY PLAN ' + sql, args)])
c.close()
