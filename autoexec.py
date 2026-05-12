import win32com.client as win32
import os
import sys

# 用于解决表格部分 根据内容自动调整表格
def auto_fit_all_tables_to_window(doc_path, output_path=None):
    doc_path = os.path.abspath(doc_path)
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"文件不存在: {doc_path}")

    word = win32.gencache.EnsureDispatch('Word.Application')
    word.Visible = False
    doc = word.Documents.Open(doc_path)

    for table in doc.Tables:
        # 2 代表 wdAutoFitWindow（根据窗口自动调整表格）
        table.AutoFitBehavior(2)
        table.AllowAutoFit = True

    out_path = os.path.abspath(output_path) if output_path else doc_path
    doc.SaveAs2(out_path)
    doc.Close()
    word.Quit()
    print(f"处理完成，保存至: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("python autoexec.py <输入文件> [输出文件]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    auto_fit_all_tables_to_window(input_file, output_file)