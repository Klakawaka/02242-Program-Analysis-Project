import jpamb
from jpamb import jvm
from dataclasses import dataclass

import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

methodid, input = jpamb.getcase()


@dataclass
class PC:
    method: jvm.AbsMethodID
    offset: int

    def __iadd__(self, delta):
        self.offset += delta
        return self

    def __add__(self, delta):
        return PC(self.method, self.offset + delta)

    def __str__(self):
        return f"{self.method}:{self.offset}"


@dataclass
class Bytecode:
    suite: jpamb.Suite
    methods: dict[jvm.AbsMethodID, list[jvm.Opcode]]

    def __getitem__(self, pc: PC) -> jvm.Opcode:
        try:
            opcodes = self.methods[pc.method]
        except KeyError:
            opcodes = list(self.suite.method_opcodes(pc.method))
            self.methods[pc.method] = opcodes

        return opcodes[pc.offset]


@dataclass
class Stack[T]:
    items: list[T]

    def __bool__(self) -> bool:
        return len(self.items) > 0

    @classmethod
    def empty(cls):
        return cls([])

    def peek(self) -> T:
        return self.items[-1]

    def pop(self) -> T:
        return self.items.pop(-1)

    def push(self, value):
        self.items.append(value)
        return self

    def __str__(self):
        if not self:
            return "ϵ"
        return "".join(f"{v}" for v in self.items)


suite = jpamb.Suite()
bc = Bytecode(suite, dict())


@dataclass
class Frame:
    locals: dict[int, jvm.Value]
    stack: Stack[jvm.Value]
    pc: PC

    def __str__(self):
        locals = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals}}}, {self.stack}, {self.pc}>"

    def from_method(method: jvm.AbsMethodID) -> "Frame":
        return Frame({}, Stack.empty(), PC(method, 0))


@dataclass
class State:
    heap: dict[int, jvm.Value]
    frames: Stack[Frame]

    def __str__(self):
        return f"{self.heap} {self.frames}"


def step(state: State) -> State | str:
    assert isinstance(state, State), f"expected frame but got {state}"
    frame = state.frames.peek()
    opr = bc[frame.pc]
    logger.debug(f"STEP {opr}\n{state}")
    match opr:
        case jvm.Push(value=v):
            frame.stack.push(v)
            frame.pc += 1
            return state
        
        case jvm.Load(type=t, index=i):
            # Handle all types: Int, Boolean, Reference, etc.
            if i in frame.locals:
                frame.stack.push(frame.locals[i])
            else:
                # Default value for uninitialized locals
                if isinstance(t, jvm.Int):
                    frame.stack.push(jvm.Value.int(0))
                elif isinstance(t, jvm.Boolean):
                    frame.stack.push(jvm.Value.boolean(False))
                elif isinstance(t, (jvm.Reference, jvm.Object)):
                    frame.stack.push(jvm.Value(t, None))
                else:
                    raise NotImplementedError(f"Load for type {t} not implemented")
            frame.pc += 1
            return state
        
        case jvm.Store(type=t, index=i):
            # Store value from stack to local variable
            value = frame.stack.pop()
            frame.locals[i] = value
            frame.pc += 1
            return state
        
        case jvm.Binary(type=jvm.Int(), operant=op):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert v1.type is jvm.Int(), f"expected int, but got {v1}"
            assert v2.type is jvm.Int(), f"expected int, but got {v2}"
            
            match op:
                case jvm.BinaryOpr.Div:
                    if v2.value == 0:
                        return "divide by zero"
                    frame.stack.push(jvm.Value.int(v1.value // v2.value))
                case jvm.BinaryOpr.Add:
                    frame.stack.push(jvm.Value.int(v1.value + v2.value))
                case jvm.BinaryOpr.Sub:
                    frame.stack.push(jvm.Value.int(v1.value - v2.value))
                case jvm.BinaryOpr.Mul:
                    frame.stack.push(jvm.Value.int(v1.value * v2.value))
                case jvm.BinaryOpr.Rem:
                    if v2.value == 0:
                        return "divide by zero"
                    frame.stack.push(jvm.Value.int(v1.value % v2.value))
                case _:
                    raise NotImplementedError(f"Binary operation {op} not implemented")
            
            frame.pc += 1
            return state
        
        case jvm.Ifz(condition=cond, target=target):
            # Conditional jump based on single value (compare with zero)
            value = frame.stack.pop()
            
            # Get the actual integer value for comparison
            if isinstance(value.type, jvm.Boolean):
                int_val = 1 if value.value else 0
            elif isinstance(value.type, jvm.Char):
                int_val = ord(value.value) if isinstance(value.value, str) else value.value
            else:
                int_val = value.value
            
            should_jump = False
            match cond:
                case "eq":
                    should_jump = (int_val == 0)
                case "ne":
                    should_jump = (int_val != 0)
                case "lt":
                    should_jump = (int_val < 0)
                case "le":
                    should_jump = (int_val <= 0)
                case "gt":
                    should_jump = (int_val > 0)
                case "ge":
                    should_jump = (int_val >= 0)
                case _:
                    raise NotImplementedError(f"Unknown ifz condition: {cond}")
            
            if should_jump:
                frame.pc = PC(frame.pc.method, target)
            else:
                frame.pc += 1
            return state
        
        case jvm.If(condition=cond, target=target):
            # Conditional jump based on two values
            value2 = frame.stack.pop()
            value1 = frame.stack.pop()
            
            # Get actual values for comparison
            def get_comparable_value(val):
                if isinstance(val.type, jvm.Boolean):
                    return 1 if val.value else 0
                elif isinstance(val.type, jvm.Char):
                    # For char comparison, use the integer value (ASCII/Unicode)
                    if isinstance(val.value, str):
                        return ord(val.value)
                    return val.value
                else:
                    return val.value
            
            v1 = get_comparable_value(value1)
            v2 = get_comparable_value(value2)
            
            should_jump = False
            match cond:
                case "eq":
                    should_jump = (v1 == v2)
                case "ne":
                    should_jump = (v1 != v2)
                case "lt":
                    should_jump = (v1 < v2)
                case "le":
                    should_jump = (v1 <= v2)
                case "gt":
                    should_jump = (v1 > v2)
                case "ge":
                    should_jump = (v1 >= v2)
                case _:
                    raise NotImplementedError(f"Unknown if condition: {cond}")
            
            if should_jump:
                frame.pc = PC(frame.pc.method, target)
            else:
                frame.pc += 1
            return state
        
        case jvm.Goto(target=target):
            # Unconditional jump
            frame.pc = PC(frame.pc.method, target)
            return state
        
        case jvm.New(classname=cn):
            # Create a new object instance
            # For AssertionError, we create a special marker
            class_name_str = str(cn)
            if "AssertionError" in class_name_str:
                # Push a reference that we can identify as AssertionError
                # We'll use a special string marker
                frame.stack.push(jvm.Value(jvm.Reference(), "AssertionError"))
            else:
                # For other objects, push a generic reference
                # In a full implementation, we'd allocate heap space
                frame.stack.push(jvm.Value(jvm.Reference(), f"Object:{class_name_str}"))
            frame.pc += 1
            return state
        
        case jvm.Dup(words=w):
            # Duplicate the top value(s) on the stack
            # For now, we only handle dup (words=1)
            if w == 1:
                if not frame.stack:
                    raise RuntimeError("Cannot dup: stack is empty")
                top_value = frame.stack.peek()
                frame.stack.push(top_value)
                frame.pc += 1
                return state
            else:
                raise NotImplementedError(f"Dup with words={w} not implemented")
        
        case jvm.Get(static=True, field=f):
            # Handle static field access (like $assertionsDisabled)
            if f.extension.name == "$assertionsDisabled":
                # Assertions are enabled by default in JPAMB (we run with -ea)
                # So $assertionsDisabled is False
                frame.stack.push(jvm.Value.boolean(False))
                frame.pc += 1
                return state
            raise NotImplementedError(f"Static field {f} not implemented")
        
        case jvm.Get(static=False, field=f):
            # Instance field access
            obj_ref = frame.stack.pop()
            if obj_ref.value is None:
                return "null pointer"
            raise NotImplementedError(f"Instance field {f} not implemented")
        
        case jvm.Throw():
            # Handle throw opcode (for assertions and exceptions)
            exception_obj = frame.stack.pop()
            if exception_obj.value is None:
                return "null pointer"
            
            # Check if it's an AssertionError
            exception_str = str(exception_obj.value)
            if exception_obj.value == "AssertionError" or "AssertionError" in exception_str:
                return "assertion error"
            
            # For other exceptions, we'll just return a generic error
            # In a full implementation, we'd check the exception type
            return "assertion error"  # Default for now
        
        case jvm.InvokeVirtual(method=m):
            # Handle virtual method invocations (including String methods)
            args = []
            param_count = len(m.methodid.params)
            for _ in range(param_count):
                args.insert(0, frame.stack.pop())
            
            # Pop object reference
            obj_ref = frame.stack.pop()
            if obj_ref.value is None:
                return "null pointer"
            
            result = handle_method_invocation(m, obj_ref, args)
            if isinstance(result, str):
                return result  # Error result
            if result is not None:
                frame.stack.push(result)
                frame.pc += 1
                return state
            raise NotImplementedError(f"Method invocation {m} not implemented")
        
        case jvm.InvokeStatic(method=m):
            # Handle static method invocations
            args = []
            param_count = len(m.methodid.params)
            for _ in range(param_count):
                args.insert(0, frame.stack.pop())
            
            # No object reference for static methods
            result = handle_method_invocation(m, None, args)
            if isinstance(result, str):
                return result  # Error result
            if result is not None:
                frame.stack.push(result)
                frame.pc += 1
                return state
            raise NotImplementedError(f"Static method invocation {m} not implemented")
        
        case jvm.InvokeSpecial(method=m):
            # Handle special method invocations (constructors, private methods)
            args = []
            param_count = len(m.methodid.params)
            for _ in range(param_count):
                args.insert(0, frame.stack.pop())
            
            # Pop object reference
            obj_ref = frame.stack.pop()
            if obj_ref.value is None:
                return "null pointer"
            
            # Check if it's a constructor
            if m.methodid.name == "<init>":
                # Constructors don't return a value, they just initialize the object
                # The object reference stays on the stack
                result = handle_method_invocation(m, obj_ref, args)
                if isinstance(result, str):
                    return result  # Error result
                # Push the object reference back (constructor doesn't return, but object stays)
                frame.stack.push(obj_ref)
                frame.pc += 1
                return state
            else:
                # Regular method call
                result = handle_method_invocation(m, obj_ref, args)
                if isinstance(result, str):
                    return result  # Error result
                if result is not None:
                    frame.stack.push(result)
                    frame.pc += 1
                    return state
            raise NotImplementedError(f"Special method invocation {m} not implemented")
        
        case jvm.Return(type=t):
            if t is None:
                # Void return
                state.frames.pop()
                if state.frames:
                    frame = state.frames.peek()
                    frame.pc += 1
                    return state
                else:
                    return "ok"
            else:
                # Return with value
                v1 = frame.stack.pop()
                state.frames.pop()
                if state.frames:
                    frame = state.frames.peek()
                    frame.stack.push(v1)
                    frame.pc += 1
                    return state
                else:
                    return "ok"
        
        case a:
            raise NotImplementedError(f"Don't know how to handle: {a!r}")


def handle_method_invocation(m: jvm.AbsMethodID, obj_ref: jvm.Value | None, args: list[jvm.Value]) -> jvm.Value | str | None:
    """Handle method invocations including String methods and assertions"""
    class_name_str = str(m.classname)
    method_name = m.methodid.name
    
    # Handle AssertionError constructor
    # When <init> is called on an AssertionError object, we keep the AssertionError marker
    if "AssertionError" in class_name_str and method_name == "<init>":
        # Constructor doesn't return a value, but we need to keep the object reference
        # The object reference is already on the stack, we just need to return None
        # to indicate the constructor was handled (no return value)
        return None  # Constructor handled, object stays on stack
    
    # Handle String methods - check for java/lang/String or just String
    if "String" in class_name_str or class_name_str.endswith("String"):
        return handle_string_method(method_name, obj_ref, args, m.methodid.return_type)
    
    return None  # Not handled


def handle_string_method(method_name: str, obj_ref: jvm.Value | None, args: list[jvm.Value], return_type: jvm.Type | None) -> jvm.Value | str | None:
    """Handle String method invocations"""
    if obj_ref is None:
        return "null pointer"
    
    string_value = obj_ref.value
    if not isinstance(string_value, str):
        # If it's a Reference but not a string, we might need to handle it differently
        # For now, assume it could be a string
        if string_value is None:
            return "null pointer"
        string_value = str(string_value)
    
    match method_name:
        case "length":
            # String.length() -> int
            if len(args) == 0:
                return jvm.Value.int(len(string_value))
        
        case "charAt":
            # String.charAt(int) -> char
            if len(args) == 1 and isinstance(args[0].type, jvm.Int):
                index = args[0].value
                if index < 0 or index >= len(string_value):
                    return "out of bounds"
                return jvm.Value.char(string_value[index])
        
        case "equals":
            # String.equals(Object) -> boolean
            if len(args) == 1:
                other = args[0].value
                if other is None:
                    return jvm.Value.boolean(False)
                return jvm.Value.boolean(string_value == str(other))
        
        case "isEmpty":
            # String.isEmpty() -> boolean
            if len(args) == 0:
                return jvm.Value.boolean(len(string_value) == 0)
        
        case "substring":
            # String.substring(int) or String.substring(int, int) -> String
            if len(args) == 1 and isinstance(args[0].type, jvm.Int):
                begin = args[0].value
                if begin < 0 or begin > len(string_value):
                    return "out of bounds"
                result_str = string_value[begin:]
                return jvm.Value(jvm.Reference(), result_str)
            elif len(args) == 2 and isinstance(args[0].type, jvm.Int) and isinstance(args[1].type, jvm.Int):
                begin = args[0].value
                end = args[1].value
                if begin < 0 or end > len(string_value) or begin > end:
                    return "out of bounds"
                result_str = string_value[begin:end]
                return jvm.Value(jvm.Reference(), result_str)
        
        case "indexOf":
            # String.indexOf(String) -> int
            if len(args) == 1:
                other = args[0].value
                if other is None:
                    return "null pointer"
                try:
                    index = string_value.index(str(other))
                    return jvm.Value.int(index)
                except ValueError:
                    return jvm.Value.int(-1)
        
        case "concat":
            # String.concat(String) -> String
            if len(args) == 1:
                other = args[0].value
                if other is None:
                    return "null pointer"
                result_str = string_value + str(other)
                return jvm.Value(jvm.Reference(), result_str)
        
        case _:
            return None  # Method not handled, let caller raise NotImplementedError


frame = Frame.from_method(methodid)
for i, v in enumerate(input.values):
    frame.locals[i] = v

state = State({}, Stack.empty().push(frame))

for x in range(1000):
    state = step(state)
    if isinstance(state, str):
        print(state)
        break
else:
    print("*")
