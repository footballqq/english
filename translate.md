# 双语CSV翻译工具 (translate.py)

## 功能简介
`translate.py` 是一个命令行工具，用于将特定格式的CSV文件（如 `razfull.csv`）中的英文书名和单词列表批量翻译成中文，并生成一个中英双语对照的CSV文件。它内置了断点续传和错误恢复机制，以确保在处理大量数据时的稳定性和效率。

## 文件格式

### 输入文件格式 (e.g., razfull.csv)
一个标准的CSV文件，程序会假定文件不包含表头，或自动跳过第一行。

- **每行结构**: 代表一本书的信息。
- **列定义**:
  - `列1`: RAZ 等级 (e.g., `aa`, `A`, `B`)
  - `列2`: 英文书名 (e.g., `A Fun Day`)
  - `列3` 及之后: 该书的英文单词列表 (e.g., `word1`, `word2`, ...)

### 输出文件格式 (e.g., translated_output.csv)
一个标准的CSV文件，包含表头。对于源文件中的每一本书，输出文件中会生成对应的两行：一行中文，一行英文。

- **表头**: `RAZ Level`, `Book Title`, `单词1`, `单词2`, ...
- **内容行示例**:
  ```csv
  aa,"有趣的一天",乐趣,天,...
  aa,"A Fun Day",fun,day,...
  ```
- **失败标记**: 如果某个单词翻译失败，对应的单元格会显示为 `[翻译失败:...]`，方便后续进行错误恢复。

## 功能与用法

### 1. 基本翻译
这是最基础的用法。程序会读取指定的输入文件，进行完整翻译，并生成一个全新的输出文件。如果输出文件已存在，它将被覆盖。

- **命令**: 
  ```bash
  python translate.py <输入文件> <输出文件>
  ```
- **示例**:
  ```bash
  python translate.py razfull.csv translated_output.csv
  ```

### 2. 断点续传 (`--resume`)
当翻译大量文件时，如果程序意外中断（例如网络问题或手动停止），此功能可以从上次的进度继续，而无需从头开始。它通过检查输出文件中已有的记录来跳过已完成的书目。

- **命令**:
  ```bash
  python translate.py <输入文件> <输出文件> --resume
  ```
- **示例**:
  ```bash
  python translate.py razfull.csv translated_output.csv --resume
  ```

### 3. 错误恢复 (`--retry-failures`)
如果第一次翻译后，输出文件中存在一些 `[翻译失败:...]` 的条目，此功能可以专门处理这些失败的单词。它会读取包含失败标记的文件，仅重试翻译失败的单词，然后生成一个**全新的、完全修正过**的文件。

- **命令**:
  ```bash
  python translate.py <含错误的文件> <修正后的新文件名> --retry-failures
  ```
- **示例**:
  ```bash
  python translate.py translated_output.csv translated_fixed.csv --retry-failures
  ```

### 4. 限制处理行数 (`--limit`)
一个用于快速测试的便捷参数，可以限制程序处理的输入文件行数。它可以与以上任何模式结合使用。

- **命令**:
  ```bash
  python translate.py --limit <行数>
  ```
- **示例**:
  ```bash
  python translate.py razfull.csv translated_output.csv --limit 10
  ```

## 完整使用流程示例

1.  **首次运行**，开始翻译 `razfull.csv`：
    ```bash
    python translate.py razfull.csv translated_output.csv
    ```
    *(假设程序运行一半后因网络问题中断...)*

2.  **恢复运行**，使用 `--resume` 从断点继续：
    ```bash
    python translate.py razfull.csv translated_output.csv --resume
    ```
    *(程序完成后，检查 `translated_output.csv`，发现有几个单词翻译失败)*

3.  **修复错误**，使用 `--retry-failures` 生成一个干净的最终文件：
    ```bash
    python translate.py translated_output.csv translated_fixed.csv --retry-failures
    ```
    *(任务完成。`translated_fixed.csv` 是最终的、干净的、完整的翻译文件)*
