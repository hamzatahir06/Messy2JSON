# 🤖 Messy2JSON

> **Transform messy, unstructured text into clean, structured JSON using Groq LLMs.**

Messy2JSON is a lightweight, cross-platform Python CLI that converts meeting notes, emails, chat logs, and voice-to-text transcripts into structured JSON containing a summary, action items, and deadlines. Built with reliability in mind, it validates AI responses, automatically repairs malformed outputs, and provides a seamless terminal experience.

---

## ✨ Features

- 🤖 AI-powered information extraction using **Groq LLMs**
- 🔒 One-time API key setup with live validation
- 🧠 Automatic JSON self-repair using an AI reflection loop
- ✅ Strict schema validation for reliable output
- 📋 Automatic clipboard copy after successful extraction
- 📂 Read input from files, interactive mode, or Unix pipes
- 💾 Save structured JSON directly to a file
- 💻 Cross-platform support (Windows, macOS, Linux)
- ⚡ Fast, clean terminal interface powered by Rich

---

## 📦 Output Format

Every input is converted into the following JSON structure:

```json
{
  "summary": "A concise summary of the input.",
  "action_items": [
    "Action item 1",
    "Action item 2"
  ],
  "deadline": "Mentioned deadline or null"
}
```

---

## 🚀 Installation

### Clone the repository

```bash
git clone https://github.com/hamzatahir06/Messy2JSON.git
cd Messy2JSON
```

### Create a virtual environment

**Linux / macOS**

```bash
python -m venv venv
source venv/bin/activate
```

**Windows**

```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Install the package

```bash
pip install -e .
```

> **PyPI support is coming soon.**

```bash
pip install messy2json
```

---

## ⚡ Quick Start

### Interactive Mode

```bash
messy2json
```

Paste your text, then type:

```text
/do
```

to generate structured JSON.

---

### Read from a File

```bash
messy2json -f meeting_notes.txt
```

---

### Read from Standard Input

```bash
cat notes.txt | messy2json
```

---

### Save Output to a File

```bash
messy2json -f notes.txt -o output.json
```

---

### Use a Different Model

```bash
messy2json --model llama-3.3-70b-versatile
```

---

## ⚙️ Configuration

During the first run, Messy2JSON securely prompts for your Groq API key, validates it online, and stores it locally using your operating system's standard configuration directory.

You can also provide configuration through environment variables.

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Your Groq API key |
| `GROQ_MODEL` | Override the default model |

---

## 📁 Project Structure

```text
Messy2JSON/
│
├── messy2json/
│   ├── __init__.py
│   └── main.py
│
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 🛠 Built With

- **Python 3.12+**
- **Groq Python SDK**
- **Rich**
- **Pyperclip**

---

## 💡 Why Messy2JSON?

Unlike basic AI wrappers, Messy2JSON is designed to produce **consistent and dependable JSON**.

It includes:

- Schema validation
- Automatic retry and self-correction
- Live API key verification
- Cross-platform configuration management
- Clipboard integration
- Interactive and non-interactive workflows

The goal is simple: **give developers structured output they can immediately use in automation pipelines, scripts, or applications.**

---

## 📄 License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for details.

---

## ⭐ Support the Project

If you find Messy2JSON useful, consider giving the repository a ⭐ on GitHub.

It helps others discover the project and motivates future development.

---

**Made with ❤️ by [Hamza Tahir](https://github.com/hamzatahir06)**