const vscode = require('vscode');
const path = require('path');
const { exec, execSync } = require('child_process');
const { LanguageClient, TransportKind } = require('vscode-languageclient');

let client;

function getEvoPath() {
    const config = vscode.workspace.getConfiguration('yistudio');
    let evoPath = config.get('evoPath', 'python3 bin/evo-ai');
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath;
    if (workspaceFolder && evoPath.includes('bin/evo-ai') && !path.isAbsolute(evoPath)) {
        evoPath = `python3 ${path.join(workspaceFolder, 'bin', 'evo-ai')}`;
    }
    return evoPath;
}

function getPythonInterpreter() {
    const pythonExe = process.platform === 'win32' ? 'python' : 'python3';
    const config = vscode.workspace.getConfiguration('yistudio');
    const evoPath = config.get('evoPath', '');
    if (evoPath.startsWith('python3') || evoPath.startsWith('python')) {
        return evoPath.split(' ')[0];
    }
    return pythonExe;
}

function activate(context) {
    console.log('YiStudio 易衍·Evomorph 扩展已激活');

    const pythonExe = getPythonInterpreter();
    const serverModule = path.join(
        __dirname,
        '..',
        '..',
        'evomorph',
        'lsp',
        'language_server.py'
    );

    const serverOptions = {
        run: {
            command: pythonExe,
            args: [serverModule],
            transport: TransportKind.stdio
        },
        debug: {
            command: pythonExe,
            args: [serverModule],
            transport: TransportKind.stdio
        }
    };

    const clientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'evomorph' }
        ],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/.evo')
        },
        initializationOptions: {
            extensionVersion: '3.0.0'
        }
    };

    client = new LanguageClient(
        'evomorphLSP',
        '易衍·Evomorph 语言服务器',
        serverOptions,
        clientOptions
    );

    client.start();
    console.log('LSP 客户端已启动，连接到语言服务器');

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
            const h = getHexagramInfo(mnemonic);
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

    function getHexagramInfo(mnemonic) {
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
        const map = {};
        HEXAGRAM_FULL.forEach(([mnemonic, symbol, gua, cn, desc, opcode]) => {
            map[mnemonic] = { symbol, gua, cn, desc, opcode };
        });
        return map[mnemonic];
    }
}

function deactivate() {
    if (client) {
        return client.stop();
    }
    return Promise.resolve();
}

module.exports = { activate, deactivate };
