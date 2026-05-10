# 🌲 PicoScrypt Compiler

Welcome to the GitHub home of `PicoScrypt-compiler`! This repository is a compact compiler project designed for our course **CS4031 - Compiler Construction** @ FAST NUCES Karachi.

![Hero Image](docs/hero_img.png)

## 🌱 Setup

1. Clone the repository on your machine:

   ```bash
   git clone https://github.com/your-username/PicoScrypt-compiler.git
   cd PicoScrypt-compiler
   ```

2. From the repo root, run the compiler:

   ```bash
   python3 --version
   ```

3. (Optional) Create a virtual environment for local testing:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. No extra packages are required for the core project. If you use a fresh environment, standard Python should be enough.

## 💻️ Usage

### Run an example

Execute the compiler with one of the example files:

```bash
python3 main.py examples/crypt.pico
```

### Try more examples

Available example scripts:
- `examples/crypt.pico`
- `examples/inn.pico`
- `examples/lighthouse.pico`
- `examples/manor.pico`
- `examples/shipwreck.pico`
- `examples/tomb.pico`

### 🧭️ Explore the codebase

Main source files:
- `lexer.py` — tokenizes raw input
- `parser.py` — builds the syntax tree
- `semantic.py` — validates semantics and rules
- `optimizer.py` — optimizes generated code
- `codegen.py` — outputs compiled code
- `interpreter.py` — runs code directly

## 🍄 Contributing

Contributions are welcome! If you want to extend the language, improve examples, or add features, feel free to open an issue or submit a pull request.
