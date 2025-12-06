import sys
import re

class PyStack:
    def __init__(self):
        self.stack = []
        self.memory = {}
        self.functions = {}
        self.tokens = []
        self.jumps = {}
        self.precedence = {
            '+': 1, '-': 1, '*': 2, '/': 2, '%': 2,
            '>': 0, '<': 0, '==': 0, '!=': 0, 
            '>=': 0, '<=': 0
        }

    def tokenize(self, source_code):
        raw_tokens = []
        for line in source_code.split('\n'):
            line = line.split('#')[0].strip()
            if not line: continue
            
            # --- Regex 终极版: 强制切分所有符号 ---
            # 1. 字符串 | 2. 双符号 | 3. 单符号 | 4. 数字/变量
            pattern = r'"[^"]*"|==|!=|<=|>=|[+\-*/%<>=()]|[^\s+\-*/%<>=()]+'
            matches = re.findall(pattern, line)
            
            # 赋值检测
            if '=' in matches and matches[0] != 'if' and '==' not in matches and '<=' not in matches and '>=' not in matches:
                try:
                    eq_index = matches.index('=')
                    var_name = matches[0]
                    expression = matches[eq_index+1:]
                    rpn = self.shunting_yard(expression)
                    raw_tokens.extend(rpn)
                    raw_tokens.append('store')
                    raw_tokens.append(var_name)
                except ValueError: pass
            else:
                raw_tokens.extend(matches)
        return raw_tokens

    def shunting_yard(self, expr_tokens):
        output = []
        ops = []
        for token in expr_tokens:
            is_num = token.replace('.', '', 1).isdigit() or (token.startswith('-') and len(token)>1)
            if is_num: output.append(token)
            elif token.startswith('"'): output.append(token)
            elif token.isidentifier() and token not in ['true', 'false']: 
                output.append('load'); output.append(token)
            elif token == '(': ops.append(token)
            elif token == ')':
                while ops and ops[-1] != '(': output.append(ops.pop())
                if ops: ops.pop()
            elif token in self.precedence:
                while (ops and ops[-1] in self.precedence and self.precedence[ops[-1]] >= self.precedence[token]):
                    output.append(ops.pop())
                ops.append(token)
            else: output.append(token)
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
                if i+1 < len(self.tokens): self.functions[self.tokens[i+1]] = {'start': i + 2}
            elif token == 'end':
                if not control_stack: raise SyntaxError("Unexpected End")
                match_type, match_idx = control_stack.pop()
                if match_type in ['if', 'else', 'def']: self.jumps[match_idx] = i + 1
                elif match_type == 'do':
                    while_type, while_idx = control_stack.pop()
                    self.jumps[i] = while_idx 
                    self.jumps[match_idx] = i + 1
                if match_type == 'def':
                    self.functions[self.tokens[match_idx+1]]['end'] = i

    def run(self, source_code, trace=False):
        print("--- Running ---")
        try:
            self.stack = []
            self.compile(source_code)
            # print(f"DEBUG TOKENS: {self.tokens}") 
            self.execute(0, len(self.tokens), trace=trace)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def check_stack(self, count=1, msg="Stack Underflow"):
        if len(self.stack) < count:
            raise RuntimeError(f"{msg}. Stack: {self.stack}")

    def execute(self, ip, limit, trace=False):
        while ip < limit:
            token = self.tokens[ip]
            
            # --- TRACE LOG: 打印每一步状态 ---
            if trace:
                print(f"IP:{ip:03} | Op:{token:<10} | Stack:{self.stack}")

            # 1. Primitives
            is_num = token.replace('.', '', 1).isdigit() or (token.startswith('-') and len(token)>1)
            if is_num: self.stack.append(float(token) if '.' in token else int(token))
            elif token.startswith('"'): self.stack.append(token.strip('"'))
            elif token == 'true': self.stack.append(True)
            elif token == 'false': self.stack.append(False)

            # 2. Variables
            elif token == 'load':
                ip += 1
                self.stack.append(self.memory[self.tokens[ip]])
            elif token == 'store':
                ip += 1
                self.check_stack(1)
                self.memory[self.tokens[ip]] = self.stack.pop()

            # 3. Stack Ops
            elif token == 'print': 
                self.check_stack(1)
                print(f">> {self.stack.pop()}")
            elif token == 'dup': 
                self.check_stack(1)
                self.stack.append(self.stack[-1])
            elif token == 'drop': 
                self.check_stack(1); self.stack.pop()
            elif token == 'swap':
                self.check_stack(2)
                self.stack[-1], self.stack[-2] = self.stack[-2], self.stack[-1]

            # 4. Math
            elif token in self.precedence:
                self.check_stack(2)
                b = self.stack.pop()
                a = self.stack.pop()
                if token == '+': self.stack.append(a + b)
                elif token == '-': self.stack.append(a - b)
                elif token == '*': self.stack.append(a * b)
                elif token == '/': self.stack.append(a / b)
                elif token == '>': self.stack.append(a > b)
                elif token == '<': self.stack.append(a < b)
                elif token == '==': self.stack.append(a == b)
                elif token == '>=': self.stack.append(a >= b)
                elif token == '<=': self.stack.append(a <= b)

            # 5. Flow
            elif token == 'if' or token == 'do':
                self.check_stack(1)
                cond = self.stack.pop()
                if not cond: ip = self.jumps[ip] - 1
            
            elif token in ['else', 'def']:
                ip = self.jumps[ip] - 1
            
            elif token == 'end':
                if ip in self.jumps: ip = self.jumps[ip] - 1

            elif token == 'call':
                ip += 1
                func_name = self.tokens[ip]
                meta = self.functions[func_name]
                # 递归调用
                self.execute(meta['start'], meta['end'], trace=trace)

            ip += 1

# --- 测试用例 ---
vm = PyStack()
code = """
"================ STAGE 1: 逻辑与循环嵌套 ================" print

# 目标：打印 1 到 3 的乘法表
# Python 逻辑:
# for i in range(1, 4):
#     for j in range(1, 4):
#         print(i * j)

i = 1
while load i 4 < do
    j = 1
    while load j 4 < do
        # 计算 i * j
        val = i * j
        
        # 打印当前结果
        load val print
        
        # j++
        j = j + 1
    end
    # i++
    i = i + 1
end

"================ STAGE 2: 斐波那契数列 (递归) ================" print
# 目标：计算 Fib(10)
# Fib(n) = Fib(n-1) + Fib(n-2)
# Fib(0)=0, Fib(1)=1

def fib
    # Stack: [n]
    dup 2 < if
        # 如果 n < 2, 直接返回 n
        # Stack: [n] -> 不需要操作，由调用者处理
    else
        # Stack: [n]
        dup 1 -      # [n, n-1]
        call fib     # [n, fib(n-1)]
        swap         # [fib(n-1), n]
        2 -          # [fib(n-1), n-2]
        call fib     # [fib(n-1), fib(n-2)]
        +            # [fib(n-1) + fib(n-2)]
    end
end

"Calculating Fib(10)..." print
10 call fib print  # 应该输出 55

"================ STAGE 3: 栈操作杂技 (Stack Acrobatics) ================" print
# 测试 swap, dup, drop 的组合使用
# 目标：交换栈顶两个数并做减法，然后再乘以 10
# 算式：((20 - 50) * 10)

50 20 
swap       # [20, 50]
-          # 20 - 50 = -30
10 * # -300
"Result should be -300:" print
print      # 输出 -300

"================ STAGE 4: 复杂条件分支 ================" print
# 测试 if-else 的深度嵌套

val = 75

load val 100 > if
    "Error: Too huge" print
else
    load val 50 > if
        load val 80 < if
            "Success: 50 < val < 80" print
        else
            "Fail: val >= 80" print
        end
    else
        "Fail: val <= 50" print
    end
end

"--- All Tests Completed ---" print
"""

vm.run(code)