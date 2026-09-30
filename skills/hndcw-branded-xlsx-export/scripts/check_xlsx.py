# 用 openpyxl 严格解析生成的 xlsx：结构 / 图片 / 合并 / 行高 / 样式
import glob, os, sys
from openpyxl import load_workbook

files = sorted(glob.glob('out/*.xlsx'))
fail = 0
for f in files:
    try:
        wb = load_workbook(f)
    except Exception as e:
        print('✗ 解析失败', f, e); fail += 1; continue
    print('=' * 78)
    print('✓', os.path.basename(f), '|', len(wb.sheetnames), '工作表:', wb.sheetnames)
    for ws in wb.worksheets:
        imgs = getattr(ws, '_images', [])
        print(f'  [{ws.title}] 尺寸 {ws.max_row}行 × {ws.max_column}列 | 图片 {len(imgs)} 张 | 合并 {len(ws.merged_cells.ranges)} 处')
        if imgs:
            im = imgs[0]
            print(f'      图片: {im.width:.0f}×{im.height:.0f}px 锚点 {im.anchor._from.col},{im.anchor._from.row}')
        # 打印前 6 行内容摘要
        for r in range(1, min(ws.max_row, 7) + 1):
            vals = []
            for c in range(1, min(ws.max_column, 7) + 1):
                cell = ws.cell(row=r, column=c)
                v = cell.value
                if v not in (None, ''):
                    vals.append(f'{cell.coordinate}={str(v)[:34]}')
            h = ws.row_dimensions[r].height
            print(f'      r{r}(h={h if h else "-"}) ' + ' | '.join(vals))
        # 表尾 4 行
        for r in range(max(1, ws.max_row - 3), ws.max_row + 1):
            vals = []
            for c in range(1, min(ws.max_column, 7) + 1):
                v = ws.cell(row=r, column=c).value
                if v not in (None, ''):
                    vals.append(f'{ws.cell(row=r,column=c).coordinate}={str(v)[:56]}')
            if vals:
                print(f'      r{r} ' + ' | '.join(vals))
    wb.close()

print('=' * 78)
print('失败文件数:', fail)
sys.exit(1 if fail else 0)
