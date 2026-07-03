图标说明
========

当前 build_desktop.bat 中使用了 --icon=icon.ico 参数。

由于尚未提供实际的 .ico 图标文件，打包时 PyInstaller 会使用默认图标。

如需自定义图标，请按以下步骤操作：

1. 准备一个 256x256 或 512x512 的 PNG 图片
2. 使用在线工具或 imagemagick 转换为 .ico 格式：
   - 在线工具: https://convertio.co/png-ico/
   - 命令行: magick convert icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
3. 将生成的 icon.ico 放在项目根目录（与 desktop_app.py 同级）
4. 重新运行 build_desktop.bat 即可

图标设计建议：
- 主色调：蓝色/紫色渐变，体现科技感
- 图形元素：购物袋、对话气泡、AI 芯片 组合
- 风格：简洁扁平化，避免过于复杂的细节
- 格式：.ico 包含 256x256、128x128、64x64、48x48、32x32、16x16 多尺寸

暂时可以先用任意 256x256 PNG 转成 icon.ico 使用。
