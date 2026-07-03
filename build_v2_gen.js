const fs = require('fs');
const path = require('path');
const src = fs.readFileSync('scripts/build_resume.js', 'utf8');
const marker = '// ========== 项目 3：超市后台管理系统 ==========';
const start = src.indexOf(marker);
const after = src.substring(start);
const endMarker = '    ],\r\n  }],\r\n});';
const endPos = after.indexOf(endMarker);

// If CRLF not found, try LF
let endPos2 = endPos;
if (endPos2 === -1) {
    endPos2 = after.indexOf('    ],\n  }],\n});');
}

if (endPos2 === -1) {
    console.error('Could not find end marker in:\n' + after.substring(after.length - 400));
    process.exit(1);
}

const end = start + endPos2 + '    ],'.length;
const result = src.substring(0, start) + src.substring(end);
const result2 = result.replace('叶泳君_简历_优化版.docx', '叶泳君_简历_AIagent+AIMux.docx');
fs.writeFileSync('build_v2.js', result2, 'utf8');
console.log('V2 script written');
console.log('AIMux:', result2.includes('AIMux'));
console.log('超市:', result2.includes('超市后台管理系统'));
console.log('Packer:', result2.includes('Packer'));
