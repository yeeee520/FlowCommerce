"""验证新简历内容"""
import os, re, zipfile

desktop = r"C:\Users\yeeee\Desktop"
path = os.path.join(desktop, "求职简历", "yeeee", "叶泳君_简历_优化版.docx")

# 读取 docx 中的文本
texts = []
with zipfile.ZipFile(path) as z:
    with z.open("word/document.xml") as f:
        content = f.read().decode("utf-8")
        texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', content)

full_text = "".join(texts)
print("=" * 60)
print("简历文本内容预览:")
print("=" * 60)
# Print in chunks for readability
for i in range(0, len(full_text), 200):
    print(full_text[i:i+200])
