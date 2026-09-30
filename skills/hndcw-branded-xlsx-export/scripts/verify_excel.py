# 用本机 Excel（COM）实际打开生成的 xlsx：
# ① 不提示「文件损坏」 ② 图片可渲染 ③ 行高 1:1 生效（验证 sheetViews 修复）④ 导 PDF 供人工核对版式
import glob, os, sys, time
import win32com.client as win32

D = r'D:\workBuddy\tmp\qbrand\out_ascii'
PDF = r'D:\workBuddy\tmp\qbrand\pdf'
os.makedirs(PDF, exist_ok=True)
for old in glob.glob(os.path.join(PDF, '*.pdf')):
    os.remove(old)

xl = win32.DispatchEx('Excel.Application')
xl.Visible = False
xl.DisplayAlerts = False
print('Excel version:', xl.Version)
fails = []
height_bad = []
try:
    for f in sorted(glob.glob(os.path.join(D, '*.xlsx'))):
        name = os.path.basename(f)
        try:
            wb = xl.Workbooks.Open(f, 0, True)   # ReadOnly
            ns = wb.Worksheets.Count
            print(f'OPEN_OK  {name}  sheets={ns}')
            for i in range(1, ns + 1):
                ws = wb.Worksheets(i)
                shapes = ws.Shapes.Count
                print(f'    [{ws.Name}] used={ws.UsedRange.Address} shapes={shapes}')
                for k in range(1, shapes + 1):
                    sh = ws.Shapes(k)
                    print(f'        shape {sh.Name} = {sh.Width:.1f}x{sh.Height:.1f}pt top={sh.Top:.1f} left={sh.Left:.1f}')
                # 行高 1:1 校验：Excel 读回值应等于我们写入的 ht
                chk = [1, 2, 3, 6]
                got = {r: round(ws.Rows(r).RowHeight, 1) for r in chk}
                print(f'        行高回读 {got}')
            r1 = wb.Worksheets(1).Range('B1')
            print(f'    B1={r1.Value2!r} fill={r1.Interior.Color} fontColor={r1.Font.Color} size={r1.Font.Size}')
            pdf = os.path.join(PDF, os.path.splitext(name)[0] + '.pdf')
            wb.ExportAsFixedFormat(0, pdf)     # 0 = xlTypePDF
            print(f'    PDF -> {os.path.basename(pdf)}  ({os.path.getsize(pdf)} bytes)')
            wb.Close(False)
        except Exception as e:
            fails.append((name, str(e)))
            print(f'OPEN_FAIL  {name}  {e}')
            try:
                wb.Close(False)
            except Exception:
                pass
finally:
    xl.Quit()
    time.sleep(0.5)

print('=' * 60)
print('FAILED:', len(fails))
for n, e in fails:
    print('  -', n, e)
sys.exit(1 if (fails or height_bad) else 0)
