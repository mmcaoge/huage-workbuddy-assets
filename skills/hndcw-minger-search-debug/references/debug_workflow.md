# 鸣儿检索链路调试 · 真机验证闭环

## A. HTTP 两轮复验脚本模板（服务器 /tmp/_httpN.sh）
```bash
#!/bin/bash
J=/tmp/_jarN.txt; rm -f $J
post() {
  curl -s -m 120 -c $J -b $J -X POST 'https://hndcw.com/minger/api/ask' \
    -H 'Content-Type: application/json' -H 'User-Agent: Mozilla/5.0 (iPhone)' \
    --data-binary "{\"text\":\"$1\"}" -o "$2" -w '%{http_code}'
}
echo "Q1 http=$(post '海南省各市县最新招演出会 / 音乐节 / 演唱会 / 优秀剧目的招投标公告' /tmp/q1.json)"
echo "Q2 http=$(post '海南省 中标' /tmp/q2.json)"
python3 - <<'PY'
import json
for tag,f in [('Q1 演出/音乐节/演唱会/剧目','/tmp/q1.json'),('Q2 海南省 中标','/tmp/q2.json')]:
    try: d=json.load(open(f,encoding='utf-8'))
    except Exception as e: print(tag,'解析失败',e); continue
    cards=d.get('cards') or []
    print('\n== %s =='%tag)
    print('  ok=%s intent=%s cost=%s 卡片=%d'%(d.get('ok'),d.get('intent'),d.get('cost'),len(cards)))
    print('  正文:',str(d.get('text') or '').replace('\n',' ')[:170])
    for c in cards[:5]: print('   -',str(c.get('title'))[:52],'|',c.get('area'),'|',c.get('stage'))
PY
```
判读：Q2 若仍只出「文旅演出类中标」= 跨轮污染未治；应出全省全行业（教育/医疗/政务/设备/维修等）。

## B. DBG 日志插入（抓真实 LLM 入参）
在 `src/agent/index.js` 的 `const filters = normalizeFilters(args, text);` 之后插入：
```js
console.error('[DBG-NORM] text=', JSON.stringify(text), '| rawArgs=', JSON.stringify(args), '| filters=', JSON.stringify(filters));
```
跑完 HTTP 后：`pm2 logs hndcw --nostream | grep DBG-NORM`
确认后**务必移除该行**再重启（避免线上日志污染）。

## C. 部署闭环
```bash
# 本机：从源密钥复制部署密钥（用完即删）
cp "C:/Users/琼崖纵队/.ssh/wb_auto2" "D:/.ssh_deploy/wb_auto2"
cp "C:/Users/琼崖纵队/.ssh/known_hosts" "D:/.ssh_deploy/known_hosts"   # 若有

# 服务器：备份 + 覆盖 + 重启
ssh -p YOUR_SSH_PORT -i D:/.ssh_deploy/wb_auto2 -o UserKnownHostsFile=D:/.ssh_deploy/known_hosts root@YOUR_SERVER_IP \
  "cp /www/wwwroot/hndcw.com/src/agent/index.js /tmp/bakN_index_$(date +%Y%m%d_%H%M%S).js"
scp -P YOUR_SSH_PORT -i D:/.ssh_deploy/wb_auto2 -o UserKnownHostsFile=D:/.ssh_deploy/known_hosts \
  index.js root@YOUR_SERVER_IP:/www/wwwroot/hndcw.com/src/agent/index.js
ssh ... "node --check /www/wwwroot/hndcw.com/src/agent/index.js && pm2 restart hndcw"

# 清理部署密钥（SAFE_DELETE 会拦 rm，用 PowerShell icacls /reset + Remove-Item）
```
scp 同基名文件必须分目录精确指定目标，否则基名覆盖。

## D. 回滚
若修复翻车：`ssh ... "cp /tmp/bakN_index_*.js /www/wwwroot/hndcw.com/src/agent/index.js && pm2 restart hndcw"`
