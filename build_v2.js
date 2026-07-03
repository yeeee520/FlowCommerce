const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  LevelFormat, ImageRun, TabStopType, TabStopPosition
} = require('docx');

// ============================================================
// 样式定义
// ============================================================
const COLORS = {
  primary: "2D5BFF",    // 蓝色主题
  dark: "1A1A2E",
  gray: "555555",
  lightGray: "888888",
  border: "E0E0E0",
  bg: "F5F7FA",
};

const fontMain = "微软雅黑";
const fontEN = "Arial";

// 通用段落样式
const pBase = (text, opts = {}) => new Paragraph({
  spacing: { before: 0, after: opts.after || 0, line: opts.line || 360 },
  alignment: opts.align || AlignmentType.LEFT,
  indent: opts.indent || undefined,
  children: [
    new TextRun({
      text,
      font: opts.font || fontMain,
      size: opts.size || 21,
      bold: opts.bold || false,
      color: opts.color || COLORS.dark,
    }),
  ],
  ...(opts.extra || {}),
});

// 段落含多个 run
const pRuns = (runs, opts = {}) => new Paragraph({
  spacing: { before: 0, after: opts.after || 0, line: opts.line || 360 },
  alignment: opts.align || AlignmentType.LEFT,
  children: runs.map(r => new TextRun({
    text: r.text,
    font: r.font || fontMain,
    size: r.size || 21,
    bold: r.bold || false,
    color: r.color || COLORS.dark,
  })),
  ...(opts.extra || {}),
});

// 分隔线
const divider = () => new Paragraph({
  spacing: { before: 40, after: 40 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLORS.primary, space: 1 } },
  children: [],
});

// 项目标题（时间+名称+角色）
const projectTitle = (time, name, subtitle, role) => {
  const runs = [
    { text: time + "  ", font: fontEN, size: 22, bold: true, color: COLORS.primary },
    { text: name, size: 24, bold: true, color: COLORS.dark },
  ];
  if (subtitle) {
    runs.push({ text: "（" + subtitle + "）", size: 20, color: COLORS.lightGray });
  }
  if (role) {
    runs.push({ text: "    " + role, size: 20, bold: true, color: COLORS.gray });
  }
  return new Paragraph({
    spacing: { before: 160, after: 40, line: 360 },
    children: runs.map(r => new TextRun(r)),
  });
};

// 项目描述标签
const projTag = (text) => new Paragraph({
  spacing: { before: 40, after: 0, line: 340 },
  indent: { left: 240 },
  children: [
    new TextRun({ text: "▎ ", size: 18, color: COLORS.primary }),
    new TextRun({ text, font: fontMain, size: 18, bold: true, color: COLORS.dark }),
  ],
});

// Bullet point
const bullet = (text) => new Paragraph({
  spacing: { before: 20, after: 20, line: 340 },
  indent: { left: 480 },
  children: [
    new TextRun({ text: text, font: fontMain, size: 20, color: COLORS.gray }),
  ],
});

// ============================================================
// 构建文档
// ============================================================
const doc = new Document({
  styles: {
    default: {
      document: { run: { font: fontMain, size: 21 } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 }, // A4
        margin: { top: 1000, right: 1200, bottom: 800, left: 1200 },
      },
    },
    children: [

      // ==================== 头部 ====================
      new Table({
        width: { size: 9506, type: WidthType.DXA },
        columnWidths: [7000, 2506],
        rows: [
          new TableRow({
            children: [
              // 左侧：姓名 + 个人信息
              new TableCell({
                width: { size: 7000, type: WidthType.DXA },
                borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
                margins: { top: 0, bottom: 0, left: 0, right: 80 },
                children: [
                  new Paragraph({
                    spacing: { before: 0, after: 40 },
                    children: [
                      new TextRun({ text: "叶泳君", font: fontMain, size: 52, bold: true, color: COLORS.dark }),
                    ],
                  }),
                  new Paragraph({
                    spacing: { before: 0, after: 60 },
                    children: [
                      new TextRun({ text: "年龄：21    |    电话：17722938771    |    邮箱：1421617771@qq.com", font: fontMain, size: 18, color: COLORS.lightGray }),
                    ],
                  }),
                  new Paragraph({
                    spacing: { before: 0, after: 0 },
                    children: [
                      new TextRun({ text: "期望城市：广州 / 深圳", font: fontMain, size: 18, color: COLORS.lightGray }),
                    ],
                  }),
                ],
              }),
              // 右侧：照片
              new TableCell({
                width: { size: 2506, type: WidthType.DXA },
                borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
                margins: { top: 0, bottom: 0, left: 80, right: 0 },
                verticalAlign: "center",
                children: [
                  new Paragraph({
                    alignment: AlignmentType.RIGHT,
                    children: [new ImageRun({
                      type: "jpeg",
                      data: fs.readFileSync("static/profile_photo.jpeg"),
                      transformation: { width: 100, height: 130 },
                      altText: { title: "photo", description: "Profile photo", name: "photo" },
                    })],
                  }),
                ],
              }),
            ],
          }),
        ],
      }),

      divider(),

      // ==================== 求职意向 ====================
      new Paragraph({
        spacing: { before: 80, after: 40 },
        children: [
          new TextRun({ text: "求职意向：", font: fontMain, size: 22, bold: true, color: COLORS.dark }),
          new TextRun({ text: "AI Agent 应用开发实习生（多 Agent 协作 / RAG / Agent 架构方向）", font: fontMain, size: 22, color: COLORS.primary }),
        ],
      }),

      divider(),

      // ==================== 教育背景 ====================
      new Paragraph({
        spacing: { before: 80, after: 40 },
        children: [
          new TextRun({ text: "教育背景", font: fontMain, size: 28, bold: true, color: COLORS.dark }),
        ],
      }),

      new Paragraph({
        spacing: { before: 0, after: 20, line: 360 },
        children: [
          new TextRun({ text: "2023.09 - 2027.06  ", font: fontEN, size: 21, bold: true, color: COLORS.primary }),
          new TextRun({ text: "广州华立学院", font: fontMain, size: 22, bold: true, color: COLORS.dark }),
          new TextRun({ text: "    计算机科学与技术（本科）", font: fontMain, size: 21, color: COLORS.gray }),
        ],
      }),

      bullet("主修课程：Java 程序设计、C 语言程序设计、Python 程序设计、HTML5 / JavaScript / CSS、计算机网络、计算机组成原理、Linux 基础、AI Agent 应用开发（自修）"),
      bullet("GPA 3.6/4.5（优秀），平均分 85.34，连续 2 次获得专项奖学金（专业前 5%）；自修 AI Agent 开发与 LLM 集成、RAG 检索增强生成"),

      divider(),

      // ==================== 项目经历 ====================
      new Paragraph({
        spacing: { before: 80, after: 80 },
        children: [
          new TextRun({ text: "项目经历", font: fontMain, size: 28, bold: true, color: COLORS.dark }),
        ],
      }),

      // ========== 项目 1：电商 AI Agent 体系（新增）==========
      projectTitle("2026.05 - 2026.07", "电商 AI Agent 体系", "多 Agent 协作电商智能平台", "架构设计 & 全栈开发"),
      new Paragraph({
        spacing: { before: 0, after: 40 },
        indent: { left: 240 },
        children: [
          new TextRun({ text: "项目地址：", size: 18, color: COLORS.lightGray }),
          new TextRun({ text: "https://github.com/yeeee520/AIagent", size: 18, color: COLORS.primary }),
        ],
      }),

      projTag("核心架构"),
      bullet("【数据中台】设计以数据中台为核心枢纽的 Agent 体系架构，负责数据清洗、转换、注入全流程，将多源异构数据统一标准化后注入 RAG 知识库，作为整个 Agent 集群的数据基础设施"),
      bullet("【Agent 集群 & MCP】基于 MCP（Model Context Protocol）协议构建 Agent 集群管理框架，定义统一的 Agent 通信接口与能力边界，实现 AI 客服 Agent、运营 Agent、直播切片 Agent 等多 Agent 的发现、路由与协作调度"),
      bullet("【RAG 知识库】基于 ChromaDB（向量数据库）+ LangChain 搭建检索增强生成知识库，支持文本 Embedding（text-embedding-3-small）与语义检索，Top-K 候选召回 + BM25 混合检索策略"),

      projTag("Agent 工作流设计"),
      bullet("【AI 客服 Agent】对接 RAG 知识库实现智能问答，爬取真实客服聊天记录 -> 经数据中台机器清洗 + 人工清洗 -> 注入 RAG，AI 客服可拉取知识库中的文本、图片、视频等多模态素材，实现对传统人工客服的智能化替代"),
      bullet("【运营 Agent】自动生成电商宣传视频、宣传图、文案等营销素材，输出至 AI 素材中心进行商品 ID 关联，经数据中台清洗后补充至 RAG 知识库，实现多模态知识体系的持续更新"),
      bullet("【直播切片 Agent】自动识别直播内容，将产品特点、促销信息等关键片段智能切片为标签化短视频素材，同步至 AI 素材中心完成商品关联与知识库注入"),
      bullet("【模型微调规划】预留模型微调管线，数据中台可调出大量优质清洗数据用于模型 Fine-tuning，使 AI 客服回复更拟人化"),

      projTag("桌面应用 & 工程化"),
      bullet("使用 FastAPI 构建后端 API 服务（RESTful + SSE 流式响应），集成 ChromaDB 持久化与 SQLite 关系型数据存储"),
      bullet("基于 PyWebView 将 Web 应用封装为原生桌面窗口（1200x800），关闭窗口自动停止后台服务，零残留进程"),
      bullet("使用 PyInstaller 打包为单文件 EXE（22MB），嵌入像素风萌版鲸鱼图标，首次运行自动迁移 ChromaDB 至 %APPDATA% 实现数据持久化"),
      bullet("前端采用极简苹果风格 UI（#f5f5f7 背景 + 圆角卡片），HTML/CSS/JS 纯原生实现，零框架依赖"),

      projTag("技术栈"),
      bullet("Python / FastAPI / Uvicorn / ChromaDB / LangChain / OpenAI API / PyWebView / PyInstaller / SQLite / HTML / CSS / JavaScript"),

      new Paragraph({ spacing: { before: 120, after: 0 }, children: [] }),

      // ========== 项目 2：AIMux ==========
      projectTitle("2026.04 - 2026.07", "AIMux", "AI 编码代理桌面工具", "全栈开发"),
      new Paragraph({
        spacing: { before: 0, after: 40 },
        indent: { left: 240 },
        children: [
          new TextRun({ text: "项目地址：", size: 18, color: COLORS.lightGray }),
          new TextRun({ text: "github.com/yeeee520/AIMux", size: 18, color: COLORS.primary }),
        ],
      }),

      projTag("项目概述"),
      bullet("【AI 辅助开发】全程使用 Codex/Claude 等 AI Agent 工具完成编码与调试，通过自身代理路由验证多模型协作流程。基于 Python + CustomTkinter 构建 Windows 桌面 GUI，集成 4 个功能标签页（控制台 / API Keys / 路由规则 / 请求日志），实现可视化配置持久化"),
      bullet("基于 Flask 实现反向代理服务器，兼容 OpenAI/Codex Response 双协议格式自动转换，支持 SSE 流式转发并保留推理内容渲染。设计多 Provider 动态路由引擎，支持任意 API Provider 注册，基于通配符模型名自动匹配路由规则"),
      bullet("集成系统托盘常驻后台（pystray 托盘图标右键菜单）；使用 PyInstaller 打包为独立 EXE 分发，首次运行自动在 %APPDATA% 生成配置与图标"),
      bullet("实现一键配置 Codex/Claude Code 工具，自动修改 ~/.codex/config.toml 及 ~/.claude/settings.json，无缝切换 API 端点至本地代理，请求端到端耗时 < 50ms"),

      projTag("技术栈"),
      bullet("Python / CustomTkinter / Flask / OpenAI API / SSE / PyInstaller / pystray"),

      new Paragraph({ spacing: { before: 120, after: 0 }, children: [] }),

          ],
  }],
});

// ============================================================
// 生成文件
// ============================================================
const outputPath = "C:/Users/yeeee/Desktop/求职简历/yeeee/叶泳君_简历_AIagent+AIMux.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log("简历已生成: " + outputPath);
}).catch(err => {
  console.error("生成失败:", err);
});
