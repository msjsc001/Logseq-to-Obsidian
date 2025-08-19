# Logseq 到 Obsidian 迁移工具

这是一个为 Logseq 用户设计的、工业级强度的 Python 迁移脚本，旨在将您的笔记库无缝、精确地迁移到 Obsidian，同时保留知识网络中最关键的链接结构。

## 它是做什么用的？ (目的)

当您将 Logseq 笔记直接迁移到 Obsidian 时，会遇到几个核心的兼容性问题，本工具旨在一次性解决它们：

1.  **Logseq 块引和块嵌转为 Obsidian 的页面做块**: Logseq 的核心链接方式是块引用 `((uuid))`，这种格式在 Obsidian 中无法识别。本工具能将这些引用智能地转换为 Obsidian 支持的 `[[链接]]` 格式。也就是用`[[页面做块]]`这样极大的保全了logseq块连接，会有少部分没能覆盖到的，我们需要手动处理。

    -   **转换前**:
        ```markdown
        - 这是一个源内容块。
          id:: 1234-5678-90ab-cdef
        - 这里引用了上面的块: ((1234-5678-90ab-cdef))
        ```
    -   **转换后**:
        ```markdown
        - [[这是一个源内容块。]]
        - 这里引用了上面的块: [[这是一个源内容块。]]
        ```

2.  **Logseq 页头属性转为 Obsidian 支持的方式**: Logseq 使用 `tags:: a, b` 这样的格式记录元数据，而 Obsidian 使用标准的 YAML Frontmatter。本工具会自动转换页头属性，并保留所有信息。

    -   **转换前**:
        ```markdown
        alias:: 别名1, 别名2
        tags:: 标签A, 标签B

        文件的其他内容...
        ```
    -   **转换后**:
        ```yaml
        ---
        aliases:
          - "别名1"
          - "别名2"
        tags:
          - "标签A"
          - "标签B"
        ---

        文件的其他内容...
        ```

3.  **Logseq PDF 标注链接也转为 Obsidian 页面做块的方式并标注页码**: Logseq 对 PDF 的标注（Annotation）有特殊的块结构。本工具能准确识别这种结构，提取标注内容和对应的页码，并合成为一个新的、有意义的链接，如 `[[标注内容 page-页码]]`。

    -   **转换前**:
        ```markdown
        - 这是PDF第17页的一句标注。
          ls-type:: annotation
          hl-page:: 17
          id:: 1111-2222-3333-4444
        ```
    -   **转换后**:
        ```markdown
        - [[这是PDF第17页的一句标注。 page-17]]
        ```
        > (注意: `ls-type` 和 `hl-page` 等元数据行会被自动清理)

4.  **Obsidian页面语法的兼容转换**: Windows 文件名和 Markdown 语法中不允许某些特殊字符（如 `* / \ :` 等）。本工具会自动清洗这些字符，确保所有生成的链接在 Obsidian 中都有效且显示正确。

    -   **转换前**:
        ```markdown
        - 内容包含: "特殊*字符" < > | / \ ?
          id:: abcd-efgh-ijkl-mnop
        ```
    -   **转换后**:
        ```markdown
        - [[内容包含： “特殊★字符“ 〈 〉 ｜ - 、 ？]]
        ```

## 它是如何工作的？ (架构)

为了达到最高的准确性和稳定性，脚本采用了经典的 **“读-处理-写” (Read-Process-Write)** 三阶段架构：

1.  **第一阶段：只读扫描，构建数据库**
    -   脚本首先会以**只读模式**完整扫描您指定的笔记目录。
    -   它会智能识别所有带 `id::` 的块，包括普通块和复杂的 PDF 标注块，然后提取或合成它们最终应该呈现的文本内容。
    -   所有文本内容都会经过特殊字符清洗。
    -   最终，脚本会在内存中建立一个完整、准确的 `uuid -> 清洗后的最终内容` 映射数据库。**此阶段不修改任何文件，确保了数据源的纯净。**

2.  **第二阶段：内存处理与文件写入**
    -   在拥有了完整的数据库后，脚本会再次遍历您的笔记。
    -   对于每个文件，它会：
        a.  将文件内容完整读入内存。
        b.  在内存中执行所有转换操作：转换页头属性、替换所有 `((uuid))` 引用、用数据库里的最终内容包裹原始块。
        c.  清理所有不再需要的 Logseq 元数据行（如 `ls-type::`, `hl-page::` 等）。
        d.  将内存中**完全转换好**的内容，一次性、覆盖性地写回原文件。

这种架构彻底分离了数据读取和写入，从根本上避免了因处理顺序和数据状态不一致而可能出现的各种错误（如链接丢失、重复包裹等）。

## 如何使用？

### 环境要求
-   Python 3.6 或更高版本。

### 执行步骤

1.  **下载脚本**: 将 `L块-O页面块_migrate.py` 文件放置到您希望运行它的地方（例如，您的 Logseq 笔记库根目录，或任何方便的位置）。
2.  **打开终端**:
    -   在 Windows 上，可以是 `Command Prompt (cmd)` 或 `PowerShell`。
    -   在 macOS 或 Linux 上，是 `Terminal`。
3.  **导航到脚本目录**: 使用 `cd` 命令进入到您存放脚本的文件夹。例如：
    ```bash
    cd D:\MyNotes\LogseqVault
    ```
4.  **执行命令**:
    -   **推荐方式 (迁移指定目录)**:
        ```bash
        python L块-O页面块_migrate.py "D:\path\to\your\notes"
        ```
        > **注意**: 请将 `"D:\path\to\your\notes"` 替换成您真实的 Logseq 笔记库路径。

    -   **便捷方式 (迁移当前目录)**: 如果您已经 `cd` 到了笔记库的根目录，可以直接运行：
        ```bash
        python L块-O页面块_migrate.py
        ```

## 需要注意什么？

-   **务必备份！**: 尽管脚本内置了自动备份功能，但在对您宝贵的知识库进行任何批量操作前，**强烈建议您手动将整个笔记库复制一份作为最终保险**。
-   **自动备份位置**: 脚本会在您指定的笔记目录下创建一个名为 `L块-O页面块_backup_[日期时间]` 的文件夹，里面是运行前所有 `.md` 文件的完整备份。
-   **日志文件**: 每次运行，脚本都会在**其所在的目录**下生成一个 `.log` 文件。如果迁移后发现有少量链接未转换，您可以查看这个日志文件，它会记录所有警告信息（如未在数据库中找到的 ID），方便您定位问题。
-   **幂等性**: 脚本被设计为可以安全地重复运行。如果您第一次运行后发现有遗漏（例如，新加入了一些文件），您可以直接再次运行，它不会破坏已经转换好的内容。

---
# Obsidian 的大纲双链接笔记方式使用教程！
## OB大纲
<img width="1159" height="2091" alt="image" src="https://github.com/user-attachments/assets/9f842d46-b5ad-40d8-aed0-ab387e83aacb" />

## OB块引用与块嵌入
<img width="1440" height="2695" alt="image" src="https://github.com/user-attachments/assets/660089f2-e0e8-443a-9309-253cdc47499e" />

## OB属性与查询
<img width="968" height="4100" alt="image" src="https://github.com/user-attachments/assets/5c04418b-04f6-4db5-847e-fbb6ac750586" />

## OB Dataview插件
<img width="1134" height="2338" alt="image" src="https://github.com/user-attachments/assets/37486091-39a2-4d60-ad1e-6041697360e4" />

## OB Bases数据库
<img width="1168" height="931" alt="image" src="https://github.com/user-attachments/assets/38caa078-8ef0-4b8c-aff1-294fa89c9028" />

## OB代码块
<img width="1134" height="2572" alt="image" src="https://github.com/user-attachments/assets/10a3e629-84d3-403c-9a22-bcaa4f69f7a5" />

## OB表格
<img width="1123" height="2088" alt="image" src="https://github.com/user-attachments/assets/bec61ea7-2f47-4266-b392-68d72dd8120a" />








