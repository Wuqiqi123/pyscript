class PyStack:
    def __init__(self):
        self.stack = []
        self.memory = {}
        self.tokens = []
        self.jumps = {} 
        # 定义运算符优先级
        self.precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '>': 0, '<': 0, '==': 0}

    def shunting_yard(self, expression_tokens):
        """
        核心算法：将中缀表达式 (1 + 2) 转为 后缀表达式 (1 2 +)
        同时自动处理变量加载：遇到 'a' 自动转为 'load a'
        """
        output_queue = []
        operator_stack = []

        for token in expression_tokens:
            # 1. 如果是数字
            if token.replace('.', '', 1).isdigit():
                output_queue.append(token)
            # 2. 如果是变量名 (非数字、非符号)
            elif token.isidentifier() and token not in ['true', 'false']:
                # 关键点：在中缀表达式里看到变量 'x'，意味着要把它的值取出来
                # 所以我们生成两个指令：'load' 和 'x'
                # 但是为了保持 RPN 队列纯净，我们稍后在 execute 时处理，或者在这里直接展开
                # 这里我们选择直接展开指令
                output_queue.append("load") 
                output_queue.append(token)
            # 3. 如果是左括号
            elif token == '(':
                operator_stack.append(token)
            # 4. 如果是右括号
            elif token == ')':
                while operator_stack and operator_stack[-1] != '(':
                    output_queue.append(operator_stack.pop())
                operator_stack.pop() # 弹出 '('
            # 5. 如果是运算符
            elif token in self.precedence:
                while (operator_stack and operator_stack[-1] in self.precedence and
                       self.precedence[operator_stack[-1]] >= self.precedence[token]):
                    output_queue.append(operator_stack.pop())
                operator_stack.append(token)
            # 6. 其他 (字符串等)
            else:
                output_queue.append(token)

        while operator_stack:
            output_queue.append(operator_stack.pop())
        
        return output_queue

    def parse(self, code):
        self.tokens = []
        lines = code.split('\n')
        
        for line in lines:
            line = line.split('#')[0].strip()
            if not line: continue

            # --- 新增逻辑：检测赋值语句 (a = ...) ---
            if '=' in line and '==' not in line: 
                # 注意：简单的根据 = 分割，不处理 if a == b
                # 这里假设赋值语句必须是： 变量 = 表达式
                parts = line.split('=', 1)
                var_name = parts[0].strip()
                expression = parts[1].strip()
                
                # 1. 处理表达式部分的空格 (把 (1+2) 变成 1 + 2)
                expr_tokens = expression.replace('(', ' ( ').replace(')', ' ) ').split()
                
                # 2. 将表达式转为 RPN 指令
                rpn_tokens = self.shunting_yard(expr_tokens)
                self.tokens.extend(rpn_tokens)
                
                # 3. 添加赋值指令
                self.tokens.append('store')
                self.tokens.append(var_name)
                
            else:
                # 兼容旧语法：直接分割
                # 也要处理括号加空格，方便混合使用
                clean_line = line.replace('(', ' ( ').replace(')', ' ) ')
                self.tokens.extend(clean_line.split())

        # --- 下面是原来的跳转表构建逻辑 (保持不变) ---
        stack_control = []
        for i, token in enumerate(self.tokens):
            if token in ['if', 'while']:
                stack_control.append((token, i))
            elif token == 'else':
                # 简化处理，实际需要回填 jumps
                pass 
            elif token == 'end':
                # 简化处理
                pass
        # (为了代码简洁，这里省略复杂的 Jump 构建，直接复用之前的运行时扫描逻辑)

    def run(self, code):
        self.parse(code)
        self.execute(0, len(self.tokens))

    def execute(self, ip, limit):
        while ip < limit:
            token = self.tokens[ip]
            
            # 1. 数字处理 (包含对负数的简单支持)
            if token.replace('.', '', 1).isdigit() or (token.startswith('-') and len(token) > 1):
                self.stack.append(float(token) if '.' in token else int(token))
            
            # 2. 变量操作
            elif token == 'load':
                ip += 1
                self.stack.append(self.memory[self.tokens[ip]])
            elif token == 'store':
                ip += 1
                self.memory[self.tokens[ip]] = self.stack.pop()
            
            # 3. 数学运算 (修复版)
            elif token in ['+', '-', '*', '/', '>', '<', '==']:
                b = self.stack.pop()
                a = self.stack.pop()
                if token == '+': self.stack.append(a + b)
                elif token == '-': self.stack.append(a - b)
                elif token == '*': self.stack.append(a * b)
                elif token == '/': self.stack.append(a / b) # 加上除法
                elif token == '>': self.stack.append(a > b)
                elif token == '<': self.stack.append(a < b) # <--- 补上了这行！
                elif token == '==': self.stack.append(a == b)
            
            elif token == 'print':
                print(f"Output: {self.stack.pop()}")
            
            # 4. 控制流
            elif token == 'while': 
                pass 
            elif token == 'do':
                # 如果栈顶是 False，跳到 end
                if not self.stack.pop(): 
                    nest = 1
                    while nest > 0:
                        ip += 1
                        # 防止越界
                        if ip >= len(self.tokens): break 
                        if self.tokens[ip] in ['while', 'if']: nest+=1
                        if self.tokens[ip] == 'end': nest-=1
            
            elif token == 'end':
                # 回跳逻辑
                back = ip
                nest = 0
                is_loop = False
                while back > 0:
                    back -= 1
                    if self.tokens[back] == 'end': nest += 1
                    if self.tokens[back] == 'while':
                        if nest == 0: 
                            ip = back - 1 # 跳到 while 前一个位置
                            is_loop = True
                            break
                        nest -= 1
            
            ip += 1


vm = PyStack()

code = """
# 1. 直接赋值
a = 10
b = 20

# 2. 复杂的数学表达式 (自动处理优先级)
# 这行代码会自动翻译成: load a, load b, +, 2, *, store c
c = ( a + b ) * 2 
load c print

# 3. 混合使用：在 While 循环里使用赋值
# 逻辑：从 0 加到 4
i = 0
sum = 0

while load i 5 < do
    # 以前是: load sum load i + store sum
    # 现在可以是:
    sum = sum + i
    i = i + 1
end

load sum print
"""

print("--- 开始运行 ---")
vm.run(code)