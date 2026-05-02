# System Documentation Diagrams

This folder contains system design diagrams for the Smart Microgrid Analytics project.
These diagrams are for documentation purposes (thesis, reports, presentations).

## Diagram Types

1. **Class Diagram** - Shows object-oriented design and relationships
2. **Use Case Diagram** - Illustrates user interactions with the system
3. **Activity Diagram** - Depicts workflow and process flow
4. **Entity-Relationship Diagram** - Shows database schema and relationships

## How to Use

These diagrams are written in Mermaid syntax, which can be:
- Rendered in Markdown viewers (GitHub, VSCode with Mermaid extension)
- Converted to images using [Mermaid Live Editor](https://mermaid.live/)
- Embedded in thesis documents using LaTeX mermaid packages
- Exported as PNG/SVG for presentations

## Rendering Options

### Option 1: VSCode
Install "Markdown Preview Mermaid Support" extension and preview `.md` files

### Option 2: Online
Copy diagram code to https://mermaid.live/ and export as image

### Option 3: LaTeX
Use `\usepackage{mermaid}` in your thesis document

### Option 4: Command Line
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.md -o diagram.png
```
