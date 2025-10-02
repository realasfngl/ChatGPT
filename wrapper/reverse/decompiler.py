import re
import json
import base64


class Decompiler:
    
    
    mapping: dict = {
        "1": "XOR_STR",
        "2": "SET_VALUE",
        "3": "BTOA",
        "4": "BTOA_2",
        "5": "ADD_OR_PUSH",
        "6": "ARRAY_ACCESS",
        "7": "CALL",
        "8": "COPY",
        "10": "window",
        "11": "GET_SCRIPT_SRC",
        "12": "GET_MAP",
        "13": "TRY_CALL",
        "14": "JSON_PARSE",
        "15": "JSON_STRINGIFY",
        "17": "CALL_AND_SET",
        "18": "ATOB",
        "19": "BTOA_3",
        "20": "IF_EQUAL_CALL",
        "21": "IF_DIFF_CALL",
        "22": "TEMP_STACK_CALL",
        "23": "IF_DEFINED_CALL",
        "24": "BIND_METHOD",
        "27": "REMOVE_OR_SUBTRACT",
        "28": "undefined",
        "25": "undefined",
        "26": "undefined",
        "29": "LESS_THAN",
        "31": "INCREMENT",
        "32": "DECREMENT_AND_EXEC",
        "33": "MULTIPLY",
        "34": "MOVE"
    }

    functions: dict = {
            "XOR_STR": """function XOR_STR(e, t) {
        e = String(e);
        t = String(t);
        let n = "";
        for (let r = 0; r < e.length; r++)
            n += String.fromCharCode(e.charCodeAt(r) ^ t.charCodeAt(r % t.length));
        return n;
    }
    """
    }

    @staticmethod
    def start():
        Decompiler.xorkey = ""
        Decompiler.xorkey2 = ""
        Decompiler.decompiled = "var mem = {};\n"
        Decompiler.array_dict = {}
        Decompiler.vg = 0
        Decompiler.round1 = 0
        Decompiler.found = False
        Decompiler.potential = []

    @staticmethod
    def xS(e, t):
        n = ""
        for r in range(len(e)):
            n += chr(ord(e[r]) ^ ord(t[r % len(t)]))
        return n

    @staticmethod
    def handle_operation(operation, args):
        if operation == "COPY":
            Decompiler.mapping[args[0]] = Decompiler.mapping[args[1]]
            if Decompiler.mapping[args[1]] != "window":
                if Decompiler.mapping[args[1]] in Decompiler.functions and f"function {Decompiler.mapping[args[1]]}" not in Decompiler.decompiled:
                    Decompiler.decompiled += Decompiler.functions[Decompiler.mapping[args[1]]] + "\n"
            else:
                var_name = str(args[1]).replace(".", "_")
                Decompiler.decompiled += f"var var_{var_name} = window;\n"
                Decompiler.array_dict[args[1]] = "window"
        
        elif operation == "SET_VALUE":
            var_name = str(args[0]).replace(".", "_")
            value = args[1]
            try:
                num = float(value)
                if num.is_integer():
                    Decompiler.decompiled += f"var var_{var_name} = {int(num)};\n"
                    Decompiler.array_dict[args[0]] = str(int(num))
                else:
                    Decompiler.decompiled += f"var var_{var_name} = {num};\n"
                    Decompiler.array_dict[args[0]] = str(num)
            except (ValueError, TypeError):
                if isinstance(value, str):
                    if value == "[]":
                        Decompiler.decompiled += f"var var_{var_name} = [];\n"
                        Decompiler.array_dict[args[0]] = []
                    
                    elif value == "None":
                        Decompiler.decompiled += f"var var_{var_name} = null;\n"
                        Decompiler.array_dict[args[0]] = "null"
                        
                    else:
                        Decompiler.decompiled += f"var var_{var_name} = \"{value}\";\n"
                        Decompiler.array_dict[args[0]] = f"\"{value}\""
                elif isinstance(value, list):
                    Decompiler.decompiled += f"var var_{var_name} = [];\n"
                    Decompiler.array_dict[args[0]] = []
                elif value is None:
                    Decompiler.decompiled += f"var var_{var_name} = null;\n"
                    Decompiler.array_dict[args[0]] = "null"
                else:
                    Decompiler.decompiled += f"var var_{var_name} = {value};\n"
                    Decompiler.array_dict[args[0]] = str(value)
        
        elif operation == "ARRAY_ACCESS":
            Decompiler.handle_array_access(args)
        
        elif operation == "BIND_METHOD":
            Decompiler.handle_bind_method(args)
        
        elif operation == "XOR_STR":
            if Decompiler.round1 == 1 and len(Decompiler.potential) < 2:
                Decompiler.potential.append({"var": args[0], "key": args[1]})
            var_name = str(args[0]).replace(".", "_")
            key_name = str(args[1]).replace(".", "_")
            Decompiler.decompiled += f"var var_{var_name} = XOR_STR(var_{var_name}, var_{key_name});\n"
        
        elif operation == "BTOA_3":
            var_name = str(args[0]).replace(".", "_")
            Decompiler.decompiled += f"var var_{var_name} = btoa(\"\" + var_{var_name});\n"
        
        elif operation == "CALL_AND_SET":
            var_name = str(args[0]).replace(".", "_")
            func_name = str(args[1]).replace(".", "_")
            args_str = ", ".join(f"var_{arg.replace('.', '_')}" for arg in args[2:])
            Decompiler.decompiled += f"var var_{var_name} = var_{func_name}({args_str});\n"
        
        elif operation == "IF_DEFINED_CALL":
            Decompiler.handle_if_defined_call(args)
        
        elif operation == "CALL":
            Decompiler.handle_call_operation(args)
        
        elif operation == "ADD_OR_PUSH":
            var_name = str(args[0]).replace(".", "_")
            arg_name = str(args[1]).replace(".", "_")
            Decompiler.decompiled += (
                f"var var_{var_name} = Array.isArray(var_{var_name}) ? "
                f"(var_{var_name}.push(var_{arg_name}), var_{var_name}) : var_{var_name} + var_{arg_name};\n"
            )
        
        elif operation == "IF_DIFF_CALL":
            var_0 = str(args[0]).replace(".", "_")
            var_1 = str(args[1]).replace(".", "_")
            var_2 = str(args[2]).replace(".", "_")
            if Decompiler.mapping.get(args[3]) == "COPY":
                var_4 = str(args[4]).replace(".", "_")
                var_5 = str(args[5]).replace(".", "_")
                Decompiler.decompiled += (
                    f"Math.abs(var_{var_0} - var_{var_1}) > var_{var_2} ? var_{var_4} = var_{var_5} : null;\n"
                )
            else:
                args_str = ", ".join(f"var_{arg.replace('.', '_')}" for arg in args[4:])
                Decompiler.decompiled += (
                    f"Math.abs(var_{var_0} - var_{var_1}) > var_{var_2} ? {Decompiler.mapping[args[3]]}({args_str}) : null;\n"
                )
        
        elif operation == "TRY_CALL":
            Decompiler.handle_try_call(args)
        
        elif operation == "JSON_STRINGIFY":
            var_name = str(args[0]).replace(".", "_")
            Decompiler.decompiled += f"var var_{var_name} = JSON.stringify(var_{var_name});\n"
            
        elif operation == "MOVE":
            Decompiler.decompiled += f"MOVE {args}" # not even used lmfao
        
        else:
            mapped = [Decompiler.mapping[key] for key in args[1:] if key in Decompiler.mapping]
            unlabeled = [str(key) for key in args[1:] if key not in Decompiler.mapping]
            all_values = " ".join(mapped + unlabeled)
            Decompiler.decompiled += f"// UNKNOWN: {operation} -> {args[0]} {all_values};\n"

    @staticmethod
    def handle_try_call(args):
        target_var = f"var_{str(args[0]).replace('.', '_')}"
        fn = Decompiler.mapping.get(args[1], "")
        rest_args = [f"var_{str(a).replace('.', '_')}" for a in args[2:]]
        if fn == "ARRAY_ACCESS":
            Decompiler.decompiled += (
                f"try {{ mem[{rest_args[0]}] = {rest_args[1]}[{rest_args[0]}]; }} catch(r) {{ {target_var} = \"\" + r; }}\n"
            )
        else:
            args_str = ", ".join(rest_args)
            Decompiler.decompiled += (
                f"try {{ {fn}({args_str}); }} catch(r) {{ {target_var} = \"\" + r; }}\n"
            )

    @staticmethod
    def handle_array_access(args):
        var_0 = str(args[0]).replace(".", "_")
        var_1 = str(args[1]).replace(".", "_")
        var_2 = str(args[2]).replace(".", "_")
        if f"var var_{var_1} =" in Decompiler.decompiled:
            if args[1] in Decompiler.array_dict or args[2] in Decompiler.array_dict:
                if args[2] in Decompiler.array_dict and args[1] not in Decompiler.array_dict:
                    Decompiler.decompiled += f"var var_{var_0} = var_{var_1}[{Decompiler.array_dict[args[2]]}];\n"
                elif args[1] in Decompiler.array_dict and args[2] not in Decompiler.array_dict:
                    Decompiler.decompiled += f"var var_{var_0} = {Decompiler.array_dict[args[1]]}[var_{var_2}];\n"
                else:
                    if re.search(rf"var\s+var_{var_1}\s*=\s*\w+\([^)]*\)", Decompiler.decompiled):
                        Decompiler.decompiled += f"var var_{var_0} = var_{var_1}[{Decompiler.array_dict[args[2]]}];\n"
                        Decompiler.array_dict[args[0]] = f"var_{var_1}[{Decompiler.array_dict[args[2]]}]"
                    else:
                        Decompiler.decompiled += f"var var_{var_0} = {Decompiler.array_dict[args[1]]}[{Decompiler.array_dict[args[2]]}];\n"
                        Decompiler.array_dict[args[0]] = f"{Decompiler.array_dict[args[1]]}[{Decompiler.array_dict[args[2]]}]"
            else:
                Decompiler.decompiled += f"var var_{var_0} = var_{var_1}[var_{var_2}];\n"
        else:
            Decompiler.decompiled += f"var var_{var_0} = window[var_{var_2}];\n"

    @staticmethod
    def handle_bind_method(args):
        var_0 = str(args[0]).replace(".", "_")
        var_1 = str(args[1]).replace(".", "_")
        var_2 = str(args[2]).replace(".", "_")
        if f"var var_{var_1} =" in Decompiler.decompiled:
            if args[1] in Decompiler.array_dict or args[2] in Decompiler.array_dict:
                if args[1] in Decompiler.array_dict and args[2] not in Decompiler.array_dict:
                    Decompiler.decompiled += (
                        f"var var_{var_0} = {Decompiler.array_dict[args[1]]}[var_{var_2}].bind({Decompiler.array_dict[args[1]]});\n"
                    )
                else:
                    if re.search(rf"var\s+var_{var_1}\s*=\s*\w+\([^)]*\)", Decompiler.decompiled):
                        Decompiler.decompiled += (
                            f"var var_{var_0} = var_{var_1}[{Decompiler.array_dict[args[2]]}].bind(var_{var_1});\n"
                        )
                        Decompiler.array_dict[args[0]] = f"var_{var_1}[{Decompiler.array_dict[args[2]]}]"
                    else:
                        Decompiler.decompiled += (
                            f"var var_{var_0} = {Decompiler.array_dict[args[1]]}[{Decompiler.array_dict[args[2]]}].bind({Decompiler.array_dict[args[1]]});\n"
                        )
                        Decompiler.array_dict[args[0]] = f"{Decompiler.array_dict[args[1]]}[{Decompiler.array_dict[args[2]]}]"
            else:
                Decompiler.decompiled += (
                    f"var var_{var_0} = var_{var_1}[var_{var_2}].bind(var_{var_1});\n"
                )
        else:
            Decompiler.decompiled += (
                f"var var_{var_0} = window[var_{var_2}].bind(var_{var_1});\n"
            )

    @staticmethod
    def handle_if_defined_call(args):
        result = []
        for item in args:
            if item in Decompiler.mapping:
                keys = [k for k, v in Decompiler.mapping.items() if v == Decompiler.mapping[item] and k != item]
                result.append(keys[0] if keys else None)
            else:
                result.append(None)
        result = [
            None if key is None else ([k for k, v in Decompiler.mapping.items() if v == Decompiler.mapping[key] and k != key] or [None])[0]
            for key in result
        ]
        
        if len(args) == 4:
            target = str(args[3]).replace(".", "_")
            count = len(re.findall(target, Decompiler.decompiled))
            if count <= 1 and f"var var_{str(args[2]).replace('.', '_')}" not in Decompiler.decompiled:
                if not Decompiler.xorkey:
                    Decompiler.xorkey = str(args[3])
                var_0 = str(args[0]).replace(".", "_")
                arg_2 = str(args[2]).replace(".", "_")
                arg_3 = str(args[3]).replace(".", "_")
                if Decompiler.mapping.get(result[1]) == "SET_VALUE":
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? (mem[\"{args[2]}\"] = \"{args[3]}\", var_{var_0}) : var_{var_0};\n"
                    )
                else:
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? ({Decompiler.mapping[result[1]]}(\"{args[2]}\", \"{args[3]}\") || var_{var_0}) : var_{var_0};\n"
                    )
            elif count <= 3:
                var_0 = str(args[0]).replace(".", "_")
                arg_2 = str(args[2]).replace(".", "_")
                arg_3 = str(args[3]).replace(".", "_")
                if Decompiler.mapping.get(result[1]) == "SET_VALUE":
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? ((mem[\"{args[2]}\"] = \"{args[3]}\") || var_{var_0}) : var_{var_0};\n"
                    )
                else:
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? ({Decompiler.mapping[result[1]]}(var_{arg_2}, mem[\"{args[3]}\"]) || var_{var_0}) : var_{var_0};\n"
                    )
            elif Decompiler.mapping.get(result[1]) == "JSON_PARSE":
                var_0 = str(args[0]).replace(".", "_")
                arg_3 = str(args[3]).replace(".", "_")
                Decompiler.decompiled += (
                    f"var var_{var_0} = var_{var_0} !== void 0 ? (JSON.parse(var_{arg_3}) || var_{var_0}) : var_{var_0};\n"
                )
            else:
                var_0 = str(args[0]).replace(".", "_")
                args_str = ", ".join(f"var_{arg.replace('.', '_')}" for arg in args[2:])
                Decompiler.decompiled += (
                    f"var var_{var_0} = var_{var_0} !== void 0 ? ({Decompiler.mapping[result[1]]}({args_str}) || var_{var_0}) : var_{var_0};\n"
                )
        else:
            var_0 = str(args[0]).replace(".", "_")
            if len(args) > 4 and f"mem[\"{args[4]}\"] =" in Decompiler.decompiled:
                args_str = ", ".join(
                    f"mem[\"{arg}\"]" if i + 2 == 3 else f"var_{str(arg).replace('.', '_')}"
                    for i, arg in enumerate(args[2:])
                )
                if Decompiler.mapping.get(result[1]) == "CALL":
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? (var_{str(args[2]).replace('.', '_')}({args_str}) || var_{var_0}) : var_{var_0};\n"
                    )
                else:
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? ({Decompiler.mapping[result[1]]}({args_str}) || var_{var_0}) : var_{var_0};\n"
                    )
            else:
                args_str = ", ".join(f"var_{arg.replace('.', '_')}" for arg in args[2:])
                if Decompiler.mapping.get(result[1]) == "ATOB":
                    arg_2 = str(args[2]).replace(".", "_")
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? (atob(\"\" + var_{arg_2}) || var_{var_0}) : var_{var_0};\n"
                    )
                elif len(args) >= 3 and result[1] in Decompiler.mapping:
                    Decompiler.decompiled += (
                        f"var var_{var_0} = var_{var_0} !== void 0 ? ({Decompiler.mapping[result[1]]}({args_str}) || var_{var_0}) : var_{var_0};\n"
                    )
                else:
                    Decompiler.decompiled += f"// ERROR: Invalid IF_DEFINED_CALL with args {args};\n"

    @staticmethod
    def handle_call_operation(args):
        if args[0] in Decompiler.mapping:
            if Decompiler.mapping[args[0]] == "BTOA":
                arg_1 = str(args[1]).replace(".", "_")
                Decompiler.decompiled += f"console.log(btoa(\"\" + var_{arg_1}));\n"
            else:
                args_str = ", ".join(f"var_{arg.replace('.', '_')}" for arg in args)
                Decompiler.decompiled += f"{Decompiler.mapping[args[0]]}({args_str});\n"
        else:
            if f"var var_{str(args[0]).replace('.', '_')} = \"set\";" in Decompiler.decompiled:
                arg_1 = str(args[1]).replace(".", "_")
                arg_2 = str(args[2]).replace(".", "_")
                arg_3 = str(args[3]).replace(".", "_")
                Decompiler.decompiled += f"var_{arg_1}[var_{arg_2}] = var_{arg_3};\n"
            else:
                args_str = ", ".join(f"var_{arg.replace('.', '_')}" for arg in args[1:])
                Decompiler.decompiled += f"var_{str(args[0]).replace('.', '_')}({args_str});\n"

    @staticmethod
    def remove_unused_variables():
        lines = Decompiler.decompiled.split("\n")
        used_vars = set()
        var_decl_lines = []

        for i, line in enumerate(lines):
            match = re.match(r"^var\s+var_([\w_]+)\s*=", line)
            if match:
                var_decl_lines.append({"name": match.group(1), "index": i})

        for var in var_decl_lines:
            name = var["name"]
            is_used = any(name in line and not line.startswith(f"var var_{name} =") for line in lines)
            if is_used:
                used_vars.add(name)

        Decompiler.decompiled = "\n".join(
            line for line in lines
            if not re.match(r"^var\s+var_([\w_]+)\s*=", line) or re.match(r"^var\s+var_([\w_]+)\s*=", line).group(1) in used_vars
        )

    @staticmethod
    def decompile(bytecode):
        while len(bytecode) > 0:
            e = str(bytecode[0][0])
            t = [str(item) for item in bytecode[0][1:]]
            bytecode.pop(0)
            Decompiler.vg += 1
            
            if e in Decompiler.mapping:
                Decompiler.handle_operation(Decompiler.mapping[e], t)
            else:
                Decompiler.decompiled += f"// UNKNOWN_OPCODE {e} -> {', '.join(t)};\n"
            
            if Decompiler.mapping.get(e) == "CALL" and not Decompiler.found:
                for entry in Decompiler.potential:
                    if len(t) > 3 and entry["var"] == t[3]:
                        key_str = str(entry["key"]).replace(".", "_")
                        regex = rf"var var_{key_str} = (.*);"
                        match = re.search(regex, Decompiler.decompiled)
                        if match:
                            Decompiler.xorkey2 = match.group(1).replace(";", "")
                        Decompiler.found = True
                        break

        if Decompiler.round1 == 0:
            Decompiler.round1 += 1
            Decompiler.decompile_2()

    @staticmethod
    def decompile_2():
        matches = [m.group(2) for m in re.finditer(r"var\s+\w+\s*=\s*(['\"`])([\s\S]*?)\1", Decompiler.decompiled)]
        bytecode = max(matches, key=len, default="")
        if bytecode:
            decoded = json.loads(Decompiler.xS(base64.b64decode(bytecode).decode(), str(Decompiler.xorkey)))
            Decompiler.decompile(decoded)
        
        if Decompiler.round1 == 1:
            Decompiler.round1 += 1
            Decompiler.decompile_3()

    @staticmethod
    def decompile_3():
        matches = [m.group(2) for m in re.finditer(r"var\s+\w+\s*=\s*(['\"`])([\s\S]*?)\1", Decompiler.decompiled)]
        bytecode = next((s for s in matches if 60 <= len(s) <= 200), "")
        if bytecode:
            decoded = json.loads(Decompiler.xS(base64.b64decode(bytecode).decode(), str(Decompiler.xorkey)))
            Decompiler.decompile(decoded)
        Decompiler.remove_unused_variables()

    @staticmethod
    def decompile_vm(turnstile, token):
        Decompiler.start()
        Decompiler.decompiled = (
            "const { JSDOM } = require(\"jsdom\");\n"
            "const dom = new JSDOM(\"<!DOCTYPE html><p>Hello world</p>\", { url: \"https://chatgpt.com/\" });\n"
            "const window = dom.window;\n"
            "var mem = {};\n"
        )
        Decompiler.decompile(json.loads(Decompiler.xS(base64.b64decode(turnstile).decode(), str(token))))
        return Decompiler.decompiled
    
# NOTE dont mind this please i converted my JS decompiler to py using AI dont judge this please