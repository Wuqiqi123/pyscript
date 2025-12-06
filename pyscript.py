import sys
import re

class PyStack:
    def __init__(self):
        self.stack = []
        self.memory = {}
        self.functions = {}
        self.tokens = []
        self.jumps = {}
        # 定义所有运算符及其优先级
        self.precedence = {
            '+': 1, '-': 1, '*': 2, '/': 2, 
            '>': 0, '<': 0, '==': 0, '!=': 0, 
            '>=': 0, '<=': 0
        }

    def tokenize(self, source_code):
        raw_tokens = []
        for line in source_code.split('\n'):
            line = line.split('#')[0].strip()
            if not line: continue
            
            # --- 修复核心：优先匹配双字符运算符 (<=, >=, ==, !=) ---
            # 正则逻辑：字符串 | 双符号 | 单符号 | 单词
            pattern = r'"[^"]*"|==|!=|<=|>=|[()=]|[^\s()=]+'
            matches = re.findall(pattern, line)
            
            # 检测赋值语句 "i = i + 1"
            if '=' in matches and matches[0] != 'if' and '==' not in matches and '<=' not in matches and '>=' not in matches:
                try:
                    eq_index = matches.index('=')
                    var_name = matches[0]
                    expression = matches[eq_index+1:]
                    rpn = self.shunting_yard(expression)
                    raw_tokens.extend(rpn)
                    raw_tokens.append('store')
                    raw_tokens.append(var_name)
                except ValueError:
                    print(f"Syntax Error in line: {line}")
            else:
                raw_tokens.extend(matches)
        return raw_tokens

    def shunting_yard(self, expr_tokens):
        output = []
        ops = []
        for token in expr_tokens:
            # 识别数字 (包括负数)
            is_num = token.replace('.', '', 1).isdigit() or (token.startswith('-') and len(token)>1)
            
            if is_num: output.append(token)
            elif token.startswith('"'): output.append(token)
            elif token.isidentifier() and token not in ['true', 'false']: 
                output.append('load')
                output.append(token)
            elif token == '(': ops.append(token)
            elif token == ')':
                while ops and ops[-1] != '(': output.append(ops.pop())
                if ops: ops.pop()
            elif token in self.precedence:
                while (ops and ops[-1] in self.precedence and 
                       self.precedence[ops[-1]] >= self.precedence[token]):
                    output.append(ops.pop())
                ops.append(token)
            else:
                output.append(token)
        while ops: output.append(ops.pop())
        return output

    def compile(self, source_code):
        self.tokens = self.tokenize(source_code)
        self.jumps = {}
        self.functions = {}
        control_stack = []
        
        for i, token in enumerate(self.tokens):
            if token == 'if': control_stack.append(('if', i))
            elif token == 'else':
                if not control_stack: raise SyntaxError("Else without If")
                match_type, match_idx = control_stack.pop()
                self.jumps[match_idx] = i + 1
                control_stack.append(('else', i))
            elif token == 'while': control_stack.append(('while', i))
            elif token == 'do': control_stack.append(('do', i))
            elif token == 'def': 
                control_stack.append(('def', i))
                if i + 1 < len(self.tokens):
                    self.functions[self.tokens[i+1]] = {'start': i + 2}
            elif token == 'end':
                if not control_stack: raise SyntaxError("Unexpected End")
                match_type, match_idx = control_stack.pop()
                
                if match_type in ['if', 'else']: 
                    self.jumps[match_idx] = i + 1
                elif match_type == 'do':
                    while_type, while_idx = control_stack.pop()
                    self.jumps[i] = while_idx 
                    self.jumps[match_idx] = i + 1
                elif match_type == 'def':
                    self.jumps[match_idx] = i + 1
                    self.functions[self.tokens[match_idx+1]]['end'] = i

    def run(self, source_code):
        print("--- Running ---")
        try:
            self.stack = []
            self.compile(source_code)
            self.execute(0, len(self.tokens))
        except Exception as e:
            # 打印详细错误信息
            import traceback
            traceback.print_exc()

    def check_stack(self, count=1, msg="Stack Underflow"):
        if len(self.stack) < count:
            raise RuntimeError(f"{msg}. Stack: {self.stack}")

    def execute(self, ip, limit):
        # 设置最大循环次数防止死循环，或者依赖 Python 递归深度限制
        while ip < limit:
            token = self.tokens[ip]
            
            # 1. 数字 & 字符串
            if token.replace('.', '', 1).isdigit() or (token.startswith('-') and len(token)>1):
                self.stack.append(float(token) if '.' in token else int(token))
            elif token.startswith('"'): self.stack.append(token.strip('"'))
            elif token == 'true': self.stack.append(True)
            elif token == 'false': self.stack.append(False)

            # 2. 变量
            elif token == 'load':
                ip += 1
                self.stack.append(self.memory[self.tokens[ip]])
            elif token == 'store':
                ip += 1
                self.check_stack(1, f"Cannot store to {self.tokens[ip]}")
                self.memory[self.tokens[ip]] = self.stack.pop()

            # 3. 栈操作
            elif token == 'print': 
                self.check_stack(1, "Empty stack at 'print'")
                print(f">> {self.stack.pop()}")
            elif token == 'dup': 
                self.check_stack(1, "Empty stack at 'dup'")
                self.stack.append(self.stack[-1])
            elif token == 'drop': 
                self.check_stack(1, "Empty stack at 'drop'")
                self.stack.pop()

            # 4. 数学运算
            elif token in self.precedence:
                self.check_stack(2, f"Not enough operands for '{token}'")
                b = self.stack.pop()
                a = self.stack.pop()
                if token == '+': self.stack.append(a + b)
                elif token == '-': self.stack.append(a - b)
                elif token == '*': self.stack.append(a * b)
                elif token == '/': self.stack.append(a / b)
                elif token == '>': self.stack.append(a > b)
                elif token == '<': self.stack.append(a < b)
                elif token == '==': self.stack.append(a == b)
                elif token == '!=': self.stack.append(a != b)
                elif token == '>=': self.stack.append(a >= b)
                elif token == '<=': self.stack.append(a <= b)

            # 5. 控制流
            elif token == 'if' or token == 'do':
                self.check_stack(1, f"No condition for '{token}'")
                cond = self.stack.pop()
                if not cond:
                    ip = self.jumps[ip] - 1
            
            elif token in ['else', 'def']:
                ip = self.jumps[ip] - 1
            
            elif token == 'end':
                if ip in self.jumps: ip = self.jumps[ip] - 1

            elif token == 'call':
                ip += 1
                func_name = self.tokens[ip]
                meta = self.functions[func_name]
                self.execute(meta['start'], meta['end'])

            ip += 1

# --- 测试用例 ---
vm = PyStack()
code = """
"--- Test 1: Math ---" print   # <--- 注意：字符串在前，print 在后
x = 10
y = 20
z = ( x + y ) * 2
load z print

"--- Test 2: Factorial ---" print
def fact
    dup 1 <= if    # Stack: [n, n, 1] -> [n, Bool]
        drop 1     # If True: Drop n, return 1
    elseFactorial
        dup 1 -    # If False: [n, n-1]
        call fact  # [n, result]
        * # [n * result]
    end
end

5 call fact print
"""
vm.run(code)