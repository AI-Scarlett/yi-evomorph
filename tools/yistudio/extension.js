const vscode = require('vscode');
const { exec, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const HEXAGRAM_FULL = [
    ['CREA','䷀','乾','创生','创建新进程/线程',63],
    ['RECV','䷁','坤','承纳','接收消息/映射',0],
    ['ALLOC','䷂','屯','初生','在堆/栈开辟内存',17],
    ['SPRT','䷃','蒙','苗蒙','加载动态库',34],
    ['WAIT','䷄','需','需待','等待条件满足',23],
    ['LOCK','䷅','讼','争讼','争抢互斥锁',58],
    ['BRANCH','䷆','师','师众','条件分支跳转',2],
    ['MERGE','䷇','比','比辅','合并数据流',16],
    ['PREFETCH','䷈','小畜','小畜','预取缓存行',55],
    ['STEP','䷉','履','履礼','单步执行/迭代',59],
    ['FLUSH','䷊','泰','泰通','刷新写缓冲',7],
    ['HALT','䷋','否','否闭','暂停/阻塞',56],
    ['FELLOWSHIP','䷌','同人','同人','同步通信集结',61],
    ['ABUNDANCE','䷍','大有','大有','写回/填充数据',47],
    ['YIELD','䷎','谦','谦退','释放资源/让出',4],
    ['SPECULATE','䷏','豫','豫乐','预测分支/投机执行',8],
    ['FOLLOWING','䷐','随','随从','数据流跟踪/复制',25],
    ['MUT','䷑','蛊','蛊坏','强制变异',38],
    ['APPROACH','䷒','临','临近','接近临界区',3],
    ['CONTEMPLATE','䷓','观','观瞻','观测/性能监视',48],
    ['BITE','䷔','噬嗑','噬嗑','断言/校验',41],
    ['ADORN','䷕','贲','贲饰','格式化/编码转换',37],
    ['STRIP','䷖','剥','剥落','剥离/解构数据',32],
    ['RETURN','䷗','复','复归','函数返回/循环回跳',1],
    ['INTRINSIC','䷘','无妄','无妄','内建原子操作',57],
    ['BARRIER','䷙','大畜','大畜','内存屏障',39],
    ['NOURISH','䷚','颐','颐养','垃圾回收/内存养护',33],
    ['OVERLOAD','䷛','大过','大过','异常/溢出处理',30],
    ['TRAP','䷜','坎','坎险','异常捕获/陷阱',18],
    ['ILLUMINATE','䷝','离','离明','日志/调试输出',45],
    ['SENSE','䷞','咸','咸感','事件监听/感应',28],
    ['PERSIST','䷟','恒','恒久','持久化存储',14],
    ['RETREAT','䷠','遁','遁退','安全退出/回滚',60],
    ['THRUST','䷡','大壮','大壮','强制执行/突破',15],
    ['ADVANCE','䷢','晋','晋进','队列推进/流水线',40],
    ['OBSCURE','䷣','明夷','明夷','加密/混淆',5],
    ['BIND','䷤','家人','家人','绑定/闭包',53],
    ['CONVERT','䷥','睽','睽乖','类型转换',43],
    ['LAME','䷦','蹇','蹇难','重试/降级',20],
    ['UNLOCK','䷧','解','解缓','解锁/释放',10],
    ['REDUCE','䷨','损','损减','缩减/压缩',35],
    ['INCREASE','䷩','益','益增','扩展/增强',49],
    ['BREAK','䷪','夬','夬决','中断/断开',31],
    ['MATE','䷫','姤','姤遇','基因交叉重组',62],
    ['GATHER','䷬','萃','萃聚','收集/归约',24],
    ['PUSH_UP','䷭','升','升推','入栈/上推',6],
    ['TRAPPED','䷮','困','困穷','死锁检测',26],
    ['WELL','䷯','井','井泉','阻塞读/管道',22],
    ['REPLACE','䷰','革','革变','替换/热更新',29],
    ['CAST','䷱','鼎','鼎定','类型铸造/固化',46],
    ['SHOCK','䷲','震','震动','信号/中断触发',9],
    ['STILL','䷳','艮','艮止','暂停/冻结',36],
    ['GRADUAL','䷴','渐','渐进','逐步执行',52],
    ['MISMATCH','䷵','归妹','归妹','类型不匹配',11],
    ['ABOUND','䷶','丰','丰盛','批量操作',13],
    ['TRAVEL','䷷','旅','旅寄','上下文切换',44],
    ['PENETRATE','䷸','巽','巽入','渗透/穿透访问',54],
    ['JOY','䷹','兑','兑悦','回调/完成通知',27],
    ['DISPERSE','䷺','涣','涣散','分散写入',50],
    ['THROTTLE','䷻','节','节度','节流/流控',19],
    ['TRUST','䷼','中孚','中孚','签名/验证',51],
    ['MICRO','䷽','小过','小过','微调/微操作',12],
    ['SYNC','䷾','既济','既济','屏障同步',21],
    ['FUTU','䷿','未济','未济','异步占位符/未来值',42],
];

const hexagramMap = {};
HEXAGRAM_FULL.forEach(([mnemonic, symbol, gua, cn, desc, opcode]) => {
    hexagramMap[mnemonic] = { symbol, gua, cn, desc, opcode };
});

function getEvoPath() {
    const config = vscode.workspace.getConfiguration('yistudio');
    let evoPath = config.get('evoPath', 'python3 bin/evo-ai');
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath;
    if (workspaceFolder && evoPath.includes('bin/evo-ai') && !path.isAbsolute(evoPath)) {
        evoPath = `python3 ${path.join(workspaceFolder, 'bin', 'evo-ai')}`;
    }
    return evoPath;
}

function activate(context) {
    console.log('YiStudio 易衍·Evomorph 扩展已激活');

    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            { scheme: 'file', language: 'evomorph' },
            {
                provideCompletionItems(document, position) {
                    const linePrefix = document.lineAt(position).text.substring(0, position.character);
                    const items = [];

                    HEXAGRAM_FULL.forEach(([mnemonic, symbol, gua, cn, desc, opcode]) => {
                        const item = new vscode.CompletionItem(`${symbol} ${mnemonic}`, vscode.CompletionItemKind.Keyword);
                        item.detail = `${symbol} ${mnemonic} (0x${opcode.toString(16).toUpperCase().padStart(2,'0')})`;
                        item.documentation = new vscode.MarkdownString(
                            `**${gua}·${cn}** — ${desc}\n\n操作码: ${opcode} (${opcode.toString(2).padStart(6,'0')})`
                        );
                        item.insertText = mnemonic;
                        item.sortText = String(opcode).padStart(3, '0');
                        items.push(item);
                    });

                    ['.ASYNC',' .ATOMIC','.PRIV','.WEAK','.STRONG','.VOLATILE'].forEach(mod => {
                        const item = new vscode.CompletionItem(mod, vscode.CompletionItemKind.Modifier);
                        const descs = {'.ASYNC':'异步执行','.ATOMIC':'原子操作','.PRIV':'私有访问','.WEAK':'弱引用','.STRONG':'强引用','.VOLATILE':'易失性'};
                        item.detail = descs[mod] || mod;
                        items.push(item);
                    });

                    for (let i = 0; i <= 15; i++) {
                        items.push(new vscode.CompletionItem(`R${i}`, vscode.CompletionItemKind.Variable));
                    }
                    ['R_FP','R_SP','R_LR','R_A0'].forEach(r => {
                        const item = new vscode.CompletionItem(r, vscode.CompletionItemKind.Variable);
                        item.detail = {R_FP:'帧指针',R_SP:'栈指针',R_LR:'链接寄存器',R_A0:'累加器'}[r];
                        items.push(item);
                    });

                    ['mut_rate','cross_pool','fitness','env_target','max_generations','卦序'].forEach(kw => {
                        items.push(new vscode.CompletionItem(kw, vscode.CompletionItemKind.Property));
                    });

                    ['min_latency','max_throughput','min_energy','min_size'].forEach(kw => {
                        const item = new vscode.CompletionItem(kw, vscode.CompletionItemKind.Constant);
                        item.detail = {min_latency:'最小延迟',max_throughput:'最大吞吐量',min_energy:'最小能耗',min_size:'最小代码体积'}[kw];
                        items.push(item);
                    });

                    return items;
                }
            },
            ' ', '\t', '.', '@'
        )
    );

    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { scheme: 'file', language: 'evomorph' },
            {
                provideHover(document, position) {
                    const range = document.getWordRangeAtPosition(position);
                    if (!range) return null;
                    const word = document.getText(range);

                    if (hexagramMap[word]) {
                        const h = hexagramMap[word];
                        return new vscode.Hover(new vscode.MarkdownString(
                            `**${h.symbol} ${word}** — ${h.gua}·${h.cn}\n\n${h.desc}\n\n| 属性 | 值 |\n|------|----|\n| 操作码 | ${h.opcode} |\n| 二进制 | ${h.opcode.toString(2).padStart(6,'0')} |`
                        ));
                    }

                    const fitnessDescs = {
                        'min_latency': '最小延迟 — 优化目标：延迟越低越好',
                        'max_throughput': '最大吞吐量 — 优化目标：吞吐量越高越好',
                        'min_energy': '最小能耗 — 优化目标：能耗越低越好',
                        'min_size': '最小代码体积 — 优化目标：代码越短越好',
                    };
                    if (fitnessDescs[word]) {
                        return new vscode.Hover(new vscode.MarkdownString(`**${word}** — ${fitnessDescs[word]}`));
                    }

                    const propDescs = {
                        'mut_rate': '**mut_rate** — 变异率 (0.0~1.0)，控制进化编译中的爻位翻转概率',
                        'cross_pool': '**cross_pool** — 交叉池名称，同池基因座可进行基因交叉',
                        'fitness': '**fitness** — 适应度表达式，定义进化优化的目标函数',
                        'env_target': '**env_target** — 目标平台列表，代码将针对这些平台优化',
                        'max_generations': '**max_generations** — 最大进化代数',
                    };
                    if (propDescs[word]) {
                        return new vscode.Hover(new vscode.MarkdownString(propDescs[word]));
                    }

                    return null;
                }
            }
        )
    );

    context.subscriptions.push(
        vscode.languages.registerDocumentSymbolProvider(
            { scheme: 'file', language: 'evomorph' },
            {
                provideDocumentSymbols(document) {
                    const symbols = [];
                    for (let i = 0; i < document.lineCount; i++) {
                        const line = document.lineAt(i).text.trim();
                        if (line.startsWith('@locus ')) {
                            const name = line.replace('@locus', '').trim().rstrip?.('{').trim() || line;
                            symbols.push(new vscode.DocumentSymbol(
                                name, '基因座', vscode.SymbolKind.Class,
                                document.lineAt(i).range, document.lineAt(i).range
                            ));
                        } else if (line.startsWith('@meta_locus ')) {
                            const name = line.replace('@meta_locus', '').trim().rstrip?.('{').trim() || line;
                            symbols.push(new vscode.DocumentSymbol(
                                `[meta] ${name}`, '元基因座', vscode.SymbolKind.Class,
                                document.lineAt(i).range, document.lineAt(i).range
                            ));
                        } else if (line.startsWith('@xiangci')) {
                            symbols.push(new vscode.DocumentSymbol(
                                '象辞', '象辞', vscode.SymbolKind.String,
                                document.lineAt(i).range, document.lineAt(i).range
                            ));
                        }
                    }
                    return symbols;
                }
            }
        )
    );

    const cmds = {
        'yistudio.compile': () => runEvoCommand('compile', '-f json'),
        'yistudio.compileToEVB': () => runEvoCommand('compile', '-f evb'),
        'yistudio.evolve': () => {
            const config = vscode.workspace.getConfiguration('yistudio');
            const target = config.get('defaultTarget', 'linux-6.x');
            const pop = config.get('populationSize', 64);
            const gen = config.get('maxGenerations', 100);
            runEvoCommand('evolve', `-g ${gen} --population ${pop} -p ${target}`);
        },
        'yistudio.runVM': () => runEvoCommand('run', ''),
        'yistudio.xiangci': () => {
            vscode.window.showInputBox({
                prompt: '输入象辞（自然语言意图）',
                placeHolder: '吾欲一程序...'
            }).then(text => {
                if (text) {
                    const evoPath = getEvoPath();
                    const terminal = vscode.window.createTerminal('象辞翻译');
                    terminal.show();
                    terminal.sendText(`${evoPath} generate "${text}" --compile`);
                }
            });
        },
        'yistudio.lookupHexagram': () => {
            vscode.window.showInputBox({
                prompt: '输入卦象符号、助记符或拼音',
                placeHolder: 'CREA / ䷀ / QIAN'
            }).then(query => {
                if (query) {
                    const evoPath = getEvoPath();
                    const terminal = vscode.window.createTerminal('卦象查询');
                    terminal.show();
                    terminal.sendText(`${evoPath} lookup "${query}"`);
                }
            });
        },
        'yistudio.listPlatforms': () => {
            const evoPath = getEvoPath();
            const terminal = vscode.window.createTerminal('目标平台');
            terminal.show();
            terminal.sendText(`${evoPath} platforms`);
        },
        'yistudio.aiGenerate': () => {
            vscode.window.showInputBox({
                prompt: '输入自然语言描述，AI 生成 .evo 代码',
                placeHolder: '并行求和，适配Linux和鸿蒙'
            }).then(text => {
                if (text) {
                    const evoPath = getEvoPath();
                    const terminal = vscode.window.createTerminal('易衍 AI');
                    terminal.show();
                    terminal.sendText(`${evoPath} generate "${text}" --compile`);
                }
            });
        },
        'yistudio.newFile': () => {
            vscode.workspace.openTextDocument({
                language: 'evomorph',
                content: '@evolang "3.0"\n\n@xiangci {\n\t""\n}\n\n@locus main {\n\tmut_rate   = 0.02\n\tcross_pool = "default"\n\tfitness    = min_latency + 2.0*max_throughput\n\tenv_target = ["linux-6.x"]\n\tmax_generations = 100\n\n\t卦序: {\n\t\t\n\t}\n}\n'
            }).then(doc => {
                vscode.window.showTextDocument(doc);
            });
        },
        'yistudio.showYao': () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selection = editor.selection;
            const text = editor.document.getText(selection);
            if (!text) {
                vscode.window.showInformationMessage('请先选中一条卦象指令');
                return;
            }
            const mnemonic = text.trim().split(/\s+/)[0];
            const h = hexagramMap[mnemonic];
            if (h) {
                const binary = h.opcode.toString(2).padStart(6, '0');
                const yaoVisual = binary.split('').map(b => b === '1' ? '⚊' : '⚋').join('');
                vscode.window.showInformationMessage(
                    `${h.symbol} ${mnemonic} — ${h.gua}·${h.cn}\n爻位: ${yaoVisual}\n二进制: ${binary}\n操作码: ${h.opcode}`,
                    { modal: true }
                );
            }
        },
    };

    for (const [cmd, handler] of Object.entries(cmds)) {
        context.subscriptions.push(vscode.commands.registerCommand(cmd, handler));
    }

    function runEvoCommand(subcmd, extraArgs) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        const filePath = editor.document.fileName;
        const evoPath = getEvoPath();
        const terminalName = {compile:'易衍编译', evolve:'易衍进化', run:'IChingVM'}[subcmd] || '易衍';
        const terminal = vscode.window.createTerminal(terminalName);
        terminal.show();
        terminal.sendText(`${evoPath} ${subcmd} "${filePath}" ${extraArgs}`);
    }

    vscode.workspace.onDidSaveTextDocument(document => {
        if (document.languageId === 'evomorph') {
            const config = vscode.workspace.getConfiguration('yistudio');
            if (config.get('enableDiagnostics', true)) {
                try {
                    const evoPath = getEvoPath();
                    const filePath = document.fileName;
                    const result = execSync(`${evoPath} compile "${filePath}" -f json`, {
                        timeout: 10000,
                        encoding: 'utf-8',
                        stdio: ['pipe','pipe','pipe']
                    });
                } catch (e) {
                    // Compilation error - could show in problems panel
                }
            }
        }
    });

    vscode.languages.registerCodeLensProvider(
        { scheme: 'file', language: 'evomorph' },
        {
            provideCodeLenses(document) {
                const lenses = [];
                for (let i = 0; i < document.lineCount; i++) {
                    const line = document.lineAt(i).text.trim();
                    if (line.startsWith('@locus ')) {
                        const range = document.lineAt(i).range;
                        lenses.push(new vscode.CodeLens(range, {
                            title: '▶ 运行',
                            command: 'yistudio.runVM'
                        }));
                        lenses.push(new vscode.CodeLens(range, {
                            title: '🧬 进化',
                            command: 'yistudio.evolve'
                        }));
                    }
                }
                return lenses;
            }
        }
    );
}

function deactivate() {}

module.exports = { activate, deactivate };
