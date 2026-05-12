"""
test_com.py - 极简 COM 测试：只打开→保存→关闭
"""
import win32com.client as win32
import sys

doc_path = sys.argv[1]
print(f"打开: {doc_path}")

word = win32.Dispatch("Word.Application")
word.Visible = False
word.DisplayAlerts = False

doc = word.Documents.Open(doc_path)
print("打开成功")

out_path = sys.argv[2] if len(sys.argv) > 2 else doc_path
doc.SaveAs2(out_path)
print(f"保存: {out_path}")

doc.Close()
word.Quit()
print("完成")
