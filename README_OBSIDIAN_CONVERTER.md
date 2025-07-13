# Obsidian to Hugo Converter

This Python script converts Obsidian markdown notes to Hugo-compatible format.

## Features

- **Backlink Removal**: Converts Obsidian-style backlinks (`[[Page Name]]` or `[[Page Name|Display Text]]`) to plain text
- **Image Processing**: Handles Obsidian image embeds (`![[image.png]]`) and moves images to Hugo's post structure
- **Folder Organization**: Creates unique folders for each post containing the `index.md` file and associated images
- **Hugo Front Matter**: Automatically generates proper YAML front matter for Hugo posts
- **Command Line Interface**: Easy to use with command line arguments

## Requirements

- Python 3.6+
- PyYAML library

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python obsidian_to_hugo.py /path/to/obsidian/vault
```

### Specify Hugo Site Root
```bash
python obsidian_to_hugo.py /path/to/obsidian/vault --hugo-root /path/to/hugo/site
```

## What the Script Does

1. **Scans** the Obsidian vault folder for all `.md` files
2. **Processes** each markdown file to:
   - Remove Obsidian-style backlinks that aren't supported in Hugo
   - Convert image embeds to standard markdown format
   - Generate appropriate Hugo front matter (title, date, draft status)
3. **Creates** a unique folder for each post in `content/posts/`
4. **Copies** any referenced images to the post folder
5. **Saves** the processed content as `index.md` in each post folder

## Example

Given an Obsidian note with this content:
```markdown
# My Blog Post

I want to reference [[Another Note]] and show an image: ![[diagram.png]]
```

The script will create:
```
content/posts/my-blog-post/
├── index.md
└── diagram.png
```

Where `index.md` contains:
```markdown
---
title: My Blog Post
date: '2025-07-13'
draft: false
---

# My Blog Post

I want to reference Another Note and show an image: ![diagram.png](diagram.png)
```

## File Structure

- **Input**: Obsidian vault with `.md` files and images
- **Output**: Hugo-compatible folder structure in `content/posts/`

The script automatically:
- Creates slugified folder names from post titles
- Handles duplicate image references
- Searches for images in common Obsidian attachment folders
- Preserves file modification dates for front matter generation

## Notes

- The script preserves the original Obsidian files (read-only operation)
- Images are copied (not moved) from the Obsidian vault
- Existing Hugo posts with the same slug will be overwritten
- The script handles both Obsidian-style (`![[image.png]]`) and standard markdown (`![alt](image.png)`) image references